#!/usr/bin/env python3
"""
Enhanced TAL Corpus Searcher

Enhanced semantic search with improved functionality grouping, topic modeling,
and JIRA requirements analysis. Works with enhanced corpus indexes.
"""

import os
import re
import json
import pickle
import math
import sys
from collections import Counter, defaultdict

# Try to import NLTK for consistent text processing
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Add SimpleChunk class for pickle compatibility
class SimpleChunk:
    """Simple chunk class for pickle compatibility."""
    def __init__(self, content="", source_file="", chunk_id=0, start_line=0, end_line=0, procedure_name=""):
        self.content = content
        self.source_file = source_file
        self.chunk_id = chunk_id
        self.start_line = start_line
        self.end_line = end_line
        self.procedure_name = procedure_name
        self.raw_words = []
        self.words = []
        self.stemmed_words = []
        self.word_count = 0
        self.char_count = len(content)
        self.function_calls = []
        self.variable_declarations = []
        self.control_structures = []
        self.tfidf_vector = []
        self.topic_distribution = []
        self.dominant_topic = 0
        self.dominant_topic_prob = 0.0
        self.keywords = []
        self.semantic_category = ""

class EnhancedSearchResult:
    """Enhanced search result with detailed analysis."""
    def __init__(self, chunk, similarity_score, match_reasons=None):
        self.chunk = chunk
        self.similarity_score = similarity_score
        self.match_reasons = match_reasons or []
        self.keyword_matches = []
        self.semantic_relevance = 0.0
        self.technical_relevance = 0.0
        self.functionality_group = ""
        self.implementation_patterns = []

class JiraTicket:
    """Enhanced JIRA ticket representation."""
    def __init__(self, ticket_id, title, description, acceptance_criteria=None):
        self.ticket_id = ticket_id
        self.title = title
        self.description = description
        self.acceptance_criteria = acceptance_criteria or []
        self.extracted_requirements = []
        self.technical_keywords = []
        self.domain_indicators = []
    
    def get_combined_text(self):
        """Get combined text for analysis."""
        combined = f"{self.title}\n\n{self.description}\n\n"
        if self.acceptance_criteria:
            combined += "Acceptance Criteria:\n"
            for i, criteria in enumerate(self.acceptance_criteria, 1):
                combined += f"{i}. {criteria}\n"
        return combined

class EnhancedTextProcessor:
    """Enhanced text processor matching the indexer."""
    def __init__(self):
        self.stemmer = None
        self.stop_words = set()
        
        if NLTK_AVAILABLE:
            self.stemmer = PorterStemmer()
            try:
                self.stop_words = set(stopwords.words('english'))
            except:
                pass
        
        # Programming and TAL-specific stop words
        prog_stop_words = {
            'int', 'char', 'string', 'void', 'return', 'if', 'else', 'while', 'for',
            'include', 'define', 'endif', 'ifdef', 'ifndef', 'proc', 'subproc',
            'begin', 'end', 'call', 'set', 'get', 'var', 'let', 'const', 'static',
            'tal', 'tandem', 'guardian', 'oss', 'nsk', 'system', 'file', 'record',
            'field', 'page', 'block', 'buffer', 'error', 'status', 'code', 'flag'
        }
        self.stop_words.update(prog_stop_words)
    
    def process_words(self, words):
        """Process words to match indexer processing."""
        if not words:
            return [], []
        
        # Filter stop words and short words
        filtered_words = [
            word for word in words 
            if word.lower() not in self.stop_words 
            and len(word) >= 3
            and not word.isdigit()
        ]
        
        # Apply stemming
        stemmed_words = []
        if self.stemmer and filtered_words:
            stemmed_words = [self.stemmer.stem(word) for word in filtered_words]
        else:
            stemmed_words = filtered_words.copy()
        
        return filtered_words, stemmed_words

class EnhancedCorpusSearcher:
    """Enhanced semantic search with functionality grouping."""
    
    def __init__(self):
        self.chunks = []
        self.vectorizer_data = {}
        self.functionality_groups = {}
        self.stats = {}
        self.corpus_metadata = {}
        self.text_processor = EnhancedTextProcessor()
        
        # Wire processing domain knowledge for requirement analysis
        self.requirement_patterns = {
            'wire_transfer_initiation': ['initiate', 'originate', 'send', 'wire', 'transfer', 'payment'],
            'wire_transfer_receiving': ['receive', 'beneficiary', 'credit', 'incoming', 'settlement'],
            'iso20022_processing': ['iso20022', 'pacs', 'pain', 'camt', 'xml', 'structured'],
            'swift_processing': ['swift', 'mt103', 'mt202', 'gpi', 'fin', 'legacy'],
            'fedwire_operations': ['fedwire', 'imad', 'omad', 'federal', 'reserve'],
            'chips_operations': ['chips', 'clearing', 'house', 'netting', 'prefunded'],
            'message_processing': ['process', 'parse', 'transform', 'convert', 'message', 'format'],
            'validation_screening': ['validate', 'verify', 'screen', 'check', 'compliance', 'sanctions'],
            'exception_handling': ['exception', 'error', 'repair', 'investigation', 'return', 'reversal'],
            'reporting_audit': ['report', 'audit', 'log', 'track', 'monitor', 'regulatory'],
            'routing_decision': ['route', 'routing', 'decision', 'path', 'correspondent', 'intermediary'],
            'settlement_clearing': ['settle', 'settlement', 'clear', 'clearing', 'finalize', 'confirm']
        }
        
        # Wire processing technical implementation patterns
        self.implementation_patterns = {
            'iso20022_implementation': ['iso20022', 'pacs', 'pain', 'camt', 'xml', 'structured'],
            'swift_legacy': ['swift', 'mt103', 'mt202', 'fin', 'legacy', 'migration'],
            'fedwire_processing': ['fedwire', 'imad', 'omad', 'typecode', 'bfc', 'federal'],
            'chips_processing': ['chips', 'uid', 'netting', 'prefunded', 'clearing'],
            'real_time_processing': ['realtime', 'rtgs', 'immediate', 'instant', 'online'],
            'batch_processing': ['batch', 'bulk', 'scheduled', 'overnight', 'queue'],
            'straight_through': ['stp', 'straightthrough', 'automated', 'notouch'],
            'exception_workflow': ['manual', 'intervention', 'repair', 'investigation', 'escalation'],
            'database_heavy': ['database', 'sql', 'table', 'transaction', 'persistence'],
            'file_based': ['file', 'csv', 'flat', 'fixed', 'delimited', 'import', 'export'],
            'api_integration': ['api', 'rest', 'web', 'service', 'endpoint', 'interface'],
            'queue_messaging': ['queue', 'message', 'async', 'mq', 'jms', 'publish'],
            'compliance_screening': ['ofac', 'sanctions', 'aml', 'kyc', 'screening', 'watchlist'],
            'fraud_detection': ['fraud', 'suspicious', 'anomaly', 'pattern', 'detection'],
            'audit_logging': ['audit', 'log', 'trace', 'regulatory', 'compliance', 'reporting'],
            'encryption_security': ['encrypt', 'decrypt', 'security', 'authentication', 'authorization']
        }
        
        print("⚠️ Wire domain config not found, using basic patterns")
    
    def load_enhanced_corpus(self, corpus_path):
        """Load enhanced corpus with all metadata."""
        try:
            print(f"📚 Loading enhanced corpus from: {corpus_path}")
            
            # Add SimpleChunk to global namespace for pickle compatibility
            import sys
            globals()['SimpleChunk'] = SimpleChunk
            sys.modules[__name__].SimpleChunk = SimpleChunk
            
            with open(corpus_path, 'rb') as f:
                corpus_data = pickle.load(f)
            
            # Check corpus version
            version = corpus_data.get('version', 'unknown')
            print(f"   📦 Corpus version: {version}")
            
            # Reconstruct enhanced chunks with error handling
            self.chunks = []
            for i, chunk_data in enumerate(corpus_data.get('chunks', [])):
                try:
                    # Handle both object and dictionary formats
                    if hasattr(chunk_data, '__dict__'):
                        # It's a SimpleChunk object
                        chunk = chunk_data
                    else:
                        # It's a dictionary, create a simple object
                        chunk = type('EnhancedChunk', (), {})()
                        
                        # Basic properties (always present)
                        chunk.content = chunk_data.get('content', '')
                        chunk.source_file = chunk_data.get('source_file', '')
                        chunk.chunk_id = chunk_data.get('chunk_id', i)
                        chunk.start_line = chunk_data.get('start_line', 0)
                        chunk.end_line = chunk_data.get('end_line', 0)
                        chunk.procedure_name = chunk_data.get('procedure_name', '')
                        chunk.word_count = chunk_data.get('word_count', 0)
                        chunk.char_count = chunk_data.get('char_count', 0)
                        
                        # Enhanced NLP properties
                        chunk.words = chunk_data.get('words', [])
                        chunk.stemmed_words = chunk_data.get('stemmed_words', [])
                        chunk.semantic_category = chunk_data.get('semantic_category', 'general')
                        
                        # Technical pattern properties
                        chunk.function_calls = chunk_data.get('function_calls', [])
                        chunk.variable_declarations = chunk_data.get('variable_declarations', [])
                        chunk.control_structures = chunk_data.get('control_structures', [])
                        
                        # Vector and topic properties
                        chunk.tfidf_vector = chunk_data.get('tfidf_vector', [])
                        chunk.topic_distribution = chunk_data.get('topic_distribution', [])
                        chunk.dominant_topic = chunk_data.get('dominant_topic', 0)
                        chunk.dominant_topic_prob = chunk_data.get('dominant_topic_prob', 0.0)
                        chunk.keywords = chunk_data.get('keywords', [])
                    
                    # Ensure chunk has words for searching
                    if not hasattr(chunk, 'words') or not chunk.words:
                        if hasattr(chunk, 'content') and chunk.content:
                            chunk.words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', chunk.content.lower())
                        else:
                            chunk.words = []
                    
                    self.chunks.append(chunk)
                    
                except Exception as chunk_error:
                    print(f"⚠️  Warning: Error loading chunk {i}: {chunk_error}")
                    continue
            
            # Load enhanced vectorizer data with error handling
            self.vectorizer_data = corpus_data.get('vectorizer', {})
            self.functionality_groups = corpus_data.get('functionality_groups', {})
            self.stats = corpus_data.get('stats', {})
            self.corpus_metadata = {
                'version': version,
                'created_at': corpus_data.get('created_at', 'unknown'),
                'nltk_available': corpus_data.get('nltk_available', False),
                'wire_processing_optimized': corpus_data.get('wire_processing_optimized', False)
            }
            
            # Validate essential data
            if not self.chunks:
                print("❌ No chunks found in corpus")
                return False
            
            if not self.vectorizer_data:
                print("⚠️  No vectorizer data found, search capabilities will be limited")
            
            print(f"✅ Enhanced corpus loaded successfully!")
            print(f"   📊 {len(self.chunks)} chunks")
            
            vocab_size = len(self.vectorizer_data.get('vocabulary', {}))
            stemmed_vocab_size = len(self.vectorizer_data.get('stemmed_vocabulary', {}))
            print(f"   📝 {vocab_size} vocabulary words")
            if stemmed_vocab_size > 0:
                print(f"   🌿 {stemmed_vocab_size} stemmed terms")
            
            topic_count = len(self.vectorizer_data.get('topic_labels', []))
            print(f"   🏷️  {topic_count} topics")
            
            func_groups_count = len(self.functionality_groups.get('semantic_categories', {}))
            print(f"   🔗 {func_groups_count} functionality groups")
            
            total_files = self.stats.get('total_files', 0)
            print(f"   📁 {total_files} source files")
            
            created_at = self.corpus_metadata['created_at']
            print(f"   📅 Created: {created_at}")
            
            if self.corpus_metadata['wire_processing_optimized']:
                print(f"   🏦 Wire processing optimized: ✅")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading enhanced corpus: {e}")
            print("💡 Troubleshooting tips:")
            print("   • Ensure the corpus file was created with the enhanced indexer")
            print("   • Try re-indexing your codebase with the enhanced indexer")
            print("   • Check that the file path is correct and accessible")
            import traceback
            traceback.print_exc()
            return False
    
    def enhanced_text_search(self, query, max_results=15, use_semantic_boost=True):
        """Enhanced text search with semantic category boosting."""
        print(f"🔍 Enhanced search: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        
        # Process query
        query_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query.lower())
        filtered_words, stemmed_words = self.text_processor.process_words(query_words)
        
        # Simple keyword matching for chunks
        results = []
        for chunk in self.chunks:
            # Basic keyword matching
            chunk_words_set = set(chunk.words) if hasattr(chunk, 'words') and chunk.words else set()
            if not chunk_words_set and chunk.content:
                chunk_words_set = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', chunk.content.lower()))
            
            query_words_set = set(filtered_words)
            
            # Calculate overlap
            overlap = len(chunk_words_set & query_words_set)
            if overlap > 0:
                # Calculate similarity score
                base_score = overlap / len(query_words_set) if query_words_set else 0
                
                # Boost for semantic category
                semantic_boost = 0.0
                if use_semantic_boost and hasattr(chunk, 'semantic_category'):
                    category_words = chunk.semantic_category.replace('_', ' ').split()
                    category_overlap = len(set(category_words) & query_words_set)
                    semantic_boost = category_overlap * 0.1
                
                # Boost for procedure name
                proc_boost = 0.0
                if hasattr(chunk, 'procedure_name') and chunk.procedure_name:
                    proc_words = set(chunk.procedure_name.lower().split('_'))
                    proc_overlap = len(proc_words & query_words_set)
                    proc_boost = proc_overlap * 0.1
                
                # Combined score
                combined_score = base_score + semantic_boost + proc_boost
                
                # Generate match reasons
                reasons = []
                if base_score > 0:
                    reasons.append(f"Keyword overlap: {overlap} terms")
                if semantic_boost > 0:
                    reasons.append(f"Semantic category: {chunk.semantic_category}")
                if proc_boost > 0:
                    reasons.append(f"Procedure: {chunk.procedure_name}")
                
                result = EnhancedSearchResult(chunk, combined_score, reasons)
                result.keyword_matches = list(chunk_words_set & query_words_set)
                result.semantic_relevance = semantic_boost
                
                if hasattr(chunk, 'semantic_category'):
                    result.functionality_group = f"semantic:{chunk.semantic_category}"
                
                results.append(result)
        
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_results]
    
    def search_semantic_categories(self, category_name=None, max_results=15):
        """Search by semantic category."""
        semantic_groups = self.functionality_groups.get('semantic_categories', {})
        
        if category_name is None:
            # Show available categories
            print(f"📊 Available semantic categories:")
            for cat, chunks in semantic_groups.items():
                print(f"  {cat.replace('_', ' ').title()}: {len(chunks)} chunks")
            return []
        
        if category_name not in semantic_groups:
            print(f"❌ Category not found: {category_name}")
            return []
        
        chunks = semantic_groups[category_name]
        print(f"🏷️  Found {len(chunks)} chunks in category: {category_name}")
        
        # Return chunks sorted by topic probability
        results = []
        for chunk in chunks:
            score = chunk.dominant_topic_prob if hasattr(chunk, 'dominant_topic_prob') else 0.5
            result = EnhancedSearchResult(chunk, score, [f"Semantic category: {category_name}"])
            result.semantic_relevance = score
            result.functionality_group = f"semantic:{category_name}"
            results.append(result)
        
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:max_results]
    
    def display_enhanced_results(self, results, show_content=True, max_lines=8):
        """Display enhanced search results with detailed analysis."""
        if not results:
            print("❌ No results found")
            return
        
        print(f"\n🎯 Found {len(results)} enhanced results:")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            print(f"\n{i}. RELEVANCE SCORE: {result.similarity_score:.3f}")
            print(f"   📁 FILE: {os.path.basename(chunk.source_file)}")
            print(f"   📍 LINES: {chunk.start_line}-{chunk.end_line}")
            print(f"   🔧 PROCEDURE: {chunk.procedure_name or 'None'}")
            print(f"   📊 SIZE: {chunk.word_count} words | {chunk.char_count} chars")
            
            # Enhanced metadata
            if hasattr(chunk, 'semantic_category'):
                print(f"   🏷️  CATEGORY: {chunk.semantic_category.replace('_', ' ').title()}")
            
            if result.functionality_group:
                print(f"   🔗 GROUP: {result.functionality_group}")
            
            if hasattr(chunk, 'dominant_topic') and chunk.dominant_topic < len(self.vectorizer_data.get('topic_labels', [])):
                topic_label = self.vectorizer_data['topic_labels'][chunk.dominant_topic]
                print(f"   🎯 TOPIC: {topic_label}")
            
            # Technical patterns
            if hasattr(chunk, 'function_calls') and chunk.function_calls:
                print(f"   📞 FUNCTIONS: {', '.join(chunk.function_calls[:5])}")
            
            if hasattr(chunk, 'variable_declarations') and chunk.variable_declarations:
                print(f"   📊 VARIABLES: {', '.join(chunk.variable_declarations[:5])}")
            
            if result.implementation_patterns:
                print(f"   🔧 PATTERNS: {', '.join(result.implementation_patterns)}")
            
            # Enhanced keywords and matches
            if hasattr(chunk, 'keywords') and chunk.keywords:
                print(f"   🔑 KEYWORDS: {', '.join(chunk.keywords[:8])}")
            
            if result.keyword_matches:
                print(f"   🎯 MATCHES: {', '.join(result.keyword_matches[:8])}")
            
            # Relevance analysis
            print(f"   📝 ANALYSIS: {'; '.join(result.match_reasons)}")
            
            if result.semantic_relevance > 0:
                print(f"   🎨 SEMANTIC: {result.semantic_relevance:.3f}")
            
            # Content preview
            if show_content:
                print(f"   📄 CODE PREVIEW:")
                lines = chunk.content.split('\n')
                
                # Show meaningful lines (skip empty/comment-only lines)
                meaningful_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                        meaningful_lines.append(line)
                
                for j, line in enumerate(meaningful_lines[:max_lines]):
                    print(f"      {line[:80]}{'...' if len(line) > 80 else ''}")
                
                if len(meaningful_lines) > max_lines:
                    print(f"      ... ({len(meaningful_lines) - max_lines} more meaningful lines)")
            
            print("   " + "-"*75)
    
    def print_corpus_info(self):
        """Print enhanced corpus information."""
        print(f"\n{'='*70}")
        print("📊 ENHANCED CORPUS INFORMATION")
        print("="*70)
        
        print(f"Version: {self.corpus_metadata.get('version', 'unknown')}")
        print(f"Created: {self.corpus_metadata.get('created_at', 'unknown')}")
        print(f"NLP Processing: {'Enhanced (NLTK)' if self.corpus_metadata.get('nltk_available') else 'Basic'}")
        print(f"Total chunks: {len(self.chunks)}")
        print(f"Vocabulary size: {len(self.vectorizer_data.get('vocabulary', {}))}")
        print(f"Stemmed vocabulary: {len(self.vectorizer_data.get('stemmed_vocabulary', {}))}")
        
        # Show semantic categories
        semantic_categories = self.stats.get('semantic_categories', {})
        if semantic_categories:
            print(f"\n🏷️  Semantic Categories:")
            for category, count in semantic_categories.items():
                print(f"  {category.replace('_', ' ').title()}: {count} chunks")
        
        # Show functionality groups
        func_groups = self.functionality_groups
        if func_groups:
            print(f"\n🔗 Functionality Groups:")
            print(f"  Semantic categories: {len(func_groups.get('semantic_categories', {}))}")
            print(f"  Procedure patterns: {len(func_groups.get('procedure_patterns', {}))}")
            print(f"  Function patterns: {len(func_groups.get('function_patterns', {}))}")
        
        # Show topics
        topic_labels = self.vectorizer_data.get('topic_labels', [])
        if topic_labels:
            print(f"\n🎯 Topics:")
            for i, label in enumerate(topic_labels):
                print(f"  Topic {i:2d}: {label}")

def get_enhanced_jira_input():
    """Enhanced JIRA ticket input with requirement analysis."""
    print(f"\n{'='*60}")
    print("🎫 ENHANCED JIRA TICKET INPUT")
    print("="*60)
    
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
    """Enhanced main searcher application."""
    print("="*70)
    print("🔍 ENHANCED TAL CORPUS SEARCHER")
    print("="*70)
    print("Enhanced semantic search with functionality grouping")
    print("Features:")
    print("• Semantic category search")
    print("• Enhanced JIRA requirement analysis")
    print("• Technical pattern matching")
    print("• Functionality grouping")
    print("• Implementation pattern detection")
    
    # Load corpus
    if len(sys.argv) > 1:
        corpus_file = sys.argv[1]
    else:
        corpus_file = input("\n📚 Enter enhanced corpus file (.pkl): ").strip()
    
    if not os.path.exists(corpus_file):
        print(f"❌ Corpus file not found: {corpus_file}")
        return False
    
    # Initialize enhanced searcher
    searcher = EnhancedCorpusSearcher()
    if not searcher.load_enhanced_corpus(corpus_file):
        return False
    
    while True:
        print(f"\n{'='*60}")
        print("🔍 ENHANCED SEARCH OPTIONS")
        print("="*60)
        print("1. Enhanced text search")
        print("2. Enhanced JIRA ticket analysis")
        print("3. Search by semantic category")
        print("4. Show corpus information")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            # Enhanced text search
            query = input("\n🔍 Enter search query: ").strip()
            if not query:
                continue
            
            try:
                max_results = int(input("Max results (default 15): ") or "15")
                use_semantic = input("Use semantic boosting? (y/n, default y): ").strip().lower()
                use_semantic = use_semantic != 'n'
            except ValueError:
                max_results, use_semantic = 15, True
            
            results = searcher.enhanced_text_search(query, max_results, use_semantic)
            searcher.display_enhanced_results(results)
        
        elif choice == "2":
            # Enhanced JIRA analysis
            ticket = get_enhanced_jira_input()
            
            # Simple JIRA analysis using text search
            combined_text = ticket.get_combined_text()
            results = searcher.enhanced_text_search(combined_text, 20, True)
            
            print(f"\n🎫 JIRA Analysis Results for: {ticket.ticket_id}")
            searcher.display_enhanced_results(results)
        
        elif choice == "3":
            # Semantic category search
            print("\n🏷️  Available options:")
            print("  - Leave empty to see all categories")
            print("  - Enter category name to search within it")
            
            category = input("\nSemantic category: ").strip()
            if not category:
                searcher.search_semantic_categories()
                continue
            
            try:
                max_results = int(input("Max results (default 15): ") or "15")
            except ValueError:
                max_results = 15
            
            results = searcher.search_semantic_categories(category, max_results)
            searcher.display_enhanced_results(results)
        
        elif choice == "4":
            # Show corpus info
            searcher.print_corpus_info()
        
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ Enhanced search failed!")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
