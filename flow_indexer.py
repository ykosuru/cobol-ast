#!/usr/bin/env python3
"""
Fixed Flow-Based TAL Corpus Indexer for Wire Processing

Complete implementation with proper imports and class definitions.
Creates semantic indexes with payment flow capabilities for Federal Reserve, SWIFT, and CHIPS.
"""

import os
import re
import json
import pickle
import math
import sys
from collections import defaultdict, Counter
from pathlib import Path
from enum import Enum
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass

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

class ISOMessageType(Enum):
    """ISO 20022 message types relevant to Federal Reserve systems."""
    # Customer Credit Transfers
    PACS008 = "pacs.008.001"  # FIToFICstmrCdtTrf
    PACS009 = "pacs.009.001"  # FIToFICstmrCdtTrf (Return)
    PACS002 = "pacs.002.001"  # FIToFIPmtStsRpt
    PACS004 = "pacs.004.001"  # PmtRtr
    PACS007 = "pacs.007.001"  # FIToFIPmtRvsl
    
    # Customer Payment Initiation
    PAIN001 = "pain.001.001"  # CstmrCdtTrfInitn
    PAIN002 = "pain.002.001"  # CstmrPmtStsRpt
    
    # Cash Management
    CAMT052 = "camt.052.001"  # BkToCstmrAcctRpt
    CAMT053 = "camt.053.001"  # BkToCstmrStmt
    CAMT054 = "camt.054.001"  # BkToCstmrDbtCdtNtfctn
    CAMT056 = "camt.056.001"  # FIToFICstmrCdtTrfCxlReq
    CAMT029 = "camt.029.001"  # ResolutionOfInvestigation

class ValidationScope(Enum):
    """Scope of validation being performed."""
    FIELD_LEVEL = "field_level"           # Individual field validation
    MESSAGE_LEVEL = "message_level"       # Entire message structure
    BUSINESS_RULE = "business_rule"       # Business logic validation
    CROSS_REFERENCE = "cross_reference"   # Cross-field dependencies
    SEQUENCE = "sequence"                 # Message sequence validation
    DUPLICATE = "duplicate"               # Duplicate detection
    FORMAT = "format"                     # Format compliance (XML, character sets)
    REGULATORY = "regulatory"             # Fed-specific regulatory rules

class ValidationCategory(Enum):
    """Categories of validation rules."""
    MANDATORY_FIELD = "mandatory_field"
    OPTIONAL_FIELD = "optional_field"
    FIELD_FORMAT = "field_format"
    FIELD_LENGTH = "field_length"
    CODE_LIST = "code_list"
    PATTERN_MATCH = "pattern_match"
    BUSINESS_LOGIC = "business_logic"
    CROSS_FIELD = "cross_field"
    CONDITIONAL = "conditional"
    REGULATORY_RULE = "regulatory_rule"

# ===== DATA CLASSES =====

@dataclass
class ValidationPattern:
    """Represents a specific validation pattern found in code."""
    validation_type: ValidationCategory
    scope: ValidationScope
    iso_message_type: Optional[ISOMessageType]
    field_path: str  # XPath-like field reference
    validation_rule: str  # Description of the rule
    error_code: Optional[str]  # Associated error code
    code_snippet: str  # Relevant code fragment
    line_range: Tuple[int, int]  # Start and end lines

# ===== CHUNK CLASSES =====

class FlowBasedChunk:
    """Enhanced chunk representation with payment flow metadata."""
    
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
        self.message_patterns = self._extract_message_patterns()
        self.transaction_types = self._extract_transaction_types()
        
        # Payment flow analysis
        self.detected_networks = set()  # Set of PaymentNetwork
        self.flow_capabilities = {}  # FlowType -> confidence score
        self.primary_flow = None  # Primary FlowType
        self.secondary_flows = []  # Secondary FlowType list
        
        # Network-specific attributes
        self.fedwire_type_codes = self._extract_fedwire_types()
        self.swift_message_types = self._extract_swift_message_types()
        self.chips_features = self._extract_chips_features()
        
        # ISO validation patterns
        self.validation_patterns = []  # List of ValidationPattern objects
        self.iso_message_types = []    # List of detected ISO message types
        
        # Will be filled by vectorizer
        self.flow_vector = []  # Multi-dimensional flow capability vector
        self.network_vector = []  # Network-specific vector
        self.tfidf_vector = []
        self.keywords = []
        self.flow_summary = ""
    
    def _extract_function_calls(self):
        """Extract function call patterns from code."""
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        return list(set(re.findall(pattern, self.content, re.IGNORECASE)))
    
    def _extract_variable_declarations(self):
        """Extract variable declaration patterns."""
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
    
    def _extract_message_patterns(self):
        """Extract payment message patterns."""
        message_patterns = {
            # ISO 20022 messages
            'pacs008': r'pacs\.?008|customer.credit.transfer',
            'pacs009': r'pacs\.?009|financial.institution.credit',
            'pacs002': r'pacs\.?002|payment.status.report',
            'pain001': r'pain\.?001|customer.credit.transfer.initiation',
            'camt056': r'camt\.?056|cancellation.request',
            'camt029': r'camt\.?029|resolution.investigation',
            
            # SWIFT MT messages
            'mt103': r'mt\.?103|single.customer.credit',
            'mt202': r'mt\.?202|financial.institution.transfer',
            'mt202cov': r'mt\.?202\.?cov|cover.payment',
            'mt199': r'mt\.?199|free.format',
            'mt299': r'mt\.?299|free.format.proprietary',
            
            # Fedwire patterns
            'fedwire_1000': r'type.?code.?1000|customer.transfer',
            'fedwire_1200': r'type.?code.?1200|bank.transfer',
            'fedwire_1400': r'type.?code.?1400|drawdown',
            'fedwire_1500': r'type.?code.?1500|customer.transfer.plus'
        }
        
        found_patterns = []
        content_lower = self.content.lower()
        
        for pattern_name, regex in message_patterns.items():
            if re.search(regex, content_lower):
                found_patterns.append(pattern_name)
        
        return found_patterns
    
    def _extract_transaction_types(self):
        """Extract transaction type indicators."""
        transaction_patterns = {
            # Fedwire transaction types
            'customer_transfer': r'customer.transfer|originator.*beneficiary',
            'bank_transfer': r'bank.transfer|interbank|correspondent',
            'drawdown': r'drawdown|draw.down|pull.funds',
            'settlement': r'settlement|net.settle|gross.settle',
            
            # SWIFT transaction types
            'cover_payment': r'cover.payment|mt202.*cover',
            'customer_payment': r'customer.payment|mt103',
            'gpi_tracking': r'gpi|uetr|tracker',
            
            # CHIPS transaction types
            'prefunded': r'prefunded|real.?time.settle',
            'netting': r'netting|net.position|batch.settle',
            
            # Exception types
            'investigation': r'investigation|inquiry|research',
            'repair': r'repair|fix|correct',
            'return': r'return|reversal|recall',
            'reject': r'reject|deny|refuse'
        }
        
        found_types = []
        content_lower = self.content.lower()
        
        for type_name, regex in transaction_patterns.items():
            if re.search(regex, content_lower):
                found_types.append(type_name)
        
        return found_types
    
    def _extract_fedwire_types(self):
        """Extract Fedwire-specific type codes and features."""
        fedwire_patterns = [
            r'type.?code.?(\d{4})',  # Type codes like 1000, 1200, etc.
            r'imad',  # Input Message Accountability Data
            r'omad',  # Output Message Accountability Data
            r'fedline',  # FedLine Advantage
            r'bfc',  # Business Function Code
            r'participant.?(\w+)'  # Participant codes
        ]
        
        found_features = []
        for pattern in fedwire_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            found_features.extend(matches)
        
        return found_features
    
    def __hash__(self):
        """Make chunk hashable for use in sets."""
        return hash((self.source_file, self.chunk_id, self.start_line, self.end_line))
    
    def __eq__(self, other):
        """Define equality for chunks."""
        if not isinstance(other, FlowBasedChunk):
            return False
        return (self.source_file == other.source_file and 
                self.chunk_id == other.chunk_id and
                self.start_line == other.start_line and
                self.end_line == other.end_line)
    
    def __repr__(self):
        """String representation for debugging."""
        return f"FlowBasedChunk(file={os.path.basename(self.source_file)}, id={self.chunk_id}, proc={self.procedure_name})"
    
    def _extract_swift_message_types(self):
        """Extract SWIFT-specific message types and features."""
        swift_patterns = [
            r'mt(\d{3})',  # MT message types
            r'pacs\.(\d{3})',  # ISO 20022 pacs messages
            r'pain\.(\d{3})',  # ISO 20022 pain messages
            r'camt\.(\d{3})',  # ISO 20022 camt messages
            r'bic.?([A-Z0-9]{8,11})',  # BIC codes
            r'uetr',  # Unique End-to-End Transaction Reference
            r'gpi'  # Global Payments Innovation
        ]
        
        found_types = []
        for pattern in swift_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            found_types.extend(matches)
        
        return found_types
    
    def _extract_chips_features(self):
        """Extract CHIPS-specific features."""
        chips_patterns = [
            r'uid',  # Universal Identifier
            r'sequence.?(\d+)',  # Sequence numbers
            r'prefunded',
            r'netting',
            r'participant.?(\w+)'
        ]
        
        found_features = []
        for pattern in chips_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            found_features.extend(matches)
        
        return found_features

# ===== TEXT PROCESSOR =====

class EnhancedTextProcessor:
    """Enhanced text processing with NLP capabilities for payment flows."""
    
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
        
        # Add TAL-specific stop words
        tal_stop_words = {
            'tal', 'tandem', 'guardian', 'oss', 'nsk', 'system', 'file', 'record',
            'field', 'page', 'block', 'buffer', 'status', 'code', 'flag'
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

# ===== CHUNKER =====

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
                    chunk = FlowBasedChunk(
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
                        chunk = FlowBasedChunk(
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
            chunk = FlowBasedChunk(
                content=chunk_content,
                source_file=file_path,
                chunk_id=chunk_id,
                start_line=chunk_start_line,
                end_line=len(lines) - 1,
                procedure_name=current_proc_name
            )
            chunks.append(chunk)
        
        return chunks

# ===== PAYMENT FLOW ANALYZER =====

class PaymentFlowAnalyzer:
    """Analyzes code chunks for payment flow capabilities."""
    
    def __init__(self):
        self.flow_definitions = self._load_flow_definitions()
        self.network_patterns = self._load_network_patterns()
    
    def _load_flow_definitions(self):
        """Load payment flow capability definitions."""
        return {
            FlowType.CUSTOMER_TRANSFER: {
                'keywords': {
                    'customer', 'transfer', 'originator', 'beneficiary', 'type_code_1000',
                    'individual', 'corporate', 'credit', 'debit', 'funds'
                },
                'patterns': [
                    r'customer.*transfer.*process',
                    r'originator.*beneficiary',
                    r'type.?code.?1000',
                    r'individual.*payment',
                    r'corporate.*payment'
                ],
                'functions': [
                    r'.*customer.*transfer.*',
                    r'.*originator.*process.*',
                    r'.*beneficiary.*validate.*',
                    r'.*individual.*payment.*'
                ]
            },
            
            FlowType.VALIDATION: {
                'keywords': {
                    'validation', 'validate', 'verify', 'check', 'format', 'mandatory',
                    'optional', 'field', 'structure', 'schema', 'compliance'
                },
                'patterns': [
                    r'validation.*process',
                    r'message.*validate',
                    r'field.*validate',
                    r'format.*check',
                    r'schema.*validate'
                ],
                'functions': [
                    r'.*validate.*',
                    r'.*verify.*',
                    r'.*check.*format.*',
                    r'.*field.*valid.*'
                ]
            },
            
            # Add other flow types as needed...
        }
    
    def _load_network_patterns(self):
        """Load network-specific patterns."""
        return {
            PaymentNetwork.FEDWIRE: {
                'keywords': {
                    'fedwire', 'federal_reserve', 'fed', 'imad', 'omad', 'fedline',
                    'advantage', 'type_code', 'bfc', 'participant', 'cutoff'
                },
                'patterns': [
                    r'fedwire.*process',
                    r'federal.*reserve',
                    r'type.*code.*\d{4}',
                    r'imad.*generate',
                    r'omad.*process'
                ],
                'message_types': ['1000', '1200', '1400', '1500']
            },
            
            PaymentNetwork.SWIFT: {
                'keywords': {
                    'swift', 'mt103', 'mt202', 'mt199', 'bic', 'fin', 'gpi',
                    'uetr', 'iso20022', 'pacs', 'pain', 'camt'
                },
                'patterns': [
                    r'swift.*process',
                    r'mt\d{3}.*handle',
                    r'iso20022.*process',
                    r'pacs\d{3}.*parse'
                ],
                'message_types': ['103', '202', '199', '008', '009']
            }
        }
    
    def analyze_chunk(self, chunk: FlowBasedChunk):
        """Analyze a chunk for payment flow capabilities."""
        # Detect payment networks
        self._detect_networks(chunk)
        
        # Analyze flow capabilities
        self._analyze_flow_capabilities(chunk)
        
        # Set primary and secondary flows
        self._determine_primary_flows(chunk)
        
        # Create flow summary
        self._create_flow_summary(chunk)
    
    def _detect_networks(self, chunk: FlowBasedChunk):
        """Detect which payment networks this chunk relates to."""
        content_lower = chunk.content.lower()
        chunk_words = set(chunk.words + chunk.stemmed_words)
        
        for network, patterns in self.network_patterns.items():
            score = 0
            
            # Keyword matching
            keyword_matches = len(chunk_words & patterns['keywords'])
            score += keyword_matches * 2
            
            # Pattern matching
            for pattern in patterns['patterns']:
                if re.search(pattern, content_lower):
                    score += 3
            
            if score > 3:  # Threshold for network detection
                chunk.detected_networks.add(network)
    
    def _analyze_flow_capabilities(self, chunk: FlowBasedChunk):
        """Analyze what payment flow capabilities this chunk provides."""
        content_lower = chunk.content.lower()
        chunk_words = set(chunk.words + chunk.stemmed_words)
        
        for flow_type, definition in self.flow_definitions.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = len(chunk_words & definition['keywords'])
            score += keyword_matches * 0.3
            
            # Pattern matching
            for pattern in definition['patterns']:
                if re.search(pattern, content_lower):
                    score += 0.5
            
            chunk.flow_capabilities[flow_type] = score
    
    def _determine_primary_flows(self, chunk: FlowBasedChunk):
        """Determine primary and secondary flow capabilities."""
        sorted_flows = sorted(chunk.flow_capabilities.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_flows and sorted_flows[0][1] > 0.5:
            chunk.primary_flow = sorted_flows[0][0]
        
        chunk.secondary_flows = [
            flow for flow, score in sorted_flows[1:] 
            if score > 0.3 and score >= sorted_flows[0][1] * 0.6
        ][:3]
    
    def _create_flow_summary(self, chunk: FlowBasedChunk):
        """Create human-readable flow summary."""
        networks = [net.value for net in chunk.detected_networks]
        
        if chunk.primary_flow:
            primary_flow_name = chunk.primary_flow.value.replace('_', ' ').title()
            
            if networks:
                network_str = '/'.join(net.upper() for net in networks)
                chunk.flow_summary = f"{network_str} {primary_flow_name}"
            else:
                chunk.flow_summary = primary_flow_name
        else:
            if networks:
                chunk.flow_summary = f"{'/'.join(net.upper() for net in networks)} Processing"
            else:
                chunk.flow_summary = "General Processing"

# ===== VECTORIZER =====

class FlowBasedVectorizer:
    """Vectorizer optimized for payment flow capabilities."""
    
    def __init__(self, max_features=3000):
        self.max_features = max_features
        self.vocabulary = {}
        self.stemmed_vocabulary = {}
        self.idf_values = {}
        self.flow_analyzer = PaymentFlowAnalyzer()
        self.document_count = 0
        self.text_processor = EnhancedTextProcessor()
        
        # Flow capability dimensions
        self.flow_dimensions = list(FlowType)
        self.network_dimensions = list(PaymentNetwork)
    
    def fit_transform(self, chunks):
        """Enhanced vectorization with payment flow analysis."""
        print(f"🔍 Processing {len(chunks)} chunks with payment flow analysis...")
        
        if not chunks:
            print("No chunks to process")
            return
        
        # Process chunk words
        self._process_chunk_words(chunks)
        
        # Analyze payment flows for each chunk
        for chunk in chunks:
            self.flow_analyzer.analyze_chunk(chunk)
        
        # Build vocabulary
        self._build_vocabulary(chunks)
        
        # Create vectors
        self._create_flow_vectors(chunks)
        self._create_network_vectors(chunks)
        self._create_tfidf_vectors(chunks)
        
        print(f"✅ Payment flow processing complete:")
        print(f"   📝 {len(self.vocabulary)} vocabulary terms")
        print(f"   🔄 {len(self.flow_dimensions)} flow dimensions")
        print(f"   🌐 {len(self.network_dimensions)} network dimensions")
    
    def _process_chunk_words(self, chunks):
        """Process words for all chunks."""
        for chunk in chunks:
            filtered_words, stemmed_words = self.text_processor.process_words(chunk.raw_words)
            chunk.words = filtered_words
            chunk.stemmed_words = stemmed_words
    
    def _build_vocabulary(self, chunks):
        """Build vocabulary."""
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
        
        # Filter vocabulary
        min_df = 2
        max_df = int(0.8 * self.document_count)
        
        vocab_candidates = [
            (word, freq) for word, freq in word_doc_freq.items()
            if min_df <= freq <= max_df and len(word) >= 3
        ]
        
        stemmed_candidates = [
            (word, freq) for word, freq in stemmed_doc_freq.items()
            if min_df <= freq <= max_df and len(word) >= 3
        ]
        
        # Sort and limit
        vocab_candidates.sort(key=lambda x: x[1], reverse=True)
        stemmed_candidates.sort(key=lambda x: x[1], reverse=True)
        
        if len(vocab_candidates) > self.max_features:
            vocab_candidates = vocab_candidates[:self.max_features]
        
        if len(stemmed_candidates) > self.max_features:
            stemmed_candidates = stemmed_candidates[:self.max_features]
        
        # Create vocabulary mappings
        self.vocabulary = {word: idx for idx, (word, _) in enumerate(vocab_candidates)}
        self.stemmed_vocabulary = {word: idx for idx, (word, _) in enumerate(stemmed_candidates)}
        
        # Calculate IDF values
        for word, doc_freq in vocab_candidates:
            self.idf_values[word] = math.log(self.document_count / doc_freq)
        
        print(f"  📚 Vocabulary: {len(self.vocabulary)} words, {len(self.stemmed_vocabulary)} stems")
    
    def _create_flow_vectors(self, chunks):
        """Create flow capability vectors."""
        for chunk in chunks:
            flow_vector = []
            for flow_type in self.flow_dimensions:
                score = chunk.flow_capabilities.get(flow_type, 0.0)
                flow_vector.append(score)
            chunk.flow_vector = flow_vector
    
    def _create_network_vectors(self, chunks):
        """Create network-specific vectors."""
        for chunk in chunks:
            network_vector = []
            for network in self.network_dimensions:
                if network in chunk.detected_networks:
                    network_vector.append(1.0)
                else:
                    network_vector.append(0.0)
            chunk.network_vector = network_vector
    
    def _create_tfidf_vectors(self, chunks):
        """Create TF-IDF vectors."""
        for chunk in chunks:
            vector = [0.0] * len(self.stemmed_vocabulary)
            stemmed_counts = Counter(chunk.stemmed_words)
            total_words = len(chunk.stemmed_words)
            
            if total_words > 0:
                for stemmed_word, count in stemmed_counts.items():
                    if stemmed_word in self.stemmed_vocabulary:
                        tf = count / total_words
                        idf = 1.0  # Simplified for this example
                        tfidf = tf * idf
                        vector[self.stemmed_vocabulary[stemmed_word]] = tfidf
            
            chunk.tfidf_vector = vector

# ===== MAIN INDEXER =====

class FlowBasedCorpusIndexer:
    """Main indexer with payment flow analysis."""
    
    def __init__(self, max_features=3000):
        self.chunker = TALChunker()
        self.vectorizer = FlowBasedVectorizer(max_features)
        self.chunks = []
        self.stats = {
            'total_files': 0,
            'total_chunks': 0,
            'total_procedures': 0,
            'flow_distribution': {},
            'network_distribution': {},
        }
    
    def index_directory(self, directory_path, file_extensions=None):
        """Index directory with payment flow analysis."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h', '.cpp', '.hpp']
        
        print(f"📁 Payment flow indexing from: {directory_path}")
        
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
        for file_path in matching_files:
            print(f"  Processing: {os.path.basename(file_path)}")
            file_chunks = self.chunker.chunk_file(file_path)
            all_chunks.extend(file_chunks)
            print(f"    📦 {len(file_chunks)} chunks")
        
        self.chunks = all_chunks
        
        if not self.chunks:
            print("❌ No chunks created")
            return []
        
        print(f"\n📊 Total chunks: {len(self.chunks)}")
        
        # Payment flow vectorization
        self.vectorizer.fit_transform(self.chunks)
        
        # Update statistics
        self._update_flow_statistics(matching_files)
        
        return self.chunks
    
    def _update_flow_statistics(self, matching_files):
        """Update statistics with payment flow metrics."""
        # Count flow distributions
        flow_counts = defaultdict(int)
        network_counts = defaultdict(int)
        
        for chunk in self.chunks:
            if chunk.primary_flow:
                flow_counts[chunk.primary_flow.value] += 1
            
            for network in chunk.detected_networks:
                network_counts[network.value] += 1
        
        self.stats.update({
            'total_files': len(matching_files),
            'total_chunks': len(self.chunks),
            'total_procedures': len([c for c in self.chunks if c.procedure_name]),
            'flow_distribution': dict(flow_counts),
            'network_distribution': dict(network_counts)
        })
    
    def print_flow_statistics(self):
        """Print comprehensive payment flow statistics."""
        print(f"\n{'='*70}")
        print("📊 PAYMENT FLOW ANALYSIS STATISTICS")
        print("="*70)
        print(f"Files processed: {self.stats['total_files']}")
        print(f"Chunks created: {self.stats['total_chunks']}")
        print(f"Procedures found: {self.stats['total_procedures']}")
        
        if self.stats['network_distribution']:
            print(f"\n🌐 Payment Network Distribution:")
            for network, count in self.stats['network_distribution'].items():
                print(f"  {network.upper()}: {count} chunks")
        
        if self.stats['flow_distribution']:
            print(f"\n🔄 Payment Flow Distribution:")
            for flow, count in sorted(self.stats['flow_distribution'].items(), 
                                    key=lambda x: x[1], reverse=True):
                flow_name = flow.replace('_', ' ').title()
                print(f"  {flow_name}: {count} chunks")
    
    def print_flow_samples(self, n=3):
        """Print sample chunks with payment flow details."""
        print(f"\n{'='*70}")
        print(f"📋 PAYMENT FLOW SAMPLE CHUNKS (showing first {n})")
        print("="*70)
        
        for i, chunk in enumerate(self.chunks[:n]):
            print(f"\nChunk {i}:")
            print(f"  📁 File: {os.path.basename(chunk.source_file)}")
            print(f"  📍 Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"  🔧 Procedure: {chunk.procedure_name or 'None'}")
            print(f"  🎯 Flow Summary: {chunk.flow_summary}")
            
            if chunk.detected_networks:
                networks = [net.value.upper() for net in chunk.detected_networks]
                print(f"  🌐 Networks: {', '.join(networks)}")
            
            if chunk.primary_flow:
                primary_flow = chunk.primary_flow.value.replace('_', ' ').title()
                score = chunk.flow_capabilities[chunk.primary_flow]
                print(f"  🔄 Primary Flow: {primary_flow} (score: {score:.2f})")
            
            if chunk.message_patterns:
                print(f"  📨 Message Patterns: {', '.join(chunk.message_patterns[:3])}")
    
    def search_by_flow(self, flow_type: FlowType, threshold: float = 0.5) -> List[FlowBasedChunk]:
        """Search chunks by payment flow type."""
        matching_chunks = []
        
        for chunk in self.chunks:
            score = chunk.flow_capabilities.get(flow_type, 0)
            if score >= threshold:
                matching_chunks.append((score, chunk))
        
        matching_chunks.sort(reverse=True)
        return [chunk for _, chunk in matching_chunks[:10]]
    
    def search_by_network(self, network: PaymentNetwork) -> List[FlowBasedChunk]:
        """Search chunks by payment network."""
        return [chunk for chunk in self.chunks if network in chunk.detected_networks]
    
    def save_flow_corpus(self, output_path):
        """Save payment flow corpus with all metadata."""
        print(f"\n💾 Saving payment flow corpus...")
        
        corpus_data = {
            'version': '3.0-payment-flow-enhanced',
            'created_at': __import__('datetime').datetime.now().isoformat(),
            'chunks': [
                {
                    'content': chunk.content,
                    'source_file': chunk.source_file,
                    'chunk_id': chunk.chunk_id,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'procedure_name': chunk.procedure_name,
                    'detected_networks': [net.value for net in chunk.detected_networks],
                    'flow_capabilities': {flow.value: score for flow, score in chunk.flow_capabilities.items()},
                    'primary_flow': chunk.primary_flow.value if chunk.primary_flow else None,
                    'secondary_flows': [flow.value for flow in chunk.secondary_flows],
                    'flow_summary': chunk.flow_summary,
                    'message_patterns': chunk.message_patterns,
                    'transaction_types': chunk.transaction_types,
                    'function_calls': chunk.function_calls,
                    'flow_vector': chunk.flow_vector,
                    'network_vector': chunk.network_vector,
                    'tfidf_vector': chunk.tfidf_vector
                }
                for chunk in self.chunks
            ],
            'vectorizer': {
                'vocabulary': self.vectorizer.vocabulary,
                'stemmed_vocabulary': self.vectorizer.stemmed_vocabulary,
                'flow_dimensions': [flow.value for flow in self.vectorizer.flow_dimensions],
                'network_dimensions': [net.value for net in self.vectorizer.network_dimensions],
                'max_features': self.vectorizer.max_features,
                'document_count': self.vectorizer.document_count
            },
            'statistics': self.stats
        }
        
        # Save main corpus file
        with open(output_path, 'wb') as f:
            pickle.dump(corpus_data, f)
        
        print(f"✅ Payment flow corpus saved to: {output_path}")

# ===== SEARCHER =====

class PaymentFlowSearcher:
    """Advanced searcher for payment flow-indexed corpus."""
    
    def __init__(self, corpus_path: str):
        self.load_corpus(corpus_path)
    
    def load_corpus(self, corpus_path: str):
        """Load payment flow corpus."""
        with open(corpus_path, 'rb') as f:
            self.corpus_data = pickle.load(f)
        
        self.chunks = []
        for chunk_data in self.corpus_data['chunks']:
            # Reconstruct chunk objects with flow data
            chunk = FlowBasedChunk(
                content=chunk_data['content'],
                source_file=chunk_data['source_file'],
                chunk_id=chunk_data['chunk_id'],
                start_line=chunk_data['start_line'],
                end_line=chunk_data['end_line'],
                procedure_name=chunk_data['procedure_name']
            )
            
            # Restore flow analysis results
            chunk.detected_networks = {PaymentNetwork(net) for net in chunk_data['detected_networks']}
            chunk.flow_capabilities = {FlowType(flow): score for flow, score in chunk_data['flow_capabilities'].items()}
            chunk.primary_flow = FlowType(chunk_data['primary_flow']) if chunk_data['primary_flow'] else None
            chunk.secondary_flows = [FlowType(flow) for flow in chunk_data['secondary_flows']]
            chunk.flow_summary = chunk_data['flow_summary']
            chunk.message_patterns = chunk_data['message_patterns']
            chunk.transaction_types = chunk_data['transaction_types']
            chunk.function_calls = chunk_data['function_calls']
            chunk.flow_vector = chunk_data['flow_vector']
            chunk.network_vector = chunk_data['network_vector']
            chunk.tfidf_vector = chunk_data['tfidf_vector']
            
            self.chunks.append(chunk)
        
        print(f"📖 Loaded payment flow corpus with {len(self.chunks)} chunks")
    
    def find_validation_patterns(self, validation_type: str = "field", 
                                message_type: str = None,
                                top_k: int = 10) -> List[FlowBasedChunk]:
        """Find validation patterns for ISO messages."""
        candidates = []
        
        for chunk in self.chunks:
            # Check if this chunk handles validation
            validation_score = chunk.flow_capabilities.get(FlowType.VALIDATION, 0)
            if validation_score < 0.3:
                continue
            
            # Check for specific validation type
            content_lower = chunk.content.lower()
            if validation_type and validation_type.lower() not in content_lower:
                continue
            
            # Check for specific message type
            if message_type and message_type.lower() not in content_lower:
                continue
            
            candidates.append((validation_score, chunk))
        
        candidates.sort(reverse=True)
        return [chunk for _, chunk in candidates[:top_k]]
    
    def find_iso_message_processing(self, message_type: ISOMessageType,
                                  top_k: int = 10) -> List[FlowBasedChunk]:
        """Find chunks that process specific ISO message types."""
        candidates = []
        message_pattern = message_type.value.lower().replace('.', '')
        
        for chunk in self.chunks:
            score = 0
            content_lower = chunk.content.lower()
            
            # Check for message type in content
            if message_pattern in content_lower:
                score += 3
            
            # Check for message type in message patterns
            if any(message_pattern in pattern for pattern in chunk.message_patterns):
                score += 4
            
            # Check for message type in function calls
            if any(message_pattern in func.lower() for func in chunk.function_calls):
                score += 2
            
            if score > 0:
                candidates.append((score, chunk))
        
        candidates.sort(reverse=True)
        return [chunk for _, chunk in candidates[:top_k]]

# ===== MAIN FUNCTION =====

def main():
    """Main indexer function for payment flow processing."""
    print("="*70)
    print("🏦 PAYMENT FLOW TAL CORPUS INDEXER")
    print("="*70)
    print("Payment flow semantic indexing with comprehensive capabilities:")
    print("• Fedwire flows: Customer transfers, bank-to-bank, drawdowns, settlement")
    print("• SWIFT flows: MT103, MT202, cover payments, gpi tracking, investigations")
    print("• CHIPS flows: Prefunded payments, netting, real-time settlement")
    print("• Cross-network: Exception handling, compliance screening, reporting")
    print("• Flow-based vectorization for targeted code discovery")
    
    if not NLTK_AVAILABLE:
        print("\n⚠️  NLTK not found - install with: pip install nltk")
        print("   (Will use basic processing without stemming)")
    
    # Get directory
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("\n📁 Enter payment processing codebase directory: ").strip()
    
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
    
    # Get processing parameters
    try:
        max_features = int(input("🔧 Max vocabulary features (default 3000): ") or "3000")
    except ValueError:
        print("Invalid input, using defaults")
        max_features = 3000
    
    print(f"\n🚀 Starting payment flow indexing...")
    print(f"   📝 Max features: {max_features}")
    print(f"   🌿 NLP processing: {'Enhanced with NLTK' if NLTK_AVAILABLE else 'Basic'}")
    print(f"   🔄 Flow types: {len(FlowType)} payment flows")
    print(f"   🌐 Networks: {len(PaymentNetwork)} payment networks")
    
    # Create indexer and process
    indexer = FlowBasedCorpusIndexer(max_features)
    
    try:
        chunks = indexer.index_directory(directory, file_extensions)
        
        if not chunks:
            print("❌ No chunks created - check directory and file extensions")
            return False
        
        # Show results
        indexer.print_flow_statistics()
        indexer.print_flow_samples()
        
        # Demo searches
        print(f"\n{'='*70}")
        print("🔍 PAYMENT FLOW SEARCH EXAMPLES")
        print("="*70)
        
        # Search by flow type
        validation_chunks = indexer.search_by_flow(FlowType.VALIDATION, threshold=0.3)
        if validation_chunks:
            print(f"\n🔄 Validation Flow ({len(validation_chunks)} chunks found):")
            for chunk in validation_chunks[:3]:
                print(f"  📄 {os.path.basename(chunk.source_file)} - {chunk.procedure_name or 'No procedure'}")
                print(f"     Score: {chunk.flow_capabilities[FlowType.VALIDATION]:.2f}")
        
        # Search by network
        swift_chunks = indexer.search_by_network(PaymentNetwork.SWIFT)
        if swift_chunks:
            print(f"\n🌐 SWIFT Network ({len(swift_chunks)} chunks found):")
            for chunk in swift_chunks[:3]:
                print(f"  📄 {os.path.basename(chunk.source_file)} - {chunk.procedure_name or 'No procedure'}")
                if chunk.swift_message_types:
                    print(f"     Message types: {', '.join(chunk.swift_message_types)}")
        
        # Save corpus
        dir_name = os.path.basename(os.path.abspath(directory))
        output_file = f"payment_flow_tal_corpus_{dir_name}.pkl"
        
        save_choice = input(f"\n💾 Save payment flow corpus to {output_file}? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '']:
            indexer.save_flow_corpus(output_file)
            
            print(f"\n✅ Payment flow indexing completed successfully!")
            print(f"📁 Flow-based index: {output_file}")
            print(f"🔍 Use PaymentFlowSearcher for targeted code discovery")
            print(f"🔄 {len(FlowType)} payment flows ready for semantic search")
            print(f"🌐 {len(PaymentNetwork)} payment networks indexed")
        else:
            print(f"\n✅ Payment flow indexing completed (not saved)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during payment flow indexing: {e}")
        import traceback
        traceback.print_exc()
        return False

# ===== USAGE EXAMPLES =====

def demo_usage():
    """Demonstrate usage of the payment flow indexer."""
    print("="*70)
    print("🔍 PAYMENT FLOW SEARCH EXAMPLES")
    print("="*70)
    
    print("Example searches you can perform:")
    
    print("\n1. Find validation code for PACS.008 messages:")
    print("   searcher = PaymentFlowSearcher('payment_flow_corpus.pkl')")
    print("   pacs008_validation = searcher.find_iso_message_processing(ISOMessageType.PACS008)")
    
    print("\n2. Find field validation patterns:")
    print("   field_validation = searcher.find_validation_patterns(validation_type='field')")
    
    print("\n3. Find SWIFT message validation:")
    print("   swift_validation = searcher.find_validation_patterns(message_type='swift')")
    
    print("\n4. Search by flow type:")
    print("   validation_code = indexer.search_by_flow(FlowType.VALIDATION)")
    
    print("\n5. Search by network:")
    print("   fedwire_code = indexer.search_by_network(PaymentNetwork.FEDWIRE)")

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ Payment flow indexing failed!")
        else:
            print(f"\n" + "="*70)
            demo_usage()
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
