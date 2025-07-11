#!/usr/bin/env python3
"""
Standalone TAL Code Searcher

This is a standalone searcher that uses only sklearn for similarity search.
Accepts JIRA-style requirements and finds relevant TAL code fragments.
"""

import os
import pickle
import json
import sys
from pathlib import Path

# Check and install required packages
def check_packages():
    required = ['scikit-learn', 'numpy']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        import subprocess
        for pkg in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

check_packages()

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class CodeFragment:
    """Represents a fragment of TAL code with metadata."""
    def __init__(self, file_path, start_line, end_line, content, 
                 procedure_name=None, function_name=None, comments=None, variables=None):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.procedure_name = procedure_name
        self.function_name = function_name
        self.comments = comments or []
        self.variables = variables or []

class RequirementInput:
    """Represents user requirements (JIRA-style)."""
    def __init__(self, ticket_id, title, description, acceptance_criteria):
        self.ticket_id = ticket_id
        self.title = title
        self.description = description
        self.acceptance_criteria = acceptance_criteria
    
    def get_combined_text(self):
        """Combine all requirement text for analysis."""
        combined = f"{self.title}\n\n{self.description}\n\n"
        if self.acceptance_criteria:
            combined += "Acceptance Criteria:\n"
            for i, criteria in enumerate(self.acceptance_criteria, 1):
                combined += f"{i}. {criteria}\n"
        return combined

class CodeMatch:
    """Represents a matching code fragment with analysis."""
    def __init__(self, fragment, similarity_score, matching_keywords, relevance_reason):
        self.fragment = fragment
        self.similarity_score = similarity_score
        self.matching_keywords = matching_keywords
        self.relevance_reason = relevance_reason

class StandaloneTALSearcher:
    """Standalone TAL code searcher using sklearn only."""
    
    def __init__(self):
        self.fragments = []
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.code_vectorizer = None
        self.code_matrix = None
        self.metadata = {}
        
        # Domain-specific keywords for wire processing and financial systems
        self.keyword_domains = {
            'iso20022_messages': ['iso20022', 'iso 20022', 'pacs', 'camt', 'pain', 'head', 'grphdr', 'msgid', 'crdt', 'dbtr', 'cdtr', 'instrid', 'endtoendid', 'txid', 'remittance', 'structured', 'unstructured'],
            'swift_messages': ['swift', 'mt103', 'mt202', 'mt200', 'mt210', 'mt900', 'mt910', 'mt940', 'mt950', 'fin', 'swiftnet', 'rma', 'uetr', 'gpi', 'tracker', 'field20', 'field32a', 'field50k', 'field59', 'field70', 'field71a', 'field72'],
            'payment_types': ['cover', 'payment', 'wire', 'transfer', 'drawdown', 'bulk', 'batch', 'individual', 'book', 'transfer', 'ach', 'fedwire', 'chips', 'target2', 'sepa', 'domestic', 'international', 'cross', 'border'],
            'payment_validation': ['validation', 'validate', 'sanction', 'screening', 'ofac', 'kyc', 'aml', 'duplicate', 'check', 'verify', 'compliance', 'regulatory', 'format', 'field', 'mandatory', 'optional', 'conditional', 'cutoff', 'time'],
            'financial_networks': ['fed', 'federal', 'reserve', 'chips', 'clearing', 'house', 'swift', 'correspondent', 'nostro', 'vostro', 'intermediary', 'bank', 'routing', 'aba', 'bic', 'iban', 'sort', 'code', 'participant', 'member'],
            'funds_liquidity': ['funds', 'liquidity', 'balance', 'available', 'reserve', 'overdraft', 'credit', 'limit', 'insufficient', 'collateral', 'margin', 'exposure', 'settlement', 'prefund', 'postfund', 'intraday', 'daylight'],
            'settlement_timing': ['settlement', 'value', 'date', 'future', 'dated', 'same', 'day', 'next', 'cut', 'off', 'real', 'time', 'rtgs', 'deferred', 'net', 'gross', 'batch', 'continuous', 'window', 'deadline'],
            'message_routing': ['routing', 'route', 'destination', 'intermediary', 'correspondent', 'chain', 'path', 'hop', 'relay', 'forward', 'direct', 'indirect', 'via', 'through', 'network', 'queue', 'priority'],
            'split_advising': ['split', 'advice', 'partial', 'remainder', 'portion', 'allocate', 'distribute', 'breakdown', 'segment', 'fraction', 'multiple', 'beneficiary', 'leg', 'component', 'division'],
            'warehouse_processing': ['warehouse', 'store', 'staging', 'queue', 'batch', 'bulk', 'group', 'consolidate', 'aggregate', 'collect', 'release', 'hold', 'pending', 'defer', 'schedule', 'timer', 'trigger'],
            'gsmos_operations': ['gsmos', 'global', 'standard', 'management', 'operating', 'system', 'maintenance', 'repair', 'configuration', 'parameter', 'setting', 'profile', 'template', 'workflow', 'process'],
            'regulatory_compliance': ['regulation', 'compliance', 'audit', 'trail', 'log', 'monitor', 'report', 'exception', 'alert', 'threshold', 'limit', 'breach', 'violation', 'investigation', 'documentation'],
            'error_handling': ['error', 'exception', 'reject', 'return', 'repair', 'retry', 'timeout', 'fail', 'recovery', 'rollback', 'compensate', 'manual', 'intervention', 'escalation', 'notification'],
            'currency_fx': ['currency', 'foreign', 'exchange', 'fx', 'rate', 'conversion', 'cross', 'rate', 'base', 'quote', 'spread', 'markup', 'usd', 'eur', 'gbp', 'jpy', 'cad', 'aud', 'chf'],
            'account_management': ['account', 'customer', 'beneficiary', 'ordering', 'party', 'debtor', 'creditor', 'ultimate', 'originator', 'receiver', 'agent', 'institution', 'branch', 'subsidiary'],
            'charges_fees': ['charge', 'fee', 'commission', 'cost', 'expense', 'our', 'ben', 'sha', 'shared', 'bearer', 'waive', 'discount', 'premium', 'markup', 'spread'],
            'security_encryption': ['security', 'encrypt', 'decrypt', 'digital', 'signature', 'certificate', 'authentication', 'authorization', 'token', 'key', 'hash', 'checksum', 'integrity'],
            'database_operations': ['database', 'table', 'record', 'insert', 'update', 'select', 'delete', 'query', 'index', 'constraint', 'transaction', 'commit', 'rollback', 'lock', 'deadlock'],
            'file_operations': ['file', 'read', 'write', 'copy', 'move', 'delete', 'archive', 'backup', 'restore', 'import', 'export', 'parse', 'format', 'convert', 'transform'],
            'status_lifecycle': ['status', 'state', 'pending', 'processing', 'complete', 'failed', 'cancelled', 'expired', 'hold', 'release', 'approve', 'reject', 'return', 'repair'],
            'reporting_analytics': ['report', 'analytics', 'statistics', 'metrics', 'kpi', 'dashboard', 'summary', 'detail', 'exception', 'trend', 'volume', 'performance', 'sla'],
            'integration_apis': ['api', 'interface', 'integration', 'endpoint', 'service', 'microservice', 'rest', 'soap', 'xml', 'json', 'message', 'queue', 'broker', 'publish', 'subscribe']
        }
    
    def load_index(self, index_file_path):
        """Load TAL index from file."""
        try:
            print(f"Loading TAL index from {index_file_path}...")
            
            with open(index_file_path, 'rb') as f:
                index_data = pickle.load(f)
            
            self.fragments = index_data['fragments']
            self.tfidf_vectorizer = index_data['tfidf_vectorizer']
            self.tfidf_matrix = index_data['tfidf_matrix']
            self.code_vectorizer = index_data.get('code_vectorizer')
            self.code_matrix = index_data.get('code_matrix')
            self.metadata = index_data.get('metadata', {})
            
            print(f"✅ Index loaded successfully!")
            print(f"   - {len(self.fragments)} code fragments")
            print(f"   - {self.metadata.get('total_files', 'unknown')} files")
            print(f"   - Created: {self.metadata.get('created_at', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            return False
    
    def extract_keywords(self, text):
        """Extract domain-specific keywords from text."""
        text_lower = text.lower()
        found_keywords = {}
        
        for domain, keywords in self.keyword_domains.items():
            found = [kw for kw in keywords if kw in text_lower]
            if found:
                found_keywords[domain] = found
        
        return found_keywords
    
    def search_similar_code(self, requirement, similarity_threshold=0.1, max_results=10):
        """Search for code fragments similar to the requirement."""
        if not self.fragments or self.tfidf_matrix is None:
            print("❌ No index loaded. Please load an index first.")
            return []
        
        # Get combined requirement text
        requirement_text = requirement.get_combined_text()
        
        # Extract keywords for domain analysis
        requirement_keywords = self.extract_keywords(requirement_text)
        
        # Transform requirement using TF-IDF
        try:
            query_tfidf = self.tfidf_vectorizer.transform([requirement_text])
            tfidf_similarities = cosine_similarity(query_tfidf, self.tfidf_matrix)[0]
        except Exception as e:
            print(f"❌ Error in TF-IDF search: {e}")
            return []
        
        # Add code-specific similarity if available
        if self.code_matrix is not None and self.code_vectorizer is not None:
            try:
                query_code = self.code_vectorizer.transform([requirement_text])
                code_similarities = cosine_similarity(query_code, self.code_matrix)[0]
                
                # Combine similarities (70% general text, 30% code-specific)
                combined_similarities = 0.7 * tfidf_similarities + 0.3 * code_similarities
            except Exception:
                combined_similarities = tfidf_similarities
        else:
            combined_similarities = tfidf_similarities
        
        # Get top results
        top_indices = np.argsort(combined_similarities)[::-1][:max_results * 2]  # Get extra for filtering
        
        # Analyze matches
        matches = []
        for idx in top_indices:
            if combined_similarities[idx] >= similarity_threshold:
                fragment = self.fragments[idx]
                score = float(combined_similarities[idx])
                
                # Analyze the match
                match_analysis = self._analyze_match(fragment, requirement, requirement_keywords, score)
                if match_analysis:
                    matches.append(match_analysis)
        
        # Sort by score and limit results
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:max_results]
    
    def _analyze_match(self, fragment, requirement, requirement_keywords, score):
        """Analyze why a fragment matches the requirement."""
        
        # Extract keywords from fragment
        fragment_text = f"{fragment.content} {' '.join(fragment.comments)}"
        fragment_keywords = self.extract_keywords(fragment_text)
        
        # Find matching keywords
        matching_keywords = []
        for domain in requirement_keywords:
            if domain in fragment_keywords:
                common = set(requirement_keywords[domain]) & set(fragment_keywords[domain])
                matching_keywords.extend(list(common))
        
        # Generate relevance explanation
        relevance_reasons = []
        
        if fragment.procedure_name:
            relevance_reasons.append(f"Procedure '{fragment.procedure_name}'")
        
        if matching_keywords:
            relevance_reasons.append(f"Keywords: {', '.join(set(matching_keywords))}")
        
        if fragment.comments:
            # Check if comments contain requirement-related terms
            req_words = set(requirement.get_combined_text().lower().split())
            comment_words = set(' '.join(fragment.comments).lower().split())
            common_comment_words = req_words & comment_words
            if len(common_comment_words) > 2:
                relevance_reasons.append(f"Comment overlap ({len(common_comment_words)} terms)")
        
        # Check for specific patterns
        content_lower = fragment.content.lower()
        if any(word in content_lower for word in ['error', 'validate', 'check']):
            if any(word in requirement.get_combined_text().lower() for word in ['validate', 'check', 'verify']):
                relevance_reasons.append("Validation/error handling logic")
        
        relevance_reason = "; ".join(relevance_reasons) if relevance_reasons else "Text similarity match"
        
        return CodeMatch(
            fragment=fragment,
            similarity_score=score,
            matching_keywords=list(set(matching_keywords)),
            relevance_reason=relevance_reason
        )
    
    def display_search_results(self, matches, requirement, show_full_code=False):
        """Display search results in a formatted way."""
        print(f"\n" + "="*80)
        print(f"SEARCH RESULTS FOR: {requirement.ticket_id}")
        print("="*80)
        
        print(f"REQUIREMENT:")
        print(f"Title: {requirement.title}")
        print(f"Description: {requirement.description}")
        
        if requirement.acceptance_criteria:
            print(f"Acceptance Criteria:")
            for i, criteria in enumerate(requirement.acceptance_criteria, 1):
                print(f"  {i}. {criteria}")
        
        if not matches:
            print(f"\n❌ No matching code fragments found.")
            return
        
        print(f"\n📊 FOUND {len(matches)} RELEVANT CODE FRAGMENTS:")
        print("="*80)
        
        for i, match in enumerate(matches, 1):
            fragment = match.fragment
            print(f"\n{i}. SIMILARITY SCORE: {match.similarity_score:.3f}")
            print(f"   FILE: {os.path.basename(fragment.file_path)}")
            print(f"   LINES: {fragment.start_line}-{fragment.end_line}")
            
            if fragment.procedure_name:
                print(f"   PROCEDURE: {fragment.procedure_name}")
            if fragment.function_name:
                print(f"   FUNCTION: {fragment.function_name}")
            
            print(f"   RELEVANCE: {match.relevance_reason}")
            
            if match.matching_keywords:
                print(f"   KEYWORDS: {', '.join(match.matching_keywords)}")
            
            if fragment.comments:
                print(f"   COMMENTS:")
                for comment in fragment.comments[:3]:  # Show first 3 comments
                    print(f"     ! {comment}")
                if len(fragment.comments) > 3:
                    print(f"     ... and {len(fragment.comments) - 3} more comments")
            
            print(f"\n   CODE:")
            print("   " + "-"*60)
            
            if show_full_code:
                # Show complete code with line numbers
                for line_num, line in enumerate(fragment.content.split('\n'), fragment.start_line):
                    print(f"   {line_num:4d}: {line}")
            else:
                # Show preview (first 12 lines)
                lines = fragment.content.split('\n')
                preview_lines = lines[:12]
                
                for line_num, line in enumerate(preview_lines, fragment.start_line):
                    print(f"   {line_num:4d}: {line}")
                
                if len(lines) > 12:
                    remaining = len(lines) - 12
                    print(f"   ... ({remaining} more lines)")
            
            print("   " + "-"*60)
        
        print(f"\n📋 SUMMARY:")
        print(f"   - Total matches: {len(matches)}")
        print(f"   - Average similarity: {sum(m.similarity_score for m in matches) / len(matches):.3f}")
        high_confidence = len([m for m in matches if m.similarity_score > 0.5])
        print(f"   - High confidence matches (>0.5): {high_confidence}")
    
    def generate_llm_report(self, matches, requirement, output_file=None):
        """Generate a report formatted for LLM consumption."""
        
        report_lines = []
        report_lines.append("="*80)
        report_lines.append("TAL CODE ANALYSIS REPORT FOR LLM")
        report_lines.append("="*80)
        
        # Requirement section
        report_lines.append(f"\nREQUIREMENT DETAILS:")
        report_lines.append(f"Ticket ID: {requirement.ticket_id}")
        report_lines.append(f"Title: {requirement.title}")
        report_lines.append(f"\nDescription:")
        report_lines.append(requirement.description)
        
        if requirement.acceptance_criteria:
            report_lines.append(f"\nAcceptance Criteria:")
            for i, criteria in enumerate(requirement.acceptance_criteria, 1):
                report_lines.append(f"{i}. {criteria}")
        
        # Analysis section
        if matches:
            report_lines.append(f"\nANALYSIS RESULTS:")
            report_lines.append(f"- Found {len(matches)} relevant code fragments")
            avg_sim = sum(m.similarity_score for m in matches) / len(matches)
            report_lines.append(f"- Average similarity score: {avg_sim:.3f}")
            high_conf = len([m for m in matches if m.similarity_score > 0.5])
            report_lines.append(f"- High confidence matches: {high_conf}")
            
            # Top procedures
            procedures = [m.fragment.procedure_name for m in matches[:5] if m.fragment.procedure_name]
            if procedures:
                report_lines.append(f"- Top procedures: {', '.join(procedures)}")
            
            report_lines.append(f"\n" + "="*60)
            report_lines.append("RELEVANT CODE FRAGMENTS")
            report_lines.append("="*60)
            
            for i, match in enumerate(matches, 1):
                fragment = match.fragment
                report_lines.append(f"\n{i}. MATCH SCORE: {match.similarity_score:.3f}")
                report_lines.append(f"   FILE: {fragment.file_path}")
                report_lines.append(f"   LINES: {fragment.start_line}-{fragment.end_line}")
                
                if fragment.procedure_name:
                    report_lines.append(f"   PROCEDURE: {fragment.procedure_name}")
                
                report_lines.append(f"   RELEVANCE: {match.relevance_reason}")
                
                if match.matching_keywords:
                    report_lines.append(f"   KEYWORDS: {', '.join(match.matching_keywords)}")
                
                report_lines.append(f"\n   FULL CODE:")
                report_lines.append("   " + "-"*50)
                for line in fragment.content.split('\n'):
                    report_lines.append(f"   {line}")
                report_lines.append("   " + "-"*50)
        else:
            report_lines.append(f"\nNo relevant code fragments found.")
        
        # LLM instructions
        report_lines.append(f"\n" + "="*60)
        report_lines.append("INSTRUCTIONS FOR LLM ANALYSIS")
        report_lines.append("="*60)
        report_lines.append("Please analyze the requirement and matching TAL code to:")
        report_lines.append("1. Identify which existing procedures can be reused or adapted")
        report_lines.append("2. Suggest implementation approach based on similar patterns")
        report_lines.append("3. Highlight gaps where new code development is needed")
        report_lines.append("4. Recommend best practices from the existing codebase")
        report_lines.append("5. Estimate development effort based on code complexity")
        report_lines.append("6. Provide specific code modifications or new procedures needed")
        
        report_content = '\n'.join(report_lines)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"\n📄 Report saved to: {output_file}")
            except Exception as e:
                print(f"❌ Error saving report: {e}")
        
        return report_content

def get_user_requirement():
    """Interactive function to get requirement from user."""
    print(f"\n" + "="*60)
    print("ENTER REQUIREMENT DETAILS")
    print("="*60)
    
    # Get basic info
    ticket_id = input("Ticket ID (e.g., PROJ-123): ").strip()
    if not ticket_id:
        ticket_id = "REQ-001"
    
    title = input("Requirement title: ").strip()
    
    # Get multi-line description
    print(f"\nEnter requirement description (press Enter twice when done):")
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
    
    # Get acceptance criteria
    print(f"\nEnter acceptance criteria (one per line, empty line to finish):")
    acceptance_criteria = []
    while True:
        criteria = input(f"  {len(acceptance_criteria) + 1}. ").strip()
        if not criteria:
            break
        acceptance_criteria.append(criteria)
    
    return RequirementInput(ticket_id, title, description, acceptance_criteria)

def main():
    """Main searcher application."""
    print("="*60)
    print("STANDALONE TAL CODE SEARCHER")
    print("="*60)
    
    # Load index
    if len(sys.argv) > 1:
        index_file = sys.argv[1]
    else:
        index_file = input("Enter path to TAL index file (*.pkl): ").strip()
    
    if not os.path.exists(index_file):
        print(f"❌ Error: Index file not found: {index_file}")
        return False
    
    # Initialize searcher and load index
    searcher = StandaloneTALSearcher()
    if not searcher.load_index(index_file):
        return False
    
    while True:
        print(f"\n" + "="*60)
        print("SEARCH OPTIONS")
        print("="*60)
        print("1. Enter new requirement and search")
        print("2. Quick text search")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Full requirement analysis
            requirement = get_user_requirement()
            
            # Search parameters
            try:
                threshold = input(f"\nSimilarity threshold (0.0-1.0, default: 0.1): ").strip()
                threshold = float(threshold) if threshold else 0.1
            except ValueError:
                threshold = 0.1
            
            try:
                max_results = input(f"Max results (default: 8): ").strip()
                max_results = int(max_results) if max_results else 8
            except ValueError:
                max_results = 8
            
            # Perform search
            print(f"\n🔍 Searching for relevant TAL code...")
            matches = searcher.search_similar_code(requirement, threshold, max_results)
            
            # Display results
            show_full = input("Show full code in results? (y/n, default: n): ").strip().lower()
            searcher.display_search_results(matches, requirement, show_full in ['y', 'yes'])
            
            # Generate LLM report
            if matches:
                save_report = input(f"\nGenerate LLM report? (y/n): ").strip().lower()
                if save_report in ['y', 'yes']:
                    report_file = f"tal_analysis_{requirement.ticket_id.replace('-', '_')}.txt"
                    searcher.generate_llm_report(matches, requirement, report_file)
        
        elif choice == "2":
            # Quick text search
            query = input("\nEnter search text: ").strip()
            if query:
                # Create a simple requirement
                simple_req = RequirementInput("SEARCH-001", "Quick Search", query, [])
                
                matches = searcher.search_similar_code(simple_req, 0.05, 5)
                searcher.display_search_results(matches, simple_req, False)
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
