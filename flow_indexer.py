#!/usr/bin/env python3
"""
Dedicated Payment Flow Indexer

Streamlined indexer for creating searchable indexes of TAL payment processing code.
Focuses on efficient index creation and storage for use with the searcher.
"""

import os
import re
import json
import pickle
import math
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path
from enum import Enum
from typing import Dict, List, Set, Tuple, Any, Optional

# Try to import NLTK components (graceful fallback if not available)
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
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

# ===== ENUM DEFINITIONS =====

class PaymentNetwork(Enum):
    """Payment network types."""
    FEDWIRE = "fedwire"
    SWIFT = "swift" 
    CHIPS = "chips"
    GENERAL = "general"

class FlowType(Enum):
    """Payment flow types across networks."""
    CUSTOMER_TRANSFER = "customer_transfer"
    BANK_TO_BANK = "bank_to_bank"
    COVER_PAYMENT = "cover_payment"
    INVESTIGATION = "investigation"
    EXCEPTION_HANDLING = "exception_handling"
    SETTLEMENT = "settlement"
    VALIDATION = "validation"
    SCREENING = "screening"
    REPORTING = "reporting"
    REPAIR = "repair"

# ===== CHUNK CLASS =====

class IndexableChunk:
    """Lightweight chunk class optimized for indexing."""
    
    def __init__(self, content, source_file, chunk_id, start_line=0, end_line=0, procedure_name=""):
        self.content = content
        self.source_file = source_file
        self.chunk_id = chunk_id
        self.start_line = start_line
        self.end_line = end_line
        self.procedure_name = procedure_name
        
        # Extract basic patterns
        self.raw_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content.lower())
        self.function_calls = self._extract_function_calls()
        self.message_patterns = self._extract_message_patterns()
        self.transaction_types = self._extract_transaction_types()
        
        # Initialize analysis results (filled by analyzer)
        self.words = []
        self.stemmed_words = []
        self.detected_networks = set()
        self.flow_capabilities = {}
        self.primary_flow = None
        self.secondary_flows = []
        self.flow_summary = ""
        self.flow_vector = []
        self.network_vector = []
        self.tfidf_vector = []
    
    def _extract_function_calls(self):
        """Extract function call patterns."""
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        return list(set(re.findall(pattern, self.content, re.IGNORECASE)))
    
    def _extract_message_patterns(self):
        """Extract payment message patterns."""
        patterns = {
            'pacs008': r'pacs\.?008|customer.credit.transfer',
            'pacs009': r'pacs\.?009|financial.institution.credit',
            'mt103': r'mt\.?103|single.customer.credit',
            'mt202': r'mt\.?202|financial.institution.transfer',
            'fedwire_1000': r'type.?code.?1000|customer.transfer',
            'fedwire_1200': r'type.?code.?1200|bank.transfer',
        }
        
        found = []
        content_lower = self.content.lower()
        for name, regex in patterns.items():
            if re.search(regex, content_lower):
                found.append(name)
        return found
    
    def _extract_transaction_types(self):
        """Extract transaction type indicators."""
        patterns = {
            'customer_transfer': r'customer.transfer|originator.*beneficiary',
            'validation': r'validat|verify|check.*format',
            'error_handling': r'error|exception|reject|repair',
            'screening': r'ofac|sanctions|aml|compliance',
        }
        
        found = []
        content_lower = self.content.lower()
        for name, regex in patterns.items():
            if re.search(regex, content_lower):
                found.append(name)
        return found
    
    def to_dict(self):
        """Convert chunk to dictionary for serialization."""
        return {
            'content': self.content,
            'source_file': self.source_file,
            'chunk_id': self.chunk_id,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'procedure_name': self.procedure_name,
            'function_calls': self.function_calls,
            'message_patterns': self.message_patterns,
            'transaction_types': self.transaction_types,
            'detected_networks': [net.value for net in self.detected_networks],
            'flow_capabilities': {flow.value: score for flow, score in self.flow_capabilities.items()},
            'primary_flow': self.primary_flow.value if self.primary_flow else None,
            'secondary_flows': [flow.value for flow in self.secondary_flows],
            'flow_summary': self.flow_summary,
            'flow_vector': self.flow_vector,
            'network_vector': self.network_vector,
            'tfidf_vector': self.tfidf_vector
        }

# ===== TEXT PROCESSOR =====

class StreamlinedTextProcessor:
    """Efficient text processor for indexing."""
    
    def __init__(self):
        self.stemmer = None
        self.stop_words = set()
        
        if NLTK_AVAILABLE:
            self.stemmer = PorterStemmer()
            try:
                self.stop_words = set(stopwords.words('english'))
            except:
                pass
        
        # Programming and TAL stop words
        self.stop_words.update({
            'int', 'char', 'string', 'void', 'return', 'if', 'else', 'while', 'for',
            'proc', 'subproc', 'begin', 'end', 'call', 'tal', 'tandem', 'system'
        })
    
    def process_words(self, words):
        """Process words efficiently."""
        if not words:
            return [], []
        
        # Filter words
        filtered = [w for w in words 
                   if len(w) >= 3 and w.lower() not in self.stop_words and not w.isdigit()]
        
        # Apply stemming if available
        if self.stemmer:
            stemmed = [self.stemmer.stem(w) for w in filtered]
        else:
            stemmed = filtered.copy()
        
        return filtered, stemmed

# ===== CHUNKER =====

class EfficientChunker:
    """Efficient file chunker."""
    
    def __init__(self):
        self.procedure_patterns = [
            re.compile(r'^\s*(?:PROC|SUBPROC)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^\s*(\w+)\s*\([^)]*\)\s*{', re.MULTILINE),
            re.compile(r'^\s*(?:static\s+)?(?:int|void|char\*?)\s+(\w+)\s*\(', re.MULTILINE),
        ]
    
    def chunk_file(self, file_path):
        """Chunk a file efficiently."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return []
        
        if not content.strip():
            return []
        
        return self._create_chunks(content, file_path)
    
    def _create_chunks(self, content, file_path):
        """Create chunks from content."""
        lines = content.split('\n')
        chunks = []
        chunk_id = 0
        
        # Find procedure boundaries
        procedures = []
        for pattern in self.procedure_patterns:
            for match in pattern.finditer(content):
                line_no = content[:match.start()].count('\n')
                proc_name = match.group(1)
                procedures.append((line_no, proc_name))
        
        procedures.sort()
        
        # Create chunks
        current_chunk = []
        chunk_start = 0
        proc_name = ""
        
        for line_no, line in enumerate(lines):
            # Check for new procedure
            for proc_line, proc in procedures:
                if proc_line == line_no:
                    # Save current chunk
                    if current_chunk and any(l.strip() for l in current_chunk):
                        chunk_content = '\n'.join(current_chunk)
                        chunk = IndexableChunk(
                            content=chunk_content,
                            source_file=file_path,
                            chunk_id=chunk_id,
                            start_line=chunk_start,
                            end_line=line_no - 1,
                            procedure_name=proc_name
                        )
                        chunks.append(chunk)
                        chunk_id += 1
                    
                    # Start new chunk
                    current_chunk = [line]
                    chunk_start = line_no
                    proc_name = proc
                    break
            else:
                current_chunk.append(line)
                
                # Split large chunks
                if len(current_chunk) > 100:
                    chunk_content = '\n'.join(current_chunk)
                    if chunk_content.strip():
                        chunk = IndexableChunk(
                            content=chunk_content,
                            source_file=file_path,
                            chunk_id=chunk_id,
                            start_line=chunk_start,
                            end_line=line_no,
                            procedure_name=proc_name
                        )
                        chunks.append(chunk)
                        chunk_id += 1
                    current_chunk = []
                    chunk_start = line_no + 1
                    proc_name = ""
        
        # Handle remaining content
        if current_chunk and any(l.strip() for l in current_chunk):
            chunk_content = '\n'.join(current_chunk)
            chunk = IndexableChunk(
                content=chunk_content,
                source_file=file_path,
                chunk_id=chunk_id,
                start_line=chunk_start,
                end_line=len(lines) - 1,
                procedure_name=proc_name
            )
            chunks.append(chunk)
        
        return chunks

# ===== FLOW ANALYZER =====

class FlowAnalyzer:
    """Analyze payment flows efficiently."""
    
    def __init__(self):
        self.flow_patterns = {
            FlowType.CUSTOMER_TRANSFER: {
                'keywords': {'customer', 'transfer', 'originator', 'beneficiary', 'individual'},
                'patterns': [r'customer.*transfer', r'originator.*beneficiary', r'type.?code.?1000']
            },
            FlowType.VALIDATION: {
                'keywords': {'validat', 'verify', 'check', 'format', 'mandatory'},
                'patterns': [r'validat.*process', r'check.*format', r'verify.*field']
            },
            FlowType.EXCEPTION_HANDLING: {
                'keywords': {'exception', 'error', 'reject', 'repair', 'fail'},
                'patterns': [r'exception.*handl', r'error.*process', r'reject.*payment']
            },
            FlowType.SCREENING: {
                'keywords': {'ofac', 'sanctions', 'aml', 'compliance', 'screening'},
                'patterns': [r'ofac.*screen', r'sanctions.*check', r'aml.*monitor']
            },
            FlowType.SETTLEMENT: {
                'keywords': {'settlement', 'clearing', 'netting', 'rtgs'},
                'patterns': [r'settlement.*process', r'clearing.*house', r'net.*position']
            }
        }
        
        self.network_patterns = {
            PaymentNetwork.FEDWIRE: {
                'keywords': {'fedwire', 'imad', 'omad', 'federal_reserve', 'type_code'},
                'patterns': [r'fedwire.*process', r'type.*code.*\d{4}', r'imad.*generate']
            },
            PaymentNetwork.SWIFT: {
                'keywords': {'swift', 'mt103', 'mt202', 'bic', 'gpi', 'uetr'},
                'patterns': [r'swift.*process', r'mt\d{3}', r'gpi.*track']
            },
            PaymentNetwork.CHIPS: {
                'keywords': {'chips', 'uid', 'netting', 'clearing_house'},
                'patterns': [r'chips.*process', r'uid.*generat', r'clearing.*house']
            }
        }
    
    def analyze_chunk(self, chunk: IndexableChunk, text_processor: StreamlinedTextProcessor):
        """Analyze chunk for flows and networks."""
        # Process words
        chunk.words, chunk.stemmed_words = text_processor.process_words(chunk.raw_words)
        
        # Detect networks
        self._detect_networks(chunk)
        
        # Analyze flows
        self._analyze_flows(chunk)
        
        # Set primary flow
        self._set_primary_flow(chunk)
        
        # Create summary
        self._create_summary(chunk)
    
    def _detect_networks(self, chunk):
        """Detect payment networks."""
        content_lower = chunk.content.lower()
        chunk_words = set(chunk.words + chunk.stemmed_words)
        
        for network, data in self.network_patterns.items():
            score = 0
            
            # Keyword matching
            keyword_matches = len(chunk_words & data['keywords'])
            score += keyword_matches * 2
            
            # Pattern matching
            for pattern in data['patterns']:
                if re.search(pattern, content_lower):
                    score += 3
            
            # Message pattern boost
            if network == PaymentNetwork.SWIFT and any('mt' in p for p in chunk.message_patterns):
                score += 2
            elif network == PaymentNetwork.FEDWIRE and any('fedwire' in p for p in chunk.message_patterns):
                score += 2
            
            if score > 2:
                chunk.detected_networks.add(network)
    
    def _analyze_flows(self, chunk):
        """Analyze payment flow capabilities."""
        content_lower = chunk.content.lower()
        chunk_words = set(chunk.words + chunk.stemmed_words)
        
        for flow, data in self.flow_patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = len(chunk_words & data['keywords'])
            score += keyword_matches * 0.5
            
            # Pattern matching
            for pattern in data['patterns']:
                if re.search(pattern, content_lower):
                    score += 1.0
            
            # Function name boost
            if chunk.procedure_name:
                proc_lower = chunk.procedure_name.lower()
                for keyword in data['keywords']:
                    if keyword in proc_lower:
                        score += 0.8
            
            # Transaction type boost
            flow_transaction_map = {
                FlowType.CUSTOMER_TRANSFER: ['customer_transfer'],
                FlowType.VALIDATION: ['validation'],
                FlowType.EXCEPTION_HANDLING: ['error_handling'],
                FlowType.SCREENING: ['screening']
            }
            
            if flow in flow_transaction_map:
                for trans_type in flow_transaction_map[flow]:
                    if trans_type in chunk.transaction_types:
                        score += 0.6
            
            chunk.flow_capabilities[flow] = score
    
    def _set_primary_flow(self, chunk):
        """Set primary and secondary flows."""
        sorted_flows = sorted(chunk.flow_capabilities.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_flows and sorted_flows[0][1] > 0.5:
            chunk.primary_flow = sorted_flows[0][0]
        
        chunk.secondary_flows = [
            flow for flow, score in sorted_flows[1:] 
            if score > 0.3 and score >= sorted_flows[0][1] * 0.6
        ][:2]
    
    def _create_summary(self, chunk):
        """Create flow summary."""
        networks = [net.value.upper() for net in chunk.detected_networks]
        
        if chunk.primary_flow:
            flow_name = chunk.primary_flow.value.replace('_', ' ').title()
            if networks:
                chunk.flow_summary = f"{'/'.join(networks)} {flow_name}"
            else:
                chunk.flow_summary = flow_name
        else:
            if networks:
                chunk.flow_summary = f"{'/'.join(networks)} Processing"
            else:
                chunk.flow_summary = "General Processing"

# ===== MAIN INDEXER =====

class PaymentFlowIndexer:
    """Main indexer for creating searchable payment flow indexes."""
    
    def __init__(self, max_features=2000):
        self.chunker = EfficientChunker()
        self.text_processor = StreamlinedTextProcessor()
        self.flow_analyzer = FlowAnalyzer()
        self.max_features = max_features
        
        self.chunks = []
        self.vocabulary = {}
        self.stats = {}
    
    def index_directory(self, directory_path, file_extensions=None, output_file=None):
        """Index a directory and save the index."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
        
        print(f"🏦 Payment Flow Indexer")
        print(f"📁 Indexing: {directory_path}")
        
        start_time = time.time()
        
        # Find files
        matching_files = self._find_files(directory_path, file_extensions)
        if not matching_files:
            print(f"❌ No files found with extensions: {file_extensions}")
            return False
        
        print(f"📄 Found {len(matching_files)} files")
        
        # Process files
        self._process_files(matching_files)
        
        if not self.chunks:
            print("❌ No code chunks created")
            return False
        
        # Analyze flows
        self._analyze_payment_flows()
        
        # Create vectors
        self._create_vectors()
        
        # Update statistics
        self._update_statistics(matching_files)
        
        # Save index
        if output_file is None:
            dir_name = os.path.basename(os.path.abspath(directory_path))
            output_file = f"payment_flow_index_{dir_name}.pkl"
        
        success = self._save_index(output_file)
        
        elapsed_time = time.time() - start_time
        
        # Print results
        self._print_results(elapsed_time, output_file)
        
        return success
    
    def _find_files(self, directory_path, file_extensions):
        """Find matching files."""
        matching_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    matching_files.append(os.path.join(root, file))
        return matching_files
    
    def _process_files(self, file_paths):
        """Process files into chunks."""
        print("🔄 Processing files...")
        
        self.chunks = []
        for i, file_path in enumerate(file_paths):
            if i % 10 == 0:
                print(f"   {i+1}/{len(file_paths)}: {os.path.basename(file_path)}")
            
            file_chunks = self.chunker.chunk_file(file_path)
            self.chunks.extend(file_chunks)
        
        print(f"📦 Created {len(self.chunks)} code chunks")
    
    def _analyze_payment_flows(self):
        """Analyze payment flows for all chunks."""
        print("🎯 Analyzing payment flows...")
        
        for i, chunk in enumerate(self.chunks):
            if i % 100 == 0 and i > 0:
                print(f"   Analyzed {i}/{len(self.chunks)} chunks")
            
            self.flow_analyzer.analyze_chunk(chunk, self.text_processor)
        
        flows_found = len([c for c in self.chunks if c.primary_flow])
        networks_found = len([c for c in self.chunks if c.detected_networks])
        
        print(f"✅ Flow analysis complete:")
        print(f"   🔄 {flows_found} chunks with identified flows")
        print(f"   🌐 {networks_found} chunks with detected networks")
    
    def _create_vectors(self):
        """Create simplified vectors."""
        print("📊 Creating vectors...")
        
        # Build basic vocabulary
        word_counts = defaultdict(int)
        for chunk in self.chunks:
            for word in set(chunk.stemmed_words):
                word_counts[word] += 1
        
        # Filter vocabulary
        min_freq = max(2, len(self.chunks) // 100)
        max_freq = len(self.chunks) // 2
        
        vocab_words = [
            word for word, count in word_counts.items()
            if min_freq <= count <= max_freq and len(word) >= 3
        ]
        
        vocab_words.sort(key=lambda w: word_counts[w], reverse=True)
        if len(vocab_words) > self.max_features:
            vocab_words = vocab_words[:self.max_features]
        
        self.vocabulary = {word: idx for idx, word in enumerate(vocab_words)}
        
        # Create vectors for chunks
        for chunk in self.chunks:
            # Flow vector
            chunk.flow_vector = [
                chunk.flow_capabilities.get(flow, 0.0) for flow in FlowType
            ]
            
            # Network vector
            chunk.network_vector = [
                1.0 if network in chunk.detected_networks else 0.0 
                for network in PaymentNetwork
            ]
            
            # Simple TF-IDF vector
            chunk.tfidf_vector = [0.0] * len(self.vocabulary)
            word_counts = Counter(chunk.stemmed_words)
            total_words = len(chunk.stemmed_words)
            
            if total_words > 0:
                for word, count in word_counts.items():
                    if word in self.vocabulary:
                        tf = count / total_words
                        chunk.tfidf_vector[self.vocabulary[word]] = tf
        
        print(f"   📝 Vocabulary size: {len(self.vocabulary)}")
    
    def _update_statistics(self, file_paths):
        """Update indexing statistics."""
        flow_counts = defaultdict(int)
        network_counts = defaultdict(int)
        message_counts = defaultdict(int)
        
        for chunk in self.chunks:
            if chunk.primary_flow:
                flow_counts[chunk.primary_flow.value] += 1
            
            for network in chunk.detected_networks:
                network_counts[network.value] += 1
            
            for pattern in chunk.message_patterns:
                message_counts[pattern] += 1
        
        self.stats = {
            'total_files': len(file_paths),
            'total_chunks': len(self.chunks),
            'chunks_with_procedures': len([c for c in self.chunks if c.procedure_name]),
            'chunks_with_flows': len([c for c in self.chunks if c.primary_flow]),
            'chunks_with_networks': len([c for c in self.chunks if c.detected_networks]),
            'vocabulary_size': len(self.vocabulary),
            'flow_distribution': dict(flow_counts),
            'network_distribution': dict(network_counts),
            'message_distribution': dict(message_counts)
        }
    
    def _save_index(self, output_file):
        """Save the searchable index."""
        print(f"💾 Saving index...")
        
        try:
            index_data = {
                'version': '1.0-payment-flow-index',
                'created_at': __import__('datetime').datetime.now().isoformat(),
                'chunks': [chunk.to_dict() for chunk in self.chunks],
                'vocabulary': self.vocabulary,
                'flow_types': [flow.value for flow in FlowType],
                'network_types': [net.value for net in PaymentNetwork],
                'statistics': self.stats
            }
            
            with open(output_file, 'wb') as f:
                pickle.dump(index_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Save summary
            summary_file = output_file.replace('.pkl', '_summary.json')
            summary = {
                'version': index_data['version'],
                'created_at': index_data['created_at'],
                'statistics': self.stats,
                'sample_procedures': [
                    chunk.procedure_name for chunk in self.chunks[:20] 
                    if chunk.procedure_name
                ],
                'sample_flows': list(set([
                    chunk.primary_flow.value for chunk in self.chunks 
                    if chunk.primary_flow
                ])),
                'sample_networks': list(set([
                    net.value for chunk in self.chunks 
                    for net in chunk.detected_networks
                ]))
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving index: {e}")
            return False
    
    def _print_results(self, elapsed_time, output_file):
        """Print indexing results."""
        print(f"\n{'='*60}")
        print("✅ INDEXING COMPLETED SUCCESSFULLY")
        print(f"{'='*60}")
        
        print(f"⏱️  Processing time: {elapsed_time:.1f} seconds")
        print(f"📁 Index file: {output_file}")
        print(f"📋 Summary file: {output_file.replace('.pkl', '_summary.json')}")
        
        print(f"\n📊 Index Statistics:")
        print(f"   Files processed: {self.stats['total_files']}")
        print(f"   Code chunks: {self.stats['total_chunks']}")
        print(f"   Procedures found: {self.stats['chunks_with_procedures']}")
        print(f"   Chunks with flows: {self.stats['chunks_with_flows']}")
        print(f"   Chunks with networks: {self.stats['chunks_with_networks']}")
        print(f"   Vocabulary size: {self.stats['vocabulary_size']}")
        
        if self.stats['flow_distribution']:
            print(f"\n🔄 Payment Flow Distribution:")
            for flow, count in sorted(self.stats['flow_distribution'].items(), 
                                    key=lambda x: x[1], reverse=True):
                flow_name = flow.replace('_', ' ').title()
                print(f"   {flow_name}: {count} chunks")
        
        if self.stats['network_distribution']:
            print(f"\n🌐 Payment Network Distribution:")
            for network, count in sorted(self.stats['network_distribution'].items(), 
                                       key=lambda x: x[1], reverse=True):
                print(f"   {network.upper()}: {count} chunks")
        
        print(f"\n🔍 Next Steps:")
        print(f"   Use the searcher to explore your indexed code:")
        print(f"   python payment_flow_searcher.py {output_file}")
        
        print(f"\n💡 Index ready for payment flow code discovery!")

# ===== COMMAND LINE INTERFACE =====

def main():
    """Main function for command line usage."""
    print("="*60)
    print("🏦 PAYMENT FLOW CODE INDEXER")
    print("="*60)
    print("Creates searchable indexes for TAL payment processing code")
    
    # Get directory to index
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("\n📁 Enter directory to index: ").strip()
    
    if not directory or not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        return False
    
    if not os.path.isdir(directory):
        print(f"❌ Path is not a directory: {directory}")
        return False
    
    # Get output file
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        dir_name = os.path.basename(os.path.abspath(directory))
        default_output = f"payment_flow_index_{dir_name}.pkl"
        output_file = input(f"📄 Output file (default: {default_output}): ").strip()
        if not output_file:
            output_file = default_output
    
    # Get file extensions
    extensions_input = input("📝 File extensions (default: .tal,.c,.h): ").strip()
    if extensions_input:
        file_extensions = [ext.strip() for ext in extensions_input.split(',')]
        file_extensions = [ext if ext.startswith('.') else '.' + ext for ext in file_extensions]
    else:
        file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
    
    # Get max features
    try:
        max_features = int(input("🔧 Max vocabulary size (default: 2000): ") or "2000")
    except ValueError:
        max_features = 2000
    
    print(f"\n🚀 Starting indexing process...")
    print(f"   📁 Directory: {directory}")
    print(f"   📄 Output: {output_file}")
    print(f"   📝 Extensions: {', '.join(file_extensions)}")
    print(f"   🔧 Max features: {max_features}")
    print(f"   🌿 NLP: {'Enhanced with NLTK' if NLTK_AVAILABLE else 'Basic'}")
    
    # Create indexer and run
    try:
        indexer = PaymentFlowIndexer(max_features=max_features)
        success = indexer.index_directory(directory, file_extensions, output_file)
        
        if success:
            return True
        else:
            print("❌ Indexing failed")
            return False
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Indexing interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Indexing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_index_from_config():
    """Create index using a configuration file."""
    config_file = input("📋 Enter config file path (JSON): ").strip()
    
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        directory = config['directory']
        output_file = config.get('output_file', 'payment_flow_index.pkl')
        file_extensions = config.get('file_extensions', ['.tal', '.c', '.h'])
        max_features = config.get('max_features', 2000)
        
        print(f"📋 Using configuration:")
        print(f"   Directory: {directory}")
        print(f"   Output: {output_file}")
        print(f"   Extensions: {file_extensions}")
        print(f"   Max features: {max_features}")
        
        indexer = PaymentFlowIndexer(max_features=max_features)
        return indexer.index_directory(directory, file_extensions, output_file)
        
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def batch_index_multiple_directories():
    """Index multiple directories in batch."""
    print("📦 Batch indexing mode")
    print("Enter directories to index (one per line, empty line to finish):")
    
    directories = []
    while True:
        directory = input("Directory: ").strip()
        if not directory:
            break
        if os.path.exists(directory) and os.path.isdir(directory):
            directories.append(directory)
            print(f"   ✅ Added: {directory}")
        else:
            print(f"   ❌ Invalid: {directory}")
    
    if not directories:
        print("❌ No valid directories provided")
        return False
    
    # Get common settings
    file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
    max_features = 2000
    
    print(f"\n🚀 Batch indexing {len(directories)} directories...")
    
    success_count = 0
    for i, directory in enumerate(directories, 1):
        print(f"\n[{i}/{len(directories)}] Processing: {directory}")
        
        dir_name = os.path.basename(os.path.abspath(directory))
        output_file = f"payment_flow_index_{dir_name}.pkl"
        
        try:
            indexer = PaymentFlowIndexer(max_features=max_features)
            if indexer.index_directory(directory, file_extensions, output_file):
                success_count += 1
                print(f"   ✅ Success: {output_file}")
            else:
                print(f"   ❌ Failed: {directory}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Batch indexing complete:")
    print(f"   ✅ Successful: {success_count}/{len(directories)}")
    print(f"   ❌ Failed: {len(directories) - success_count}/{len(directories)}")
    
    return success_count > 0

def interactive_mode():
    """Interactive indexing mode with menu."""
    while True:
        print(f"\n{'='*50}")
        print("🏦 PAYMENT FLOW INDEXER - INTERACTIVE MODE")
        print(f"{'='*50}")
        print("1. Index single directory")
        print("2. Index from configuration file") 
        print("3. Batch index multiple directories")
        print("4. View example configuration")
        print("5. Test indexer with sample data")
        print("0. Exit")
        
        choice = input("\nSelect option (0-5): ").strip()
        
        if choice == '0':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            main()
        elif choice == '2':
            create_index_from_config()
        elif choice == '3':
            batch_index_multiple_directories()
        elif choice == '4':
            show_example_config()
        elif choice == '5':
            test_indexer_with_samples()
        else:
            print("❌ Invalid choice")

def show_example_config():
    """Show example configuration file."""
    example_config = {
        "directory": "/path/to/your/tal/code",
        "output_file": "my_payment_index.pkl",
        "file_extensions": [".tal", ".TAL", ".c", ".h"],
        "max_features": 2000,
        "description": "Index configuration for payment processing TAL code"
    }
    
    print(f"\n📋 Example Configuration File (save as config.json):")
    print("="*50)
    print(json.dumps(example_config, indent=2))
    print("="*50)
    
    save_example = input("\nSave example config to file? (y/n): ").strip().lower()
    if save_example.startswith('y'):
        with open('example_config.json', 'w') as f:
            json.dump(example_config, f, indent=2)
        print("✅ Saved to: example_config.json")

def test_indexer_with_samples():
    """Test the indexer with sample TAL code."""
    import tempfile
    
    print("🧪 Creating sample TAL files for testing...")
    
    test_dir = tempfile.mkdtemp(prefix="tal_test_")
    
    # Sample TAL code
    sample_code = """
PROC VALIDATE_SWIFT_MT103(message_buffer);
BEGIN
    ! Validate SWIFT MT103 message format
    INT validation_result := 1;
    STRING bic_field[11];
    STRING amount_field[15];
    
    ! Validate BIC code format
    CALL EXTRACT_BIC_CODE(message_buffer, bic_field);
    IF NOT VALIDATE_BIC_FORMAT(bic_field) THEN
        validation_result := 0;
        CALL LOG_VALIDATION_ERROR("Invalid BIC", bic_field);
    END;
    
    ! Check OFAC sanctions screening
    IF SCREEN_OFAC_LIST(message_buffer) = 0 THEN
        validation_result := 0;
        CALL HOLD_PAYMENT_FOR_REVIEW(message_buffer);
    END;
    
    RETURN validation_result;
END;

PROC PROCESS_FEDWIRE_1000(wire_data);
BEGIN
    ! Process Fedwire type 1000 customer transfer
    STRING imad[9];
    STRING beneficiary_account[34];
    
    CALL GENERATE_IMAD(imad);
    CALL EXTRACT_BENEFICIARY_ACCOUNT(wire_data, beneficiary_account);
    
    ! Validate account format
    IF VALIDATE_ACCOUNT_NUMBER(beneficiary_account) THEN
        CALL EXECUTE_WIRE_TRANSFER(wire_data, imad);
    ELSE
        CALL REJECT_WIRE_TRANSFER(imad, "Invalid account");
    END;
END;
"""
    
    # Write sample file
    sample_file = os.path.join(test_dir, "sample_payment_code.tal")
    with open(sample_file, 'w') as f:
        f.write(sample_code)
    
    print(f"   📄 Created: {sample_file}")
    
    # Index the sample
    output_file = os.path.join(test_dir, "test_index.pkl")
    
    try:
        indexer = PaymentFlowIndexer(max_features=500)
        success = indexer.index_directory(test_dir, ['.tal'], output_file)
        
        if success:
            print(f"\n✅ Test indexing successful!")
            print(f"📁 Test index: {output_file}")
            print(f"🔍 Test with searcher:")
            print(f"   python payment_flow_searcher.py {output_file}")
            
            # Clean up option
            cleanup = input("\nDelete test files? (y/n): ").strip().lower()
            if cleanup.startswith('y'):
                import shutil
                shutil.rmtree(test_dir)
                print("🧹 Test files cleaned up")
            else:
                print(f"📁 Test files kept in: {test_dir}")
        else:
            print("❌ Test indexing failed")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

# ===== UTILITY FUNCTIONS =====

def validate_directory(directory_path):
    """Validate directory and show file count."""
    if not os.path.exists(directory_path):
        return False, "Directory does not exist"
    
    if not os.path.isdir(directory_path):
        return False, "Path is not a directory"
    
    # Count files
    file_count = 0
    tal_count = 0
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_count += 1
            if file.endswith(('.tal', '.TAL', '.c', '.h', '.cpp', '.hpp')):
                tal_count += 1
    
    if tal_count == 0:
        return False, f"No TAL/C files found (total files: {file_count})"
    
    return True, f"Found {tal_count} TAL/C files (total: {file_count})"

def estimate_processing_time(directory_path, file_extensions):
    """Estimate processing time based on file count and size."""
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                    file_count += 1
                except:
                    pass
    
    if file_count == 0:
        return "No files to process"
    
    # Rough estimation: ~1MB per minute
    mb_size = total_size / (1024 * 1024)
    estimated_minutes = max(0.1, mb_size * 0.5)  # Conservative estimate
    
    if estimated_minutes < 1:
        return f"~{estimated_minutes*60:.0f} seconds ({file_count} files, {mb_size:.1f}MB)"
    else:
        return f"~{estimated_minutes:.1f} minutes ({file_count} files, {mb_size:.1f}MB)"

def show_usage():
    """Show usage instructions."""
    print("""
Usage Examples:

1. Basic indexing:
   python payment_indexer.py /path/to/tal/code

2. Specify output file:
   python payment_indexer.py /path/to/tal/code my_index.pkl

3. Interactive mode:
   python payment_indexer.py

4. Config file mode:
   python payment_indexer.py --config config.json

5. Batch mode:
   python payment_indexer.py --batch

Command line options:
  --help        Show this help
  --config FILE Use configuration file
  --batch       Batch index multiple directories
  --interactive Interactive mode (default if no args)
""")

if __name__ == "__main__":
    try:
        # Handle command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] in ['--help', '-h']:
                show_usage()
            elif sys.argv[1] == '--config':
                create_index_from_config()
            elif sys.argv[1] == '--batch':
                batch_index_multiple_directories()
            elif sys.argv[1] == '--interactive':
                interactive_mode()
            else:
                # Standard directory indexing
                main()
        else:
            # No arguments - interactive mode
            interactive_mode()
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
