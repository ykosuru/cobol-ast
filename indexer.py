#!/usr/bin/env python3
"""
Enhanced TAL Corpus Indexer with Wire Processing Domain Knowledge

Creates semantic indexes of TAL source code files with comprehensive wire processing
domain knowledge including ISO 20022, SWIFT, Fedwire, CHIPS, and compliance terminology.

Features:
- Stop word removal and stemming
- Wire processing domain-specific topic modeling
- Technical pattern extraction (function calls, variables, control structures)
- Semantic categorization optimized for wire processing
- High-value term boosting for critical wire processing vocabulary
"""

import os
import re
import json
import pickle
import math
import random
import sys
import hashlib
from collections import defaultdict, Counter
from pathlib import Path

# Try to import NLTK components (graceful fallback if not available)
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
    
    # Download required NLTK data if needed
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("📦 Downloading NLTK data...")
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    print("⚠️  NLTK not available - using basic text processing")

class SimpleChunk:
    """Enhanced chunk representation with wire processing metadata."""
    def __init__(self, content, source_file, chunk_id, start_line=0, end_line=0, procedure_name=""):
        self.content = content
        self.source_file = source_file
        self.chunk_id = chunk_id
        self.start_line = start_line
        self.end_line = end_line
        self.procedure_name = procedure_name
        
        # Extract basic info
        self.raw_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content.lower())
        self.words = []  # Will be filled with processed words
        self.stemmed_words = []  # Will be filled with stemmed words
        self.word_count = len(self.raw_words)
        self.char_count = len(content)
        
        # Technical patterns specific to TAL/C code
        self.function_calls = self._extract_function_calls()
        self.variable_declarations = self._extract_variable_declarations()
        self.control_structures = self._extract_control_structures()
        
        # Will be filled by vectorizer
        self.tfidf_vector = []
        self.topic_distribution = []
        self.dominant_topic = -1
        self.dominant_topic_prob = 0.0
        self.keywords = []
        self.semantic_category = ""
    
    def _extract_function_calls(self):
        """Extract function call patterns from code."""
        # Pattern for function calls: word followed by parentheses
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        return list(set(re.findall(pattern, self.content, re.IGNORECASE)))
    
    def _extract_variable_declarations(self):
        """Extract variable declaration patterns."""
        # Common TAL/C variable declaration patterns
        patterns = [
            r'\bINT\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # TAL INT declarations
            r'\bSTRING\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # TAL STRING declarations
            r'\bchar\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # C char declarations
            r'\bint\s+([a-zA-Z_][a-zA-Z0-9_]*)',   # C int declarations
        ]
        
        variables = []
        for pattern in patterns:
            variables.extend(re.findall(pattern, self.content, re.IGNORECASE))
        
        return list(set(variables))
    
    def _extract_control_structures(self):
        """Extract control structure keywords."""
        control_keywords = ['if', 'else', 'while', 'for', 'switch', 'case', 'return', 'break', 'continue']
        found_structures = []
        
        content_lower = self.content.lower()
        for keyword in control_keywords:
            if re.search(r'\b' + keyword + r'\b', content_lower):
                found_structures.append(keyword)
        
        return found_structures

class EnhancedTextProcessor:
    """Enhanced text processing with NLP capabilities for wire processing."""
    
    def __init__(self):
        self.stemmer = None
        self.stop_words = set()
        
        if NLTK_AVAILABLE:
            self.stemmer = PorterStemmer()
            try:
                self.stop_words = set(stopwords.words('english'))
            except:
                pass
        
        # Add programming-specific stop words
        prog_stop_words = {
            'int', 'char', 'string', 'void', 'return', 'if', 'else', 'while', 'for',
            'include', 'define', 'endif', 'ifdef', 'ifndef', 'proc', 'subproc',
            'begin', 'end', 'call', 'set', 'get', 'var', 'let', 'const', 'static'
        }
        self.stop_words.update(prog_stop_words)
        
        # Add common TAL-specific stop words
        tal_stop_words = {
            'tal', 'tandem', 'guardian', 'oss', 'nsk', 'system', 'file', 'record',
            'field', 'page', 'block', 'buffer', 'error', 'status', 'code', 'flag'
        }
        self.stop_words.update(tal_stop_words)
    
    def process_words(self, words):
        """Process list of words: remove stop words, stem, filter."""
        if not words:
            return [], []
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if word.lower() not in self.stop_words 
            and len(word) >= 3
            and not word.isdigit()
        ]
        
        # Apply stemming if available
        stemmed_words = []
        if self.stemmer and filtered_words:
            stemmed_words = [self.stemmer.stem(word) for word in filtered_words]
        else:
            stemmed_words = filtered_words.copy()
        
        return filtered_words, stemmed_words

class TALChunker:
    """Enhanced chunker with better procedure detection."""
    
    def __init__(self):
        # Enhanced procedure patterns for TAL
        self.procedure_patterns = [
            re.compile(r'^\s*(?:PROC|SUBPROC)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^\s*(\w+)\s*\([^)]*\)\s*{', re.MULTILINE),  # C-style functions
            re.compile(r'^\s*(?:static\s+)?(?:int|void|char\*?)\s+(\w+)\s*\(', re.MULTILINE),  # C functions
        ]
    
    def chunk_file(self, file_path):
        """Chunk a single file with enhanced procedure detection."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        if not content.strip():
            return []
        
        return self._chunk_content_enhanced(content, file_path)
    
    def _chunk_content_enhanced(self, content, file_path):
        """Enhanced chunking with multiple procedure patterns."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        chunk_start_line = 0
        chunk_id = 0
        current_proc_name = ""
        
        # Find all procedure starts
        procedure_locations = []
        for pattern in self.procedure_patterns:
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n')
                proc_name = match.group(1)
                procedure_locations.append((line_no, proc_name))
        
        # Sort by line number
        procedure_locations.sort()
        
        # Process lines with procedure awareness
        proc_index = 0
        for line_no, line in enumerate(lines):
            # Check if we're at a new procedure
            while (proc_index < len(procedure_locations) and 
                   procedure_locations[proc_index][0] == line_no):
                
                # Save previous chunk if it exists
                if current_chunk and any(l.strip() for l in current_chunk):
                    chunk_content = '\n'.join(current_chunk)
                    chunk = SimpleChunk(
                        content=chunk_content,
                        source_file=file_path,
                        chunk_id=chunk_id,
                        start_line=chunk_start_line,
                        end_line=line_no - 1,
                        procedure_name=current_proc_name
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                
                # Start new chunk
                current_chunk = [line]
                chunk_start_line = line_no
                current_proc_name = procedure_locations[proc_index][1]
                proc_index += 1
                break
            else:
                current_chunk.append(line)
                
                # Split very large chunks
                if len(current_chunk) > 150:  # lines
                    chunk_content = '\n'.join(current_chunk)
                    if chunk_content.strip():
                        chunk = SimpleChunk(
                            content=chunk_content,
                            source_file=file_path,
                            chunk_id=chunk_id,
                            start_line=chunk_start_line,
                            end_line=line_no,
                            procedure_name=current_proc_name
                        )
                        chunks.append(chunk)
                        chunk_id += 1
                    current_chunk = []
                    chunk_start_line = line_no + 1
                    current_proc_name = ""
        
        # Handle remaining content
        if current_chunk and any(l.strip() for l in current_chunk):
            chunk_content = '\n'.join(current_chunk)
            chunk = SimpleChunk(
                content=chunk_content,
                source_file=file_path,
                chunk_id=chunk_id,
                start_line=chunk_start_line,
                end_line=len(lines) - 1,
                procedure_name=current_proc_name
            )
            chunks.append(chunk)
        
        return chunks

class EnhancedVectorizer:
    """Enhanced vectorizer with wire processing domain knowledge and improved topic modeling."""
    
    def __init__(self, max_features=3000, n_topics=12, min_topic_words=5):
        self.max_features = max_features
        self.n_topics = n_topics
        self.min_topic_words = min_topic_words
        self.vocabulary = {}
        self.stemmed_vocabulary = {}
        self.idf_values = {}
        self.topic_labels = []
        self.topic_keywords = []
        self.document_count = 0
        self.text_processor = EnhancedTextProcessor()
        
        # Load or set wire processing domain knowledge
        self._load_wire_domain_knowledge()
    
    def _load_wire_domain_knowledge(self):
        """Load wire processing domain configuration."""
        # Import wire processing domain configuration
        try:
            from wire_domain_config import get_wire_domain_config
            wire_config = get_wire_domain_config()
            self.domain_seeds = wire_config['domain_keywords']
            
            # Add wire-specific stop words
            wire_stop_words = wire_config['stop_words']
            self.text_processor.stop_words.update(wire_stop_words)
            
            # Store high-value terms for boosting
            self.high_value_terms = wire_config['high_value_terms']
            
            print("✅ Loaded wire processing domain configuration")
            
        except ImportError:
            print("⚠️ Wire domain config not found, using basic domain seeds")
            # Fallback to basic wire processing domains
            self.domain_seeds = {
                # Core Wire Transfer Processing
                'wire_transfer_core': [
                    'wire', 'transfer', 'payment', 'funds', 'fedwire', 'chips', 'swift', 'rtgs',
                    'originator', 'beneficiary', 'debtor', 'creditor', 'debit', 'credit', 'settlement'
                ],
                
                # ISO 20022 Message Processing
                'iso20022_messages': [
                    'iso20022', 'pacs', 'pain', 'camt', 'remt', 'pacs008', 'pacs009', 'pacs002', 
                    'pacs004', 'pacs007', 'pain001', 'camt056', 'camt029', 'camt110', 'camt111'
                ],
                
                # SWIFT Legacy and gpi
                'swift_processing': [
                    'swift', 'mt103', 'mt202', 'mt202cov', 'gpi', 'uetr', 'bic', 'tracker',
                    'fin', 'cbpr', 'mystandards', 'alliance', 'score', 'cover'
                ],
                
                # Fedwire Operations
                'fedwire_operations': [
                    'fedwire', 'imad', 'omad', 'fedline', 'advantage', 'fedpayments', 'manager',
                    'fedtransaction', 'analyzer', 'drawdown', 'participant', 'cutoff', 'typecode', 'bfc'
                ],
                
                # CHIPS Operations  
                'chips_processing': [
                    'chips', 'uid', 'sequence', 'prefunded', 'balance', 'netting', 'finality',
                    'clearing', 'house', 'interbank', 'realtime', 'gross'
                ],
                
                # Investigation and Exception Handling
                'investigation_exceptions': [
                    'investigation', 'exception', 'repair', 'return', 'reversal', 'refund',
                    'nondelivery', 'recall', 'cancellation', 'inquiry', 'resolution', 'reject'
                ],
                
                # Compliance and Screening
                'compliance_screening': [
                    'ofac', 'sanctions', 'aml', 'kyc', 'compliance', 'screening', 'fraud',
                    'monitoring', 'suspicious', 'detection', 'regulatory', 'reporting'
                ],
                
                # Correspondent Banking
                'correspondent_banking': [
                    'correspondent', 'intermediary', 'nostro', 'vostro', 'cover', 'instructing',
                    'agent', 'ultimate', 'routing', 'chain', 'relationship'
                ],
                
                # Message Validation and Processing
                'message_validation': [
                    'validation', 'authenticate', 'verify', 'mandatory', 'optional', 'format',
                    'structured', 'address', 'lei', 'remittance', 'purpose', 'charge', 'bearer'
                ],
                
                # Cross-Border and Multi-Currency
                'crossborder_currency': [
                    'crossborder', 'currency', 'exchange', 'rate', 'multicurrency', 'sepa',
                    'euro', 'international', 'domestic', 'foreign'
                ],
                
                # System Infrastructure
                'system_infrastructure': [
                    'queue', 'batch', 'realtime', 'stp', 'straightthrough', 'processing',
                    'automated', 'manual', 'intervention', 'priority', 'high', 'normal'
                ],
                
                # Database and File Operations (TAL-specific)
                'data_operations': [
                    'database', 'table', 'record', 'insert', 'update', 'select', 'query',
                    'file', 'read', 'write', 'open', 'close', 'copy', 'delete', 'archive'
                ]
            }
            self.high_value_terms = {
                'iso20022', 'pacs008', 'pacs009', 'mt103', 'mt202', 'swift', 'fedwire',
                'chips', 'uetr', 'gpi', 'ofac', 'sanctions', 'aml', 'kyc', 'stp',
                'correspondent', 'nostro', 'vostro', 'originator', 'beneficiary',
                'investigation', 'exception', 'repair', 'reversal', 'return'
            }
    
    def fit_transform(self, chunks):
        """Enhanced vectorization with improved topic modeling."""
        print(f"🔍 Processing {len(chunks)} chunks with wire processing NLP...")
        
        if not chunks:
            print("No chunks to process")
            return
        
        # Process all chunk words
        self._process_chunk_words(chunks)
        
        # Build enhanced vocabulary
        self._build_enhanced_vocabulary(chunks)
        
        # Create TF-IDF vectors
        self._create_enhanced_tfidf_vectors(chunks)
        
        # Create semantic topics using wire processing domain knowledge
        self._create_semantic_topics(chunks)
        
        # Extract enhanced keywords
        self._extract_enhanced_keywords(chunks)
        
        print(f"✅ Enhanced processing complete:")
        print(f"   📝 {len(self.vocabulary)} vocabulary terms")
        print(f"   🌿 {len(self.stemmed_vocabulary)} stemmed terms")
        print(f"   🏷️  {len(self.topic_labels)} semantic topics")
        print(f"   🔧 {sum(1 for c in chunks if c.procedure_name)} procedures identified")
    
    def _process_chunk_words(self, chunks):
        """Process words for all chunks."""
        for chunk in chunks:
            # Process raw words through NLP pipeline
            filtered_words, stemmed_words = self.text_processor.process_words(chunk.raw_words)
            chunk.words = filtered_words
            chunk.stemmed_words = stemmed_words
    
    def _build_enhanced_vocabulary(self, chunks):
        """Build vocabulary with stemming and filtering."""
        # Count word and stemmed word frequencies
        word_doc_freq = defaultdict(int)
        stemmed_doc_freq = defaultdict(int)
        
        for chunk in chunks:
            unique_words = set(chunk.words)
            unique_stemmed = set(chunk.stemmed_words)
            
            for word in unique_words:
                word_doc_freq[word] += 1
            
            for stemmed in unique_stemmed:
                stemmed_doc_freq[stemmed] += 1
        
        self.document_count = len(chunks)
        
        # Filter vocabulary (appear in at least 2 docs, but not more than 80%)
        min_df = 2
        max_df = int(0.8 * self.document_count)
        
        # Build regular vocabulary
        vocab_candidates = [
            (word, freq) for word, freq in word_doc_freq.items()
            if min_df <= freq <= max_df and len(word) >= 3
        ]
        
        # Build stemmed vocabulary  
        stemmed_candidates = [
            (word, freq) for word, freq in stemmed_doc_freq.items()
            if min_df <= freq <= max_df and len(word) >= 3
        ]
        
        # Sort by frequency and take top features
        vocab_candidates.sort(key=lambda x: x[1], reverse=True)
        stemmed_candidates.sort(key=lambda x: x[1], reverse=True)
        
        if len(vocab_candidates) > self.max_features:
            vocab_candidates = vocab_candidates[:self.max_features]
        
        if len(stemmed_candidates) > self.max_features:
            stemmed_candidates = stemmed_candidates[:self.max_features]
        
        # Create vocabulary mappings
        self.vocabulary = {word: idx for idx, (word, _) in enumerate(vocab_candidates)}
        self.stemmed_vocabulary = {word: idx for idx, (word, _) in enumerate(stemmed_candidates)}
        
        # Calculate IDF values for both vocabularies
        for word, doc_freq in vocab_candidates:
            self.idf_values[word] = math.log(self.document_count / doc_freq)
        
        print(f"  📚 Vocabulary: {len(self.vocabulary)} words, {len(self.stemmed_vocabulary)} stems")
    
    def _create_enhanced_tfidf_vectors(self, chunks):
        """Create TF-IDF vectors using processed words with wire processing boost."""
        for chunk in chunks:
            # Create vector using stemmed words for better matching
            vector = [0.0] * len(self.stemmed_vocabulary)
            stemmed_counts = Counter(chunk.stemmed_words)
            total_words = len(chunk.stemmed_words)
            
            if total_words > 0:
                for stemmed_word, count in stemmed_counts.items():
                    if stemmed_word in self.stemmed_vocabulary:
                        tf = count / total_words
                        
                        # Find original word for IDF calculation
                        original_words = [w for w in chunk.words if self.text_processor.stemmer and self.text_processor.stemmer.stem(w) == stemmed_word]
                        if original_words:
                            original_word = original_words[0]
                            idf = self.idf_values.get(original_word, 1.0)
                            
                            # Apply wire processing domain boost
                            wire_boost = 1.0
                            if hasattr(self, 'high_value_terms') and original_word.lower() in self.high_value_terms:
                                wire_boost = 1.5  # 50% boost for high-value wire terms
                            
                        else:
                            idf = 1.0
                            wire_boost = 1.0
                        
                        tfidf = tf * idf * wire_boost
                        vector[self.stemmed_vocabulary[stemmed_word]] = tfidf
            
            chunk.tfidf_vector = vector
    
    def _create_semantic_topics(self, chunks):
        """Create semantic topics using wire processing domain knowledge and word co-occurrence."""
        print("  🎯 Creating wire processing semantic topics...")
        
        # Initialize topic assignment with enhanced wire processing logic
        chunk_topic_scores = []
        
        for chunk in chunks:
            chunk_words_set = set(chunk.words + chunk.stemmed_words)
            
            # Calculate scores for each wire processing domain
            topic_scores = []
            for domain, seed_words in self.domain_seeds.items():
                # Enhanced scoring for wire processing domains
                base_overlap = len(chunk_words_set & set(seed_words))
                
                # Boost score for procedure names that match domain
                proc_boost = 0
                if chunk.procedure_name:
                    proc_words = chunk.procedure_name.lower().split('_')
                    proc_overlap = len(set(proc_words) & set(seed_words))
                    proc_boost = proc_overlap * 0.4  # Increased boost for procedures
                
                # Boost score for technical patterns specific to wire processing
                tech_boost = 0
                
                # ISO 20022 message pattern detection
                if domain == 'iso20022_messages' and any('pacs' in call.lower() or 'pain' in call.lower() or 'camt' in call.lower() for call in chunk.function_calls):
                    tech_boost += 0.3
                
                # SWIFT message pattern detection
                if domain == 'swift_processing' and any('mt' in call.lower() or 'swift' in call.lower() for call in chunk.function_calls):
                    tech_boost += 0.3
                
                # Fedwire pattern detection
                if domain == 'fedwire_operations' and any('fedwire' in call.lower() or 'imad' in call.lower() or 'omad' in call.lower() for call in chunk.function_calls):
                    tech_boost += 0.3
                
                # Exception handling pattern detection
                if domain == 'investigation_exceptions' and any('error' in struct or 'exception' in struct for struct in chunk.control_structures):
                    tech_boost += 0.2
                
                # Database operations for wire processing
                if domain == 'data_operations' and chunk.variable_declarations:
                    tech_boost += 0.15
                
                # High-value terms boost
                high_value_boost = 0
                if hasattr(self, 'high_value_terms'):
                    high_value_matches = len(chunk_words_set & self.high_value_terms)
                    high_value_boost = high_value_matches * 0.2
                
                # Combined domain score
                total_score = base_overlap + proc_boost + tech_boost + high_value_boost
                topic_scores.append(total_score)
            
            chunk_topic_scores.append(topic_scores)
        
        # Assign topics and create distributions
        self.topic_labels = list(self.domain_seeds.keys())
        self.topic_keywords = list(self.domain_seeds.values())
        
        for chunk, scores in zip(chunks, chunk_topic_scores):
            # Normalize scores to create probability distribution
            total_score = sum(scores) if sum(scores) > 0 else 1
            chunk.topic_distribution = [score / total_score for score in scores]
            
            # Find dominant topic with enhanced threshold for wire processing
            if scores:
                max_score = max(scores)
                chunk.dominant_topic = scores.index(max_score)
                chunk.dominant_topic_prob = max_score / total_score
                
                # Assign semantic category with wire processing specificity
                if chunk.dominant_topic_prob > 0.25:  # Lower threshold for better categorization
                    chunk.semantic_category = self.topic_labels[chunk.dominant_topic]
                else:
                    # Check for multiple strong domains (mixed functionality)
                    strong_domains = [i for i, score in enumerate(chunk.topic_distribution) if score > 0.15]
                    if len(strong_domains) > 1:
                        chunk.semantic_category = "mixed_wire_functionality"
                    else:
                        chunk.semantic_category = "general_wire_processing"
            else:
                chunk.dominant_topic = 0
                chunk.dominant_topic_prob = 1.0 / len(self.topic_labels)
                chunk.semantic_category = "unclassified"
        
        # Update topic labels with wire processing context and counts
        topic_counts = Counter(chunk.semantic_category for chunk in chunks)
        
        # Create enhanced topic labels with wire processing context
        enhanced_labels = []
        for label in self.topic_labels:
            count = topic_counts.get(label, 0)
            # Add wire processing context to labels
            if 'iso20022' in label:
                display_name = f"ISO 20022 Messages ({count} chunks)"
            elif 'swift' in label:
                display_name = f"SWIFT Processing ({count} chunks)"
            elif 'fedwire' in label:
                display_name = f"Fedwire Operations ({count} chunks)"
            elif 'chips' in label:
                display_name = f"CHIPS Processing ({count} chunks)"
            elif 'compliance' in label:
                display_name = f"Compliance & Screening ({count} chunks)"
            elif 'investigation' in label:
                display_name = f"Exception Handling ({count} chunks)"
            elif 'correspondent' in label:
                display_name = f"Correspondent Banking ({count} chunks)"
            elif 'crossborder' in label:
                display_name = f"Cross-Border Payments ({count} chunks)"
            else:
                display_name = f"{label.replace('_', ' ').title()} ({count} chunks)"
            
            enhanced_labels.append(display_name)
        
        self.topic_labels = enhanced_labels
    
    def _extract_enhanced_keywords(self, chunks):
        """Extract enhanced keywords combining TF-IDF and wire processing domain knowledge."""
        for chunk in chunks:
            # Get TF-IDF keywords
            word_scores = []
            for word, idx in self.stemmed_vocabulary.items():
                if idx < len(chunk.tfidf_vector) and chunk.tfidf_vector[idx] > 0:
                    word_scores.append((word, chunk.tfidf_vector[idx]))
            
            # Sort by TF-IDF score
            word_scores.sort(key=lambda x: x[1], reverse=True)
            tfidf_keywords = [word for word, _ in word_scores[:8]]
            
            # Add technical keywords
            tech_keywords = []
            if chunk.function_calls:
                tech_keywords.extend(chunk.function_calls[:3])
            if chunk.procedure_name:
                tech_keywords.append(chunk.procedure_name)
            
            # Add domain-specific keywords
            domain_keywords = []
            if chunk.semantic_category in self.domain_seeds:
                domain_words = set(self.domain_seeds[chunk.semantic_category])
                chunk_words_set = set(chunk.words)
                domain_keywords = list(domain_words & chunk_words_set)[:3]
            
            # Combine and deduplicate
            all_keywords = tfidf_keywords + tech_keywords + domain_keywords
            chunk.keywords = list(dict.fromkeys(all_keywords))[:10]  # Remove duplicates, keep order

class EnhancedCorpusIndexer:
    """Enhanced corpus indexer with wire processing functionality grouping."""
    
    def __init__(self, max_features=3000, n_topics=12):
        self.chunker = TALChunker()
        self.vectorizer = EnhancedVectorizer(max_features, n_topics)
        self.chunks = []
        self.functionality_groups = {}
        self.stats = {
            'total_files': 0,
            'total_chunks': 0,
            'total_procedures': 0,
            'avg_chunk_size': 0,
            'file_types': {},
            'largest_chunk': 0,
            'smallest_chunk': 0,
            'semantic_categories': {},
            'function_calls_found': 0,
            'variable_declarations_found': 0
        }
    
    def index_directory(self, directory_path, file_extensions=None):
        """Index directory with enhanced processing."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
        
        print(f"📁 Enhanced wire processing indexing from: {directory_path}")
        
        # Find files
        matching_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    matching_files.append(os.path.join(root, file))
        
        if not matching_files:
            print(f"❌ No files found with extensions: {file_extensions}")
            return []
        
        print(f"📄 Found {len(matching_files)} files to process")
        
        # Process files
        all_chunks = []
        file_type_counts = defaultdict(int)
        
        for file_path in matching_files:
            file_ext = Path(file_path).suffix.lower()
            file_type_counts[file_ext] += 1
            
            print(f"  Processing: {os.path.basename(file_path)}")
            file_chunks = self.chunker.chunk_file(file_path)
            all_chunks.extend(file_chunks)
            print(f"    📦 {len(file_chunks)} chunks")
        
        self.chunks = all_chunks
        
        if not self.chunks:
            print("❌ No chunks created")
            return []
        
        print(f"\n📊 Total chunks: {len(self.chunks)}")
        
        # Enhanced vectorization with wire processing domain knowledge
        self.vectorizer.fit_transform(self.chunks)
        
        # Create functionality groups
        self._create_functionality_groups()
        
        # Update statistics
        self._update_enhanced_statistics(matching_files, file_type_counts)
        
        return self.chunks
    
    def _create_functionality_groups(self):
        """Group chunks by functionality and semantic similarity."""
        print("  🔗 Creating wire processing functionality groups...")
        
        # Group by semantic category
        category_groups = defaultdict(list)
        for chunk in self.chunks:
            category_groups[chunk.semantic_category].append(chunk)
        
        # Group by procedure patterns
        procedure_groups = defaultdict(list)
        for chunk in self.chunks:
            if chunk.procedure_name:
                # Group by procedure name patterns
                proc_prefix = chunk.procedure_name.split('_')[0] if '_' in chunk.procedure_name else chunk.procedure_name[:4]
                procedure_groups[proc_prefix].append(chunk)
        
        # Group by function call patterns
        function_groups = defaultdict(list)
        for chunk in self.chunks:
            for func_call in chunk.function_calls:
                function_groups[func_call].append(chunk)
        
        self.functionality_groups = {
            'semantic_categories': dict(category_groups),
            'procedure_patterns': dict(procedure_groups),
            'function_patterns': dict(function_groups)
        }
        
        print(f"    🏷️  {len(category_groups)} semantic categories")
        print(f"    🔧 {len(procedure_groups)} procedure patterns") 
        print(f"    📞 {len(function_groups)} function patterns")
    
    def _update_enhanced_statistics(self, matching_files, file_type_counts):
        """Update statistics with enhanced metrics."""
        chunk_sizes = [c.word_count for c in self.chunks]
        
        # Count semantic categories
        category_counts = Counter(chunk.semantic_category for chunk in self.chunks)
        
        # Count technical patterns
        total_function_calls = sum(len(chunk.function_calls) for chunk in self.chunks)
        total_var_declarations = sum(len(chunk.variable_declarations) for chunk in self.chunks)
        
        self.stats.update({
            'total_files': len(matching_files),
            'total_chunks': len(self.chunks),
            'total_procedures': len([c for c in self.chunks if c.procedure_name]),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            'file_types': dict(file_type_counts),
            'largest_chunk': max(chunk_sizes) if chunk_sizes else 0,
            'smallest_chunk': min(chunk_sizes) if chunk_sizes else 0,
            'semantic_categories': dict(category_counts),
            'function_calls_found': total_function_calls,
            'variable_declarations_found': total_var_declarations
        })
    
    def print_enhanced_statistics(self):
        """Print comprehensive enhanced statistics."""
        print(f"\n{'='*70}")
        print("📊 ENHANCED WIRE PROCESSING CORPUS STATISTICS")
        print("="*70)
        print(f"Files processed: {self.stats['total_files']}")
        print(f"Chunks created: {self.stats['total_chunks']}")
        print(f"Procedures found: {self.stats['total_procedures']}")
        print(f"Function calls extracted: {self.stats['function_calls_found']}")
        print(f"Variable declarations: {self.stats['variable_declarations_found']}")
        print(f"Average chunk size: {self.stats['avg_chunk_size']:.1f} words")
        print(f"Vocabulary size: {len(self.vectorizer.vocabulary)}")
        print(f"Stemmed vocabulary: {len(self.vectorizer.stemmed_vocabulary)}")
        
        if self.stats['semantic_categories']:
            print(f"\n🏷️  Wire Processing Semantic Categories:")
            for category, count in self.stats['semantic_categories'].items():
                print(f"  {category.replace('_', ' ').title()}: {count} chunks")
        
        if self.stats['file_types']:
            print(f"\n📁 File Types:")
            for ext, count in self.stats['file_types'].items():
                print(f"  {ext}: {count} files")
    
    def print_functionality_groups(self):
        """Print wire processing functionality grouping information."""
        print(f"\n{'='*70}")
        print("🔗 WIRE PROCESSING FUNCTIONALITY GROUPS")
        print("="*70)
        
        # Show top semantic categories
        semantic_groups = self.functionality_groups['semantic_categories']
        print(f"📊 Wire Processing Semantic Categories ({len(semantic_groups)} total):")
        for category, chunks in list(semantic_groups.items())[:8]:
            print(f"  {category.replace('_', ' ').title()}: {len(chunks)} chunks")
            if chunks and chunks[0].keywords:
                print(f"    Keywords: {', '.join(chunks[0].keywords[:5])}")
        
        # Show top procedure patterns
        proc_groups = self.functionality_groups['procedure_patterns']
        print(f"\n🔧 Procedure Patterns (top 10 of {len(proc_groups)}):")
        sorted_proc_groups = sorted(proc_groups.items(), key=lambda x: len(x[1]), reverse=True)
        for pattern, chunks in sorted_proc_groups[:10]:
            print(f"  {pattern}*: {len(chunks)} procedures")
        
        # Show top function patterns
        func_groups = self.functionality_groups['function_patterns']
        print(f"\n📞 Function Patterns (top 10 of {len(func_groups)}):")
        sorted_func_groups = sorted(func_groups.items(), key=lambda x: len(x[1]), reverse=True)
        for pattern, chunks in sorted_func_groups[:10]:
            print(f"  {pattern}(): {len(chunks)} references")
    
    def print_enhanced_sample_chunks(self, n=3):
        """Print sample chunks with enhanced wire processing details."""
        print(f"\n{'='*70}")
        print(f"📋 ENHANCED WIRE PROCESSING SAMPLE CHUNKS (showing first {n})")
        print("="*70)
        
        for i, chunk in enumerate(self.chunks[:n]):
            print(f"\nChunk {i}:")
            print(f"  📁 File: {os.path.basename(chunk.source_file)}")
            print(f"  📍 Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"  🔧 Procedure: {chunk.procedure_name or 'None'}")
            print(f"  📝 Words: {chunk.word_count} | Characters: {chunk.char_count}")
            print(f"  🏷️  Category: {chunk.semantic_category}")
            print(f"  🎯 Dominant Topic: {chunk.dominant_topic} ({chunk.dominant_topic_prob:.3f})")
            
            if chunk.dominant_topic < len(self.vectorizer.topic_labels):
                print(f"     Topic: {self.vectorizer.topic_labels[chunk.dominant_topic]}")
            
            print(f"  🔑 Keywords: {', '.join(chunk.keywords[:8])}")
            
            if chunk.function_calls:
                print(f"  📞 Function Calls: {', '.join(chunk.function_calls[:5])}")
            
            if chunk.variable_declarations:
                print(f"  📊 Variables: {', '.join(chunk.variable_declarations[:5])}")
            
            if chunk.control_structures:
                print(f"  🔀 Control: {', '.join(chunk.control_structures)}")
            
            print(f"  📄 Content preview:")
            lines = chunk.content.split('\n')[:4]
            for line in lines:
                clean_line = line.strip()
                if clean_line:
                    print(f"     {clean_line[:65]}{'...' if len(clean_line) > 65 else ''}")
    
    def save_enhanced_corpus(self, output_path):
        """Save enhanced corpus with all wire processing metadata."""
        print(f"\n💾 Saving enhanced wire processing corpus...")
        
        corpus_data = {
            'version': '2.0-wire-enhanced',
            'created_at': __import__('datetime').datetime.now().isoformat(),
            'chunks': [
                {
                    # Basic chunk data
                    'content': chunk.content,
                    'source_file': chunk.source_file,
                    'chunk_id': chunk.chunk_id,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'procedure_name': chunk.procedure_name,
                    'word_count': chunk.word_count,
                    'char_count': chunk.char_count,
                    
                    # Enhanced NLP data
                    'words': chunk.words,
                    'stemmed_words': chunk.stemmed_words,
                    'semantic_category': chunk.semantic_category,
                    
                    # Technical pattern data
                    'function_calls': chunk.function_calls,
                    'variable_declarations': chunk.variable_declarations,
                    'control_structures': chunk.control_structures,
                    
                    # Vector and topic data
                    'tfidf_vector': chunk.tfidf_vector,
                    'topic_distribution': chunk.topic_distribution,
                    'dominant_topic': chunk.dominant_topic,
                    'dominant_topic_prob': chunk.dominant_topic_prob,
                    'keywords': chunk.keywords
                }
                for chunk in self.chunks
            ],
            'vectorizer': {
                'vocabulary': self.vectorizer.vocabulary,
                'stemmed_vocabulary': self.vectorizer.stemmed_vocabulary,
                'idf_values': self.vectorizer.idf_values,
                'topic_labels': self.vectorizer.topic_labels,
                'topic_keywords': self.vectorizer.topic_keywords,
                'domain_seeds': self.vectorizer.domain_seeds,
                'max_features': self.vectorizer.max_features,
                'n_topics': self.vectorizer.n_topics,
                'document_count': self.vectorizer.document_count
            },
            'functionality_groups': self.functionality_groups,
            'stats': self.stats,
            'nltk_available': NLTK_AVAILABLE,
            'wire_processing_optimized': True
        }
        
        # Save main corpus file
        with open(output_path, 'wb') as f:
            pickle.dump(corpus_data, f)
        
        # Save enhanced human-readable summary
        summary_path = output_path.replace('.pkl', '_wire_enhanced_summary.json')
        summary = {
            'version': corpus_data['version'],
            'created_at': corpus_data['created_at'],
            'wire_processing_optimized': True,
            'nltk_processing': NLTK_AVAILABLE,
            'statistics': self.stats,
            'semantic_categories': list(self.stats['semantic_categories'].keys()),
            'topic_labels': self.vectorizer.topic_labels,
            'sample_procedures': [
                chunk.procedure_name for chunk in self.chunks 
                if chunk.procedure_name
            ][:15],
            'vocabulary_preview': list(self.vectorizer.vocabulary.keys())[:30],
            'stemmed_vocabulary_preview': list(self.vectorizer.stemmed_vocabulary.keys())[:30],
            'wire_processing_domains': list(self.vectorizer.domain_seeds.keys()),
            'functionality_groups_summary': {
                'semantic_categories': len(self.functionality_groups['semantic_categories']),
                'procedure_patterns': len(self.functionality_groups['procedure_patterns']),
                'function_patterns': len(self.functionality_groups['function_patterns'])
            }
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ Enhanced wire processing corpus saved to: {output_path}")
        print(f"📋 Enhanced summary saved to: {summary_path}")
        print(f"💾 Corpus: {len(self.chunks)} chunks, {len(self.vectorizer.vocabulary)} vocab")
        print(f"🌿 Stemmed vocab: {len(self.vectorizer.stemmed_vocabulary)} terms")
        print(f"🏷️  Categories: {len(self.functionality_groups['semantic_categories'])}")
        print(f"🏦 Wire processing domains: {len(self.vectorizer.domain_seeds)}")

def main():
    """Enhanced main indexer function for wire processing."""
    print("="*70)
    print("🏦 ENHANCED WIRE PROCESSING TAL CORPUS INDEXER")
    print("="*70)
    print("Wire processing semantic indexing with comprehensive domain knowledge:")
    print("• ISO 20022 message processing (pacs.008, pacs.009, pain.001, etc.)")
    print("• SWIFT message handling (MT103, MT202, gpi, UETR, etc.)")
    print("• Fedwire operations (IMAD, OMAD, type codes, BFC, etc.)")
    print("• CHIPS processing (UID, netting, settlement, etc.)")
    print("• Compliance screening (OFAC, AML, KYC, sanctions)")
    print("• Exception handling and investigations")
    print("• Cross-border and correspondent banking")
    print("• Stop word removal and stemming optimized for wire processing")
    print("• High-value term boosting for critical wire processing vocabulary")
    
    if not NLTK_AVAILABLE:
        print("\n⚠️  NLTK not found - install with: pip install nltk")
        print("   (Will use basic processing without stemming)")
    
    # Get directory
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("\n📁 Enter wire processing codebase directory: ").strip()
    
    if not directory or not os.path.exists(directory):
        print(f"❌ Invalid directory: {directory}")
        return False
    
    if not os.path.isdir(directory):
        print(f"❌ Path is not a directory: {directory}")
        return False
    
    # Get file extensions
    print(f"\nDefault extensions: .tal, .TAL, .c, .h, .cpp, .hpp")
    extensions_input = input("📄 File extensions (Enter for default): ").strip()
    if extensions_input:
        file_extensions = [ext.strip() for ext in extensions_input.split(',')]
        file_extensions = [ext if ext.startswith('.') else '.' + ext for ext in file_extensions]
    else:
        file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
    
    # Get enhanced processing parameters
    try:
        max_features = int(input("🔧 Max vocabulary features (default 3000): ") or "3000")
        n_topics = int(input("🏷️  Number of semantic topics (default 12): ") or "12")
    except ValueError:
        print("Invalid input, using defaults")
        max_features, n_topics = 3000, 12
    
    print(f"\n🚀 Starting enhanced wire processing indexing...")
    print(f"   📝 Max features: {max_features}")
    print(f"   🏷️  Topics: {n_topics}")
    print(f"   🌿 NLP processing: {'Enhanced with NLTK' if NLTK_AVAILABLE else 'Basic'}")
    print(f"   🏦 Wire processing domains: 12 specialized categories")
    
    # Create enhanced indexer and process
    indexer = EnhancedCorpusIndexer(max_features, n_topics)
    
    try:
        chunks = indexer.index_directory(directory, file_extensions)
        
        if not chunks:
            print("❌ No chunks created - check directory and file extensions")
            return False
        
        # Show enhanced results
        indexer.print_enhanced_statistics()
        indexer.print_functionality_groups()
        indexer.print_enhanced_sample_chunks()
        
        # Save enhanced corpus
        dir_name = os.path.basename(os.path.abspath(directory))
        output_file = f"wire_enhanced_tal_corpus_{dir_name}.pkl"
        
        save_choice = input(f"\n💾 Save enhanced wire processing corpus to {output_file}? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '']:
            indexer.save_enhanced_corpus(output_file)
            
            print(f"\n✅ Enhanced wire processing indexing completed successfully!")
            print(f"📁 Enhanced index: {output_file}")
            print(f"🔍 Use with enhanced searcher for wire processing code discovery")
            print(f"🏷️  12 wire processing functionality groups ready for semantic search")
            print(f"🏦 Optimized for ISO 20022, SWIFT, Fedwire, CHIPS, and compliance workflows")
        else:
            print(f"\n✅ Enhanced indexing completed (not saved)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during enhanced indexing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ Enhanced wire processing indexing failed!")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")
