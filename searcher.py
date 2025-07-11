#!/usr/bin/env python3
"""
TAL Corpus Searcher

Loads pre-built TAL corpus indexes and provides semantic search functionality.
Supports JIRA-style requirements and advanced query capabilities.
"""

import os
import re
import json
import pickle
import math
import sys
from collections import Counter, defaultdict

class SearchResult:
    """Represents a search result with scoring details."""
    def __init__(self, chunk, similarity_score, match_reasons=None):
        self.chunk = chunk
        self.similarity_score = similarity_score
        self.match_reasons = match_reasons or []
        self.keyword_matches = []
        self.topic_relevance = 0.0

class JiraTicket:
    """Represents a JIRA ticket for requirements analysis."""
    def __init__(self, ticket_id, title, description, acceptance_criteria=None):
        self.ticket_id = ticket_id
        self.title = title
        self.description = description
        self.acceptance_criteria = acceptance_criteria or []
    
    def get_combined_text(self):
        """Get combined text for analysis."""
        combined = f"{self.title}\n\n{self.description}\n\n"
        if self.acceptance_criteria:
            combined += "Acceptance Criteria:\n"
            for i, criteria in enumerate(self.acceptance_criteria, 1):
                combined += f"{i}. {criteria}\n"
        return combined

class CorpusSearcher:
    """Advanced search functionality for TAL corpus."""
    
    def __init__(self):
        self.chunks = []
        self.vectorizer_data = {}
        self.stats = {}
        self.corpus_metadata = {}
        
        # Wire processing domain keywords for enhanced search
        self.domain_keywords = {
            'iso20022_messages': ['iso20022', 'iso', 'pacs', 'camt', 'pain', 'grphdr', 'msgid', 'crdt', 'dbtr', 'cdtr'],
            'swift_messages': ['swift', 'mt103', 'mt202', 'mt200', 'mt210', 'mt940', 'fin', 'swiftnet', 'field20', 'field32a', 'field59'],
            'payment_processing': ['payment', 'transfer', 'wire', 'cover', 'drawdown', 'bulk', 'batch', 'individual'],
            'compliance_screening': ['sanctions', 'screening', 'ofac', 'kyc', 'aml', 'compliance', 'validation', 'check'],
            'financial_networks': ['fed', 'federal', 'reserve', 'chips', 'clearing', 'correspondent', 'nostro', 'vostro'],
            'funds_liquidity': ['funds', 'liquidity', 'balance', 'available', 'reserve', 'overdraft', 'credit', 'limit'],
            'settlement_timing': ['settlement', 'value', 'date', 'future', 'same', 'day', 'rtgs', 'real', 'time'],
            'message_routing': ['routing', 'route', 'destination', 'intermediary', 'correspondent', 'chain', 'path'],
            'file_operations': ['file', 'read', 'write', 'copy', 'delete', 'move', 'archive', 'backup'],
            'database_operations': ['database', 'table', 'record', 'insert', 'update', 'select', 'query'],
            'error_handling': ['error', 'exception', 'handle', 'catch', 'log', 'audit', 'fail', 'retry'],
            'validation': ['validate', 'check', 'verify', 'sanitize', 'format', 'mandatory', 'optional']
        }
    
    def load_corpus(self, corpus_path):
        """Load a pre-built corpus from file."""
        try:
            print(f"📚 Loading corpus from: {corpus_path}")
            
            with open(corpus_path, 'rb') as f:
                corpus_data = pickle.load(f)
            
            # Reconstruct chunks
            self.chunks = []
            for chunk_data in corpus_data['chunks']:
                chunk = type('Chunk', (), {})()  # Simple object
                chunk.content = chunk_data['content']
                chunk.source_file = chunk_data['source_file']
                chunk.chunk_id = chunk_data['chunk_id']
                chunk.start_line = chunk_data['start_line']
                chunk.end_line = chunk_data['end_line']
                chunk.procedure_name = chunk_data['procedure_name']
                chunk.word_count = chunk_data['word_count']
                chunk.char_count = chunk_data['char_count']
                chunk.tfidf_vector = chunk_data['tfidf_vector']
                chunk.topic_distribution = chunk_data['topic_distribution']
                chunk.dominant_topic = chunk_data['dominant_topic']
                chunk.dominant_topic_prob = chunk_data['dominant_topic_prob']
                chunk.keywords = chunk_data['keywords']
                chunk.words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', chunk.content.lower())
                self.chunks.append(chunk)
            
            # Load vectorizer data
            self.vectorizer_data = corpus_data['vectorizer']
            self.stats = corpus_data['stats']
            self.corpus_metadata = {
                'version': corpus_data.get('version', 'unknown'),
                'created_at': corpus_data.get('created_at', 'unknown')
            }
            
            print(f"✅ Loaded corpus successfully!")
            print(f"   📊 {len(self.chunks)} chunks")
            print(f"   📝 {len(self.vectorizer_data['vocabulary'])} vocabulary words")
            print(f"   🏷️  {len(self.vectorizer_data['topic_labels'])} topics")
            print(f"   📁 {self.stats.get('total_files', 0)} source files")
            print(f"   📅 Created: {self.corpus_metadata['created_at']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading corpus: {e}")
            return False
    
    def print_corpus_info(self):
        """Print detailed corpus information."""
        print(f"\n{'='*60}")
        print("📊 CORPUS INFORMATION")
        print("="*60)
        
        print(f"Version: {self.corpus_metadata.get('version', 'unknown')}")
        print(f"Created: {self.corpus_metadata.get('created_at', 'unknown')}")
        print(f"Total chunks: {len(self.chunks)}")
        print(f"Total files: {self.stats.get('total_files', 0)}")
        print(f"Total procedures: {self.stats.get('total_procedures', 0)}")
        print(f"Average chunk size: {self.stats.get('avg_chunk_size', 0):.1f} words")
        print(f"Vocabulary size: {len(self.vectorizer_data.get('vocabulary', {}))}")
        
        if 'file_types' in self.stats:
            print(f"\nFile types:")
            for ext, count in self.stats['file_types'].items():
                print(f"  {ext}: {count} files")
        
        print(f"\nTopics:")
        for i, label in enumerate(self.vectorizer_data.get('topic_labels', [])):
            print(f"  Topic {i:2d}: {label}")
    
    def search_text(self, query, max_results=10, similarity_threshold=0.05):
        """Perform text-based similarity search."""
        if not self.chunks:
            print("❌ No corpus loaded")
            return []
        
        print(f"🔍 Searching for: '{query}'")
        
        # Extract query words and create TF-IDF vector
        query_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query.lower())
        query_word_counts = Counter(query_words)
        
        # Create query TF-IDF vector
        vocabulary = self.vectorizer_data['vocabulary']
        idf_values = self.vectorizer_data['idf_values']
        
        query_tfidf = [0.0] * len(vocabulary)
        total_query_words = len(query_words)
        
        for word, count in query_word_counts.items():
            if word in vocabulary:
                tf = count / total_query_words if total_query_words > 0 else 0
                idf = idf_values[word]
                tfidf = tf * idf
                query_tfidf[vocabulary[word]] = tfidf
        
        # Calculate similarities with all chunks
        results = []
        
        for chunk in self.chunks:
            # TF-IDF cosine similarity
            tfidf_sim = self._cosine_similarity(query_tfidf, chunk.tfidf_vector)
            
            # Domain keyword matching
            domain_score = self._calculate_domain_relevance(query_words, chunk)
            
            # Topic relevance
            topic_score = self._calculate_topic_relevance(query_words, chunk)
            
            # Combined score
            combined_score = 0.6 * tfidf_sim + 0.25 * domain_score + 0.15 * topic_score
            
            if combined_score >= similarity_threshold:
                # Analyze why this chunk matches
                match_reasons = self._analyze_match_reasons(query_words, chunk, tfidf_sim, domain_score, topic_score)
                
                result = SearchResult(chunk, combined_score, match_reasons)
                result.keyword_matches = list(set(query_words) & set(chunk.words))
                result.topic_relevance = topic_score
                
                results.append(result)
        
        # Sort by score and return top results
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_results]
    
    def search_jira_ticket(self, ticket, max_results=15, similarity_threshold=0.1):
        """Perform comprehensive search based on JIRA ticket requirements."""
        print(f"🎫 Analyzing JIRA ticket: {ticket.ticket_id}")
        print(f"   Title: {ticket.title}")
        
        # Get combined ticket text
        combined_text = ticket.get_combined_text()
        
        # Extract all relevant terms from ticket
        all_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', combined_text.lower())
        
        # Identify domain areas from ticket
        relevant_domains = self._identify_ticket_domains(combined_text)
        print(f"   Identified domains: {', '.join(relevant_domains)}")
        
        # Perform enhanced search
        results = []
        
        for chunk in self.chunks:
            # Multi-factor scoring
            tfidf_score = self._calculate_tfidf_similarity(all_words, chunk)
            domain_score = self._calculate_domain_match(relevant_domains, chunk)
            topic_score = self._calculate_topic_alignment(all_words, chunk)
            procedure_score = self._calculate_procedure_relevance(ticket, chunk)
            
            # Weighted combination for JIRA requirements
            combined_score = (0.4 * tfidf_score + 
                            0.3 * domain_score + 
                            0.2 * topic_score + 
                            0.1 * procedure_score)
            
            if combined_score >= similarity_threshold:
                reasons = self._generate_jira_match_reasons(
                    ticket, chunk, tfidf_score, domain_score, topic_score, procedure_score
                )
                
                result = SearchResult(chunk, combined_score, reasons)
                result.keyword_matches = list(set(all_words) & set(chunk.words))
                results.append(result)
        
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_results]
    
    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _calculate_domain_relevance(self, query_words, chunk):
        """Calculate domain-specific relevance score."""
        chunk_words_set = set(chunk.words)
        query_words_set = set(query_words)
        
        domain_scores = []
        for domain, keywords in self.domain_keywords.items():
            domain_keywords_set = set(keywords)
            
            # Check overlap between query, chunk, and domain keywords
            query_domain_overlap = len(query_words_set & domain_keywords_set)
            chunk_domain_overlap = len(chunk_words_set & domain_keywords_set)
            
            if query_domain_overlap > 0 and chunk_domain_overlap > 0:
                domain_score = (query_domain_overlap + chunk_domain_overlap) / len(domain_keywords_set)
                domain_scores.append(domain_score)
        
        return max(domain_scores) if domain_scores else 0.0
    
    def _calculate_topic_relevance(self, query_words, chunk):
        """Calculate topic-based relevance score."""
        if chunk.dominant_topic < 0 or chunk.dominant_topic >= len(self.vectorizer_data['topic_labels']):
            return 0.0
        
        topic_label = self.vectorizer_data['topic_labels'][chunk.dominant_topic]
        topic_words = set(topic_label.split(' + '))
        query_words_set = set(query_words)
        
        overlap = len(query_words_set & topic_words)
        return (overlap / len(topic_words)) * chunk.dominant_topic_prob if topic_words else 0.0
    
    def _analyze_match_reasons(self, query_words, chunk, tfidf_sim, domain_score, topic_score):
        """Analyze and explain why a chunk matches the query."""
        reasons = []
        
        if tfidf_sim > 0.1:
            reasons.append(f"TF-IDF similarity ({tfidf_sim:.3f})")
        
        if domain_score > 0.1:
            reasons.append(f"Domain relevance ({domain_score:.3f})")
        
        if topic_score > 0.1:
            topic_label = self.vectorizer_data['topic_labels'][chunk.dominant_topic]
            reasons.append(f"Topic match: {topic_label} ({topic_score:.3f})")
        
        if chunk.procedure_name:
            proc_words = set(chunk.procedure_name.lower().split('_'))
            query_words_set = set(query_words)
            if proc_words & query_words_set:
                reasons.append(f"Procedure name match: {chunk.procedure_name}")
        
        keyword_matches = list(set(query_words) & set(chunk.words))
        if keyword_matches:
            reasons.append(f"Keyword matches: {', '.join(keyword_matches[:5])}")
        
        return reasons if reasons else ["Low similarity match"]
    
    def _identify_ticket_domains(self, ticket_text):
        """Identify relevant domains from JIRA ticket text."""
        text_lower = ticket_text.lower()
        relevant_domains = []
        
        for domain, keywords in self.domain_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches >= 2:  # Require at least 2 keyword matches
                relevant_domains.append(domain)
        
        return relevant_domains
    
    def _calculate_tfidf_similarity(self, query_words, chunk):
        """Calculate TF-IDF similarity for JIRA search."""
        query_word_counts = Counter(query_words)
        vocabulary = self.vectorizer_data['vocabulary']
        idf_values = self.vectorizer_data['idf_values']
        
        query_tfidf = [0.0] * len(vocabulary)
        total_query_words = len(query_words)
        
        for word, count in query_word_counts.items():
            if word in vocabulary:
                tf = count / total_query_words if total_query_words > 0 else 0
                idf = idf_values[word]
                tfidf = tf * idf
                query_tfidf[vocabulary[word]] = tfidf
        
        return self._cosine_similarity(query_tfidf, chunk.tfidf_vector)
    
    def _calculate_domain_match(self, relevant_domains, chunk):
        """Calculate domain matching score for JIRA tickets."""
        if not relevant_domains:
            return 0.0
        
        chunk_words_set = set(chunk.words)
        total_score = 0.0
        
        for domain in relevant_domains:
            if domain in self.domain_keywords:
                domain_keywords_set = set(self.domain_keywords[domain])
                overlap = len(chunk_words_set & domain_keywords_set)
                domain_score = overlap / len(domain_keywords_set) if domain_keywords_set else 0
                total_score += domain_score
        
        return total_score / len(relevant_domains) if relevant_domains else 0.0
    
    def _calculate_topic_alignment(self, query_words, chunk):
        """Calculate topic alignment for JIRA analysis."""
        return self._calculate_topic_relevance(query_words, chunk)
    
    def _calculate_procedure_relevance(self, ticket, chunk):
        """Calculate procedure name relevance to ticket."""
        if not chunk.procedure_name:
            return 0.0
        
        # Check if procedure name relates to ticket content
        ticket_text = ticket.get_combined_text().lower()
        proc_name_parts = chunk.procedure_name.lower().split('_')
        
        matches = sum(1 for part in proc_name_parts if part in ticket_text)
        return matches / len(proc_name_parts) if proc_name_parts else 0.0
    
    def _generate_jira_match_reasons(self, ticket, chunk, tfidf_score, domain_score, topic_score, proc_score):
        """Generate detailed match reasons for JIRA tickets."""
        reasons = []
        
        if tfidf_score > 0.1:
            reasons.append(f"Text similarity ({tfidf_score:.3f})")
        
        if domain_score > 0.1:
            reasons.append(f"Domain alignment ({domain_score:.3f})")
        
        if topic_score > 0.1:
            topic_label = self.vectorizer_data['topic_labels'][chunk.dominant_topic]
            reasons.append(f"Topic: {topic_label} ({topic_score:.3f})")
        
        if proc_score > 0.1:
            reasons.append(f"Procedure relevance ({proc_score:.3f})")
        
        if chunk.procedure_name:
            reasons.append(f"Found in procedure: {chunk.procedure_name}")
        
        return reasons if reasons else ["General similarity"]
    
    def display_search_results(self, results, show_content=True, max_lines=6):
        """Display search results in a formatted way."""
        if not results:
            print("❌ No results found")
            return
        
        print(f"\n🎯 Found {len(results)} relevant results:")
        print("="*70)
        
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            print(f"\n{i}. SCORE: {result.similarity_score:.3f}")
            print(f"   📁 FILE: {os.path.basename(chunk.source_file)}")
            print(f"   📍 LINES: {chunk.start_line}-{chunk.end_line}")
            print(f"   🔧 PROCEDURE: {chunk.procedure_name or 'None'}")
            print(f"   📊 WORDS: {chunk.word_count} | CHARS: {chunk.char_count}")
            
            if chunk.dominant_topic < len(self.vectorizer_data['topic_labels']):
                topic_label = self.vectorizer_data['topic_labels'][chunk.dominant_topic]
                print(f"   🏷️  TOPIC: {topic_label} ({chunk.dominant_topic_prob:.3f})")
            
            if chunk.keywords:
                print(f"   🔑 KEYWORDS: {', '.join(chunk.keywords[:8])}")
            
            if result.keyword_matches:
                print(f"   🎯 MATCHES: {', '.join(result.keyword_matches[:8])}")
            
            print(f"   📝 RELEVANCE: {'; '.join(result.match_reasons)}")
            
            if show_content:
                print(f"   📄 CONTENT:")
                lines = chunk.content.split('\n')
                for j, line in enumerate(lines[:max_lines]):
                    line_clean = line.strip()
                    if line_clean:
                        print(f"      {line_clean[:75]}{'...' if len(line_clean) > 75 else ''}")
                
                if len(lines) > max_lines:
                    print(f"      ... ({len(lines) - max_lines} more lines)")
            
            print("   " + "-"*65)
    
    def export_results_for_llm(self, results, query_info, output_file=None):
        """Export search results in a format optimized for LLM analysis."""
        output_lines = []
        output_lines.append("="*80)
        output_lines.append("TAL CODE SEARCH RESULTS FOR LLM ANALYSIS")
        output_lines.append("="*80)
        
        # Query information
        if isinstance(query_info, str):
            output_lines.append(f"\nSEARCH QUERY: {query_info}")
        elif hasattr(query_info, 'ticket_id'):
            output_lines.append(f"\nJIRA TICKET: {query_info.ticket_id}")
            output_lines.append(f"TITLE: {query_info.title}")
            output_lines.append(f"DESCRIPTION: {query_info.description}")
            if query_info.acceptance_criteria:
                output_lines.append("ACCEPTANCE CRITERIA:")
                for i, criteria in enumerate(query_info.acceptance_criteria, 1):
                    output_lines.append(f"  {i}. {criteria}")
        
        # Search results
        output_lines.append(f"\nSEARCH RESULTS: {len(results)} relevant code fragments found")
        output_lines.append("="*60)
        
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            output_lines.append(f"\n{i}. RELEVANCE SCORE: {result.similarity_score:.3f}")
            output_lines.append(f"   FILE: {chunk.source_file}")
            output_lines.append(f"   LINES: {chunk.start_line}-{chunk.end_line}")
            
            if chunk.procedure_name:
                output_lines.append(f"   PROCEDURE: {chunk.procedure_name}")
            
            output_lines.append(f"   ANALYSIS: {'; '.join(result.match_reasons)}")
            
            if result.keyword_matches:
                output_lines.append(f"   KEYWORD MATCHES: {', '.join(result.keyword_matches)}")
            
            output_lines.append(f"\n   FULL CODE:")
            output_lines.append("   " + "-"*50)
            for line in chunk.content.split('\n'):
                output_lines.append(f"   {line}")
            output_lines.append("   " + "-"*50)
        
        # LLM analysis instructions
        output_lines.append(f"\n" + "="*60)
        output_lines.append("INSTRUCTIONS FOR LLM")
        output_lines.append("="*60)
        output_lines.append("Analyze the search results above and provide:")
        output_lines.append("1. Which existing procedures can be reused or modified")
        output_lines.append("2. Implementation approach based on similar patterns")
        output_lines.append("3. Gaps where new code development is needed")
        output_lines.append("4. Best practices from existing codebase")
        output_lines.append("5. Development effort estimation")
        output_lines.append("6. Specific code modifications recommended")
        
        result_text = '\n'.join(output_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result_text)
            print(f"📄 Results exported to: {output_file}")
        
        return result_text

def get_jira_ticket_input():
    """Interactive input for JIRA ticket details."""
    print(f"\n{'='*50}")
    print("🎫 JIRA TICKET INPUT")
    print("="*50)
    
    ticket_id = input("Ticket ID: ").strip()
    title = input("Title: ").strip()
    
    print("\nDescription (press Enter twice when done):")
    description_lines = []
    empty_count = 0
    
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            description_lines.append(line)
        else:
            empty_count = 0
            description_lines.append(line)
    
    # Remove trailing empty lines
    while description_lines and description_lines[-1] == "":
        description_lines.pop()
    
    description = '\n'.join(description_lines)
    
    print("\nAcceptance Criteria (one per line, empty line to finish):")
    acceptance_criteria = []
    while True:
        criteria = input(f"  {len(acceptance_criteria) + 1}. ").strip()
        if not criteria:
            break
        acceptance_criteria.append(criteria)
    
    return JiraTicket(ticket_id, title, description, acceptance_criteria)

def main():
    """Main searcher application."""
    print("="*60)
    print("🔍 TAL CORPUS SEARCHER")
    print("="*60)
    print("Search pre-built TAL corpus with semantic similarity")
    
    # Load corpus
    if len(sys.argv) > 1:
        corpus_file = sys.argv[1]
    else:
        corpus_file = input("📚 Enter corpus file path (.pkl): ").strip()
    
    if not os.path.exists(corpus_file):
        print(f"❌ Corpus file not found: {corpus_file}")
        return False
    
    # Initialize searcher
    searcher = CorpusSearcher()
    if not searcher.load_corpus(corpus_file):
        return False
    
    while True:
        print(f"\n{'='*50}")
        print("🔍 SEARCH OPTIONS")
        print("="*50)
        print("1. Text search")
        print("2. JIRA ticket analysis")
        print("3. Show corpus information")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            # Text search
            query = input("\n🔍 Enter search query: ").strip()
            if not query:
                continue
            
            try:
                max_results = int(input("Max results (default 10): ") or "10")
                threshold = float(input("Similarity threshold (default 0.05): ") or "0.05")
            except ValueError:
                max_results, threshold = 10, 0.05
            
            results = searcher.search_text(query, max_results, threshold)
            searcher.display_search_results(results)
            
            if results:
                export_choice = input(f"\n📄 Export for LLM analysis? (y/n): ").strip().lower()
                if export_choice in ['y', 'yes']:
                    output_file = f"search_results_{query.replace(' ', '_')[:20]}.txt"
                    searcher.export_results_for_llm(results, query, output_file)
        
        elif choice == "2":
            # JIRA ticket analysis
            ticket = get_jira_ticket_input()
            
            try:
                max_results = int(input(f"\nMax results (default 15): ") or "15")
                threshold = float(input("Similarity threshold (default 0.1): ") or "0.1")
            except ValueError:
                max_results, threshold = 15, 0.1
            
            results = searcher.search_jira_ticket(ticket, max_results, threshold)
            searcher.display_search_results(results)
            
            if results:
                export_choice = input(f"\n📄 Export for LLM analysis? (y/n): ").strip().lower()
                if export_choice in ['y', 'yes']:
                    output_file = f"jira_analysis_{ticket.ticket_id.replace('-', '_')}.txt"
                    searcher.export_results_for_llm(results, ticket, output_file)
        
        elif choice == "3":
            # Show corpus info
            searcher.print_corpus_info()
        
        elif choice == "4":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ Search failed!")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
