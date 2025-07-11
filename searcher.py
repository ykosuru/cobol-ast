#!/usr/bin/env python3
"""
TAL JIRA Ticket Searcher

This module analyzes JIRA tickets against TAL code indexes
and prepares results for LLM consumption.
"""

import os
import pickle
import json
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


@dataclass
class CodeFragment:
    """Represents a fragment of TAL code with metadata."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    function_name: Optional[str] = None
    procedure_name: Optional[str] = None
    comments: List[str] = None
    variables: List[str] = None
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
        if self.variables is None:
            self.variables = []


@dataclass
class JiraTicket:
    """Represents a JIRA ticket with requirements."""
    ticket_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str = "Medium"
    
    def get_combined_text(self) -> str:
        """Combine all ticket text for semantic analysis."""
        combined = f"{self.title}\n\n{self.description}\n\n"
        if self.acceptance_criteria:
            combined += "Acceptance Criteria:\n"
            for i, criteria in enumerate(self.acceptance_criteria, 1):
                combined += f"{i}. {criteria}\n"
        return combined


@dataclass 
class CodeMatch:
    """Represents a code fragment match with analysis."""
    fragment: CodeFragment
    similarity_score: float
    matching_keywords: List[str]
    relevance_reason: str
    code_snippet: str


class TALIndexLoader:
    """Loads TAL semantic indexes for searching."""
    
    def __init__(self):
        self.fragments: List[CodeFragment] = []
        self.embeddings = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.model = None
        self.index_metadata = {}
    
    def load_index(self, file_path: str) -> bool:
        """Load the index from disk."""
        try:
            print(f"Loading TAL index from {file_path}...")
            
            with open(file_path, 'rb') as f:
                index_data = pickle.load(f)
            
            self.fragments = index_data['fragments']
            self.embeddings = index_data['embeddings']
            self.tfidf_vectorizer = index_data['tfidf_vectorizer']
            self.tfidf_matrix = index_data['tfidf_matrix']
            self.index_metadata = index_data.get('metadata', {})
            
            # Initialize the same model used for indexing
            model_name = self.index_metadata.get('model_name', 'all-MiniLM-L6-v2')
            print(f"Loading sentence transformer model: {model_name}")
            self.model = SentenceTransformer(model_name)
            
            print(f"Index loaded successfully!")
            print(f"- Total fragments: {len(self.fragments)}")
            print(f"- Total files: {self.index_metadata.get('total_files', 'unknown')}")
            print(f"- Created: {self.index_metadata.get('created_at', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"Error loading index: {e}")
            return False
    
    def search(self, query: str, top_k: int = 10, 
               similarity_threshold: float = 0.1,
               combine_methods: bool = True) -> List[Tuple[CodeFragment, float]]:
        """Search for semantically similar code fragments."""
        if not self.fragments or self.embeddings is None or self.model is None:
            return []
        
        # Create query embedding
        query_embedding = self.model.encode([query])
        
        # Calculate semantic similarity
        semantic_similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        results = []
        
        if combine_methods and self.tfidf_matrix is not None:
            # Combine with TF-IDF similarity
            query_tfidf = self.tfidf_vectorizer.transform([query])
            tfidf_similarities = cosine_similarity(query_tfidf, self.tfidf_matrix)[0]
            
            # Weighted combination (favor semantic similarity)
            combined_similarities = 0.7 * semantic_similarities + 0.3 * tfidf_similarities
            similarities = combined_similarities
        else:
            similarities = semantic_similarities
        
        # Get top results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        for idx in top_indices:
            if similarities[idx] >= similarity_threshold:
                results.append((self.fragments[idx], float(similarities[idx])))
        
        return results


class JiraCodeAnalyzer:
    """Analyzes JIRA tickets against TAL code index for relevant matches."""
    
    def __init__(self, index_loader: TALIndexLoader):
        self.index_loader = index_loader
        self.keyword_extractors = {
            'file_operations': ['file', 'read', 'write', 'copy', 'delete', 'move', 'archive', 'backup'],
            'database_operations': ['database', 'table', 'record', 'insert', 'update', 'select', 'query', 'customer'],
            'data_validation': ['validate', 'check', 'verify', 'sanitize', 'format', 'validate'],
            'error_handling': ['error', 'exception', 'handle', 'catch', 'log', 'audit', 'fail'],
            'calculation': ['calculate', 'compute', 'math', 'formula', 'total', 'sum', 'average', 'count'],
            'reporting': ['report', 'export', 'generate', 'format', 'display', 'print', 'output'],
            'security': ['secure', 'authenticate', 'authorize', 'permission', 'access', 'login'],
            'performance': ['optimize', 'performance', 'speed', 'efficient', 'fast', 'cache'],
            'date_time': ['date', 'time', 'timestamp', 'schedule', 'calendar', 'julian', 'year', 'month', 'day'],
            'cleanup': ['cleanup', 'clean', 'purge', 'remove', 'temp', 'temporary', 'old', 'maintenance']
        }
    
    def extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """Extract domain-specific keywords from text."""
        text_lower = text.lower()
        found_keywords = {}
        
        for domain, keywords in self.keyword_extractors.items():
            found = [kw for kw in keywords if kw in text_lower]
            if found:
                found_keywords[domain] = found
                
        return found_keywords
    
    def analyze_ticket(self, ticket: JiraTicket, 
                      similarity_threshold: float = 0.3,
                      max_results: int = 10) -> Dict[str, Any]:
        """Analyze JIRA ticket against code index."""
        
        # Get combined ticket text for semantic search
        ticket_text = ticket.get_combined_text()
        
        # Extract keywords for domain classification
        ticket_keywords = self.extract_keywords(ticket_text)
        
        # Perform semantic search
        search_results = self.index_loader.search(
            ticket_text, 
            top_k=max_results * 2,  # Get more results for filtering
            similarity_threshold=similarity_threshold
        )
        
        # Analyze each result
        code_matches = []
        for fragment, score in search_results:
            match = self._analyze_fragment_match(fragment, score, ticket, ticket_keywords)
            if match:
                code_matches.append(match)
        
        # Sort by relevance score
        code_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Limit to max_results
        code_matches = code_matches[:max_results]
        
        # Extract full procedures for highly relevant matches
        full_procedures = self._extract_full_procedures(code_matches, score_threshold=0.6)
        
        return {
            'ticket': ticket,
            'ticket_keywords': ticket_keywords,
            'code_matches': code_matches,
            'full_procedures': full_procedures,
            'summary': self._generate_analysis_summary(ticket, code_matches, ticket_keywords)
        }
    
    def _analyze_fragment_match(self, fragment: CodeFragment, score: float, 
                               ticket: JiraTicket, ticket_keywords: Dict[str, List[str]]) -> Optional[CodeMatch]:
        """Analyze why a fragment matches and extract relevant snippet."""
        
        # Extract keywords from fragment
        fragment_text = f"{fragment.content} {' '.join(fragment.comments)}"
        fragment_keywords = self.extract_keywords(fragment_text)
        
        # Find common keywords
        matching_keywords = []
        for domain in ticket_keywords:
            if domain in fragment_keywords:
                common = set(ticket_keywords[domain]) & set(fragment_keywords[domain])
                matching_keywords.extend(list(common))
        
        # Generate relevance reason
        relevance_reason = self._generate_relevance_reason(fragment, ticket_keywords, matching_keywords)
        
        # Extract most relevant code snippet (focus on key parts)
        code_snippet = self._extract_relevant_snippet(fragment, ticket.get_combined_text())
        
        return CodeMatch(
            fragment=fragment,
            similarity_score=score,
            matching_keywords=matching_keywords,
            relevance_reason=relevance_reason,
            code_snippet=code_snippet
        )
    
    def _generate_relevance_reason(self, fragment: CodeFragment, 
                                  ticket_keywords: Dict[str, List[str]], 
                                  matching_keywords: List[str]) -> str:
        """Generate explanation for why this fragment is relevant."""
        reasons = []
        
        if fragment.procedure_name:
            reasons.append(f"Procedure '{fragment.procedure_name}' found")
        
        if matching_keywords:
            reasons.append(f"Matches keywords: {', '.join(set(matching_keywords))}")
        
        if fragment.comments:
            reasons.append(f"Contains {len(fragment.comments)} relevant comments")
        
        # Check for specific patterns
        content_lower = fragment.content.lower()
        if 'error' in content_lower and 'handle' in content_lower:
            reasons.append("Contains error handling logic")
        
        if 'validate' in content_lower or 'check' in content_lower:
            reasons.append("Contains validation logic")
        
        if 'file' in content_lower and ('read' in content_lower or 'write' in content_lower):
            reasons.append("Contains file operations")
        
        return "; ".join(reasons) if reasons else "Semantic similarity match"
    
    def _extract_relevant_snippet(self, fragment: CodeFragment, ticket_text: str) -> str:
        """Extract the most relevant part of the code fragment."""
        lines = fragment.content.split('\n')
        
        # If it's a short fragment, return all
        if len(lines) <= 20:
            return fragment.content
        
        # For longer fragments, try to find most relevant section
        ticket_words = set(ticket_text.lower().split())
        line_scores = []
        
        for i, line in enumerate(lines):
            line_words = set(line.lower().split())
            common_words = len(ticket_words & line_words)
            line_scores.append((i, common_words))
        
        # Sort by relevance and get best section
        line_scores.sort(key=lambda x: x[1], reverse=True)
        
        if line_scores[0][1] > 0:  # If we found relevant lines
            best_line_idx = line_scores[0][0]
            # Extract context around the best line
            start = max(0, best_line_idx - 10)
            end = min(len(lines), best_line_idx + 10)
            snippet_lines = lines[start:end]
            
            if start > 0:
                snippet_lines.insert(0, "... (previous code)")
            if end < len(lines):
                snippet_lines.append("... (more code follows)")
                
            return '\n'.join(snippet_lines)
        else:
            # Return first 20 lines as fallback
            return '\n'.join(lines[:20] + ['... (truncated)'])
    
    def _extract_full_procedures(self, code_matches: List[CodeMatch], 
                                score_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """Extract full procedures for high-scoring matches."""
        full_procedures = []
        
        for match in code_matches:
            if match.similarity_score >= score_threshold and match.fragment.procedure_name:
                # Get the full procedure content
                full_proc = {
                    'procedure_name': match.fragment.procedure_name,
                    'file_path': match.fragment.file_path,
                    'full_content': match.fragment.content,
                    'similarity_score': match.similarity_score,
                    'relevance_reason': match.relevance_reason,
                    'line_range': f"{match.fragment.start_line}-{match.fragment.end_line}",
                    'comments': match.fragment.comments,
                    'variables': match.fragment.variables
                }
                full_procedures.append(full_proc)
        
        return full_procedures
    
    def _generate_analysis_summary(self, ticket: JiraTicket, 
                                  code_matches: List[CodeMatch],
                                  ticket_keywords: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate analysis summary."""
        
        # Count matches by domain
        domain_matches = {}
        for match in code_matches:
            for keyword in match.matching_keywords:
                for domain, keywords in self.keyword_extractors.items():
                    if keyword in keywords:
                        domain_matches[domain] = domain_matches.get(domain, 0) + 1
        
        # Get top procedures
        top_procedures = [m.fragment.procedure_name for m in code_matches 
                         if m.fragment.procedure_name][:5]
        
        return {
            'total_matches': len(code_matches),
            'avg_similarity': sum(m.similarity_score for m in code_matches) / len(code_matches) if code_matches else 0,
            'domains_found': list(domain_matches.keys()),
            'top_procedures': top_procedures,
            'ticket_keywords': ticket_keywords,
            'high_confidence_matches': len([m for m in code_matches if m.similarity_score > 0.7])
        }
    
    def format_for_llm(self, analysis_result: Dict[str, Any]) -> str:
        """Format the analysis results for LLM consumption."""
        
        ticket = analysis_result['ticket']
        code_matches = analysis_result['code_matches']
        full_procedures = analysis_result['full_procedures']
        summary = analysis_result['summary']
        
        # Build formatted output
        output = []
        output.append("="*80)
        output.append("JIRA TICKET ANALYSIS FOR LLM PROCESSING")
        output.append("="*80)
        
        # Ticket Information
        output.append(f"\nTICKET: {ticket.ticket_id}")
        output.append(f"TITLE: {ticket.title}")
        output.append(f"PRIORITY: {ticket.priority}")
        
        output.append(f"\nDESCRIPTION:")
        output.append(ticket.description)
        
        if ticket.acceptance_criteria:
            output.append(f"\nACCEPTANCE CRITERIA:")
            for i, criteria in enumerate(ticket.acceptance_criteria, 1):
                output.append(f"{i}. {criteria}")
        
        # Analysis Summary
        output.append(f"\nANALYSIS SUMMARY:")
        output.append(f"- Total code matches found: {summary['total_matches']}")
        output.append(f"- Average similarity score: {summary['avg_similarity']:.3f}")
        output.append(f"- High confidence matches: {summary['high_confidence_matches']}")
        output.append(f"- Relevant domains: {', '.join(summary['domains_found'])}")
        output.append(f"- Top procedures: {', '.join(summary['top_procedures'])}")
        
        # Full Procedures (High Relevance)
        if full_procedures:
            output.append(f"\n" + "="*60)
            output.append("FULL PROCEDURES (HIGH RELEVANCE)")
            output.append("="*60)
            
            for i, proc in enumerate(full_procedures, 1):
                output.append(f"\n{i}. PROCEDURE: {proc['procedure_name']}")
                output.append(f"   FILE: {proc['file_path']}")
                output.append(f"   LINES: {proc['line_range']}")
                output.append(f"   SIMILARITY: {proc['similarity_score']:.3f}")
                output.append(f"   RELEVANCE: {proc['relevance_reason']}")
                output.append(f"\n   FULL CODE:")
                output.append("   " + "-"*50)
                for line in proc['full_content'].split('\n'):
                    output.append(f"   {line}")
                output.append("   " + "-"*50)
        
        # Code Snippets
        output.append(f"\n" + "="*60)
        output.append("RELEVANT CODE SNIPPETS")
        output.append("="*60)
        
        for i, match in enumerate(code_matches[:10], 1):  # Limit to top 10
            output.append(f"\n{i}. MATCH SCORE: {match.similarity_score:.3f}")
            output.append(f"   FILE: {match.fragment.file_path}")
            output.append(f"   LINES: {match.fragment.start_line}-{match.fragment.end_line}")
            
            if match.fragment.procedure_name:
                output.append(f"   PROCEDURE: {match.fragment.procedure_name}")
            
            output.append(f"   RELEVANCE: {match.relevance_reason}")
            output.append(f"   KEYWORDS: {', '.join(match.matching_keywords)}")
            
            output.append(f"\n   CODE SNIPPET:")
            output.append("   " + "-"*40)
            for line in match.code_snippet.split('\n'):
                output.append(f"   {line}")
            output.append("   " + "-"*40)
        
        # Instructions for LLM
        output.append(f"\n" + "="*60)
        output.append("INSTRUCTIONS FOR LLM")
        output.append("="*60)
        output.append("\nPlease analyze the above JIRA ticket requirements and TAL code matches to:")
        output.append("1. Identify which existing procedures can be reused or modified")
        output.append("2. Suggest implementation approach based on similar existing code")
        output.append("3. Highlight any gaps where new code needs to be written")
        output.append("4. Recommend best practices based on the existing codebase patterns")
        output.append("5. Estimate development effort based on complexity of similar existing code")
        output.append("6. Provide specific code modifications or new procedures needed")
        
        return '\n'.join(output)


def parse_jira_ticket() -> JiraTicket:
    """Interactive function to create a JIRA ticket."""
    print("\n=== JIRA Ticket Input ===")
    
    ticket_id = input("Enter JIRA Ticket ID (e.g., PROJ-123): ").strip()
    title = input("Enter ticket title: ").strip()
    
    print("\nEnter ticket description (press Enter twice when done):")
    description_lines = []
    empty_line_count = 0
    
    while True:
        line = input()
        if line == "":
            empty_line_count += 1
            if empty_line_count >= 2:
                break
            description_lines.append(line)
        else:
            empty_line_count = 0
            description_lines.append(line)
    
    # Remove trailing empty lines
    while description_lines and description_lines[-1] == "":
        description_lines.pop()
    
    description = '\n'.join(description_lines)
    
    print("\nEnter acceptance criteria (one per line, empty line to finish):")
    acceptance_criteria = []
    while True:
        criteria = input(f"  {len(acceptance_criteria) + 1}. ").strip()
        if not criteria:
            break
        acceptance_criteria.append(criteria)
    
    priority = input("Enter priority (Low/Medium/High) [Medium]: ").strip() or "Medium"
    
    return JiraTicket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
        priority=priority
    )


def load_jira_from_file(file_path: str) -> Optional[JiraTicket]:
    """Load JIRA ticket from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return JiraTicket(
            ticket_id=data['ticket_id'],
            title=data['title'],
            description=data['description'],
            acceptance_criteria=data.get('acceptance_criteria', []),
            priority=data.get('priority', 'Medium')
        )
    except Exception as e:
        print(f"Error loading JIRA ticket from file: {e}")
        return None


def save_jira_template(file_path: str):
    """Save a JIRA ticket template JSON file."""
    template = {
        "ticket_id": "PROJ-123",
        "title": "Example ticket title",
        "description": "Detailed description of the requirement...",
        "acceptance_criteria": [
            "First acceptance criteria",
            "Second acceptance criteria",
            "Third acceptance criteria"
        ],
        "priority": "Medium"
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)
    
    print(f"JIRA ticket template saved to: {file_path}")


def main():
    """Main searcher application."""
    
    print("="*60)
    print("TAL JIRA TICKET SEARCHER")
    print("="*60)
    
    # Initialize index loader
    index_loader = TALIndexLoader()
    
    # Load index
    while True:
        index_file = input("Enter path to TAL index file (default: tal_semantic_index.pkl): ").strip()
        if not index_file:
            index_file = "tal_semantic_index.pkl"
        
        if os.path.exists(index_file):
            if index_loader.load_index(index_file):
                break
            else:
                print("Failed to load index. Please try again.")
        else:
            print(f"Index file not found: {index_file}")
            print("Please run the TAL indexer first to create an index.")
            
            create_choice = input("Would you like to specify a different path? (y/n): ").strip().lower()
            if create_choice not in ['y', 'yes']:
                return
    
    # Initialize analyzer
    analyzer = JiraCodeAnalyzer(index_loader)
    
    print("\n=== TAL JIRA Ticket Analysis ===")
    
    while True:
        print("\nChoose an option:")
        print("1. Analyze JIRA ticket (interactive input)")
        print("2. Analyze JIRA ticket from JSON file")
        print("3. Create JIRA ticket template")
        print("4. Simple code search")
        print("5. View index statistics")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            # Interactive JIRA ticket input
            ticket = parse_jira_ticket()
            
            print(f"\nAnalyzing ticket {ticket.ticket_id} against TAL codebase...")
            
            # Get analysis parameters
            threshold = input("Enter similarity threshold (0.0-1.0, default: 0.2): ").strip()
            try:
                threshold = float(threshold) if threshold else 0.2
            except ValueError:
                threshold = 0.2
            
            max_results = input("Enter max results (default: 15): ").strip()
            try:
                max_results = int(max_results) if max_results else 15
            except ValueError:
                max_results = 15
            
            # Perform analysis
            analysis_result = analyzer.analyze_ticket(
                ticket, 
                similarity_threshold=threshold, 
                max_results=max_results
            )
            
            # Format for LLM
            llm_output = analyzer.format_for_llm(analysis_result)
            
            # Save to file
            output_filename = f"jira_analysis_{ticket.ticket_id.replace('-', '_')}.txt"
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(llm_output)
            
            print(f"\nAnalysis complete! Results saved to: {output_filename}")
            print("\nSummary:")
            summary = analysis_result['summary']
            print(f"- Found {summary['total_matches']} relevant code matches")
            print(f"- Average similarity: {summary['avg_similarity']:.3f}")
            print(f"- High confidence matches: {summary['high_confidence_matches']}")
            print(f"- Relevant domains: {', '.join(summary['domains_found']) if summary['domains_found'] else 'None'}")
            
            # Show preview
            if analysis_result['code_matches']:
                print(f"\nTop 3 matches preview:")
                for i, match in enumerate(analysis_result['code_matches'][:3], 1):
                    print(f"\n{i}. {match.fragment.procedure_name or 'Code Fragment'}")
                    print(f"   File: {match.fragment.file_path}")
                    print(f"   Similarity: {match.similarity_score:.3f}")
                    print(f"   Reason: {match.relevance_reason}")
        
        elif choice == "2":
            # Load JIRA ticket from file
            file_path = input("Enter path to JIRA JSON file: ").strip()
            
            if os.path.exists(file_path):
                ticket = load_jira_from_file(file_path)
                if ticket:
                    print(f"\nLoaded ticket: {ticket.ticket_id} - {ticket.title}")
                    
                    # Perform analysis with default parameters
                    analysis_result = analyzer.analyze_ticket(ticket, similarity_threshold=0.2, max_results=15)
                    
                    # Format for LLM
                    llm_output = analyzer.format_for_llm(analysis_result)
                    
                    # Save to file
                    output_filename = f"jira_analysis_{ticket.ticket_id.replace('-', '_')}.txt"
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        f.write(llm_output)
                    
                    print(f"Analysis complete! Results saved to: {output_filename}")
            else:
                print(f"File not found: {file_path}")
        
        elif choice == "3":
            # Create JIRA template
            template_path = input("Enter path for template file (default: jira_template.json): ").strip()
            if not template_path:
                template_path = "jira_template.json"
            
            save_jira_template(template_path)
        
        elif choice == "4":
            # Simple code search
            while True:
                query = input("\nEnter search query (empty to return to menu): ").strip()
                if not query:
                    break
                
                results = index_loader.search(query, top_k=5)
                
                if results:
                    print(f"\nFound {len(results)} similar code fragments:")
                    for i, (fragment, score) in enumerate(results, 1):
                        print(f"\n{i}. Similarity: {score:.3f}")
                        print(f"   File: {fragment.file_path}")
                        print(f"   Lines: {fragment.start_line}-{fragment.end_line}")
                        if fragment.procedure_name:
                            print(f"   Procedure: {fragment.procedure_name}")
                        
                        # Show first few lines of code
                        code_lines = fragment.content.split('\n')[:3]
                        print(f"   Code preview:")
                        for line in code_lines:
                            print(f"     {line}")
                        print("     ...")
                else:
                    print("No similar code fragments found.")
        
        elif choice == "5":
            # View index statistics  
            if hasattr(index_loader, 'index_metadata') and index_loader.index_metadata:
                print("\n" + "="*40)
                print("INDEX STATISTICS")
                print("="*40)
                print(f"Total fragments: {len(index_loader.fragments)}")
                print(f"Total files: {index_loader.index_metadata.get('total_files', 'unknown')}")
                print(f"Model used: {index_loader.index_metadata.get('model_name', 'unknown')}")
                print(f"Created at: {index_loader.index_metadata.get('created_at', 'unknown')}")
                
                # Count procedures and functions
                procedures = sum(1 for f in index_loader.fragments if f.procedure_name)
                functions = sum(1 for f in index_loader.fragments if f.function_name)
                print(f"Procedures found: {procedures}")
                print(f"Functions found: {functions}")
            else:
                print("No index statistics available.")
        
        elif choice == "6":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    # Check required packages
    import subprocess
    import sys
    
    required_packages = [
        "sentence-transformers",
        "scikit-learn", 
        "numpy"
    ]
    
    print("Checking required packages...")
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        install_choice = input("Install missing packages? (y/n): ").strip().lower()
        if install_choice in ['y', 'yes']:
            for package in missing_packages:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        else:
            print("Cannot proceed without required packages.")
            exit(1)
    
    main()
