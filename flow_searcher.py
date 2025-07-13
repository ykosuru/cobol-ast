#!/usr/bin/env python3
"""
Payment Flow Corpus Searcher

Standalone searcher for payment flow-indexed TAL corpus files.
Provides comprehensive search capabilities for Federal Reserve, SWIFT, and CHIPS
wire processing code discovery.
"""

import os
import re
import json
import pickle
import math
import sys
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional
from enum import Enum

# ===== ENUM DEFINITIONS (must match indexer) =====

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
    PACS008 = "pacs.008.001"  # FIToFICstmrCdtTrf
    PACS009 = "pacs.009.001"  # FIToFICstmrCdtTrf (Return)
    PACS002 = "pacs.002.001"  # FIToFIPmtStsRpt
    PACS004 = "pacs.004.001"  # PmtRtr
    PACS007 = "pacs.007.001"  # FIToFIPmtRvsl
    PAIN001 = "pain.001.001"  # CstmrCdtTrfInitn
    PAIN002 = "pain.002.001"  # CstmrPmtStsRpt
    CAMT052 = "camt.052.001"  # BkToCstmrAcctRpt
    CAMT053 = "camt.053.001"  # BkToCstmrStmt
    CAMT054 = "camt.054.001"  # BkToCstmrDbtCdtNtfctn
    CAMT056 = "camt.056.001"  # FIToFICstmrCdtTrfCxlReq
    CAMT029 = "camt.029.001"  # ResolutionOfInvestigation

# ===== CHUNK CLASS FOR LOADING =====

class SearchableChunk:
    """Chunk class for search operations (loaded from saved corpus)."""
    
    def __init__(self, chunk_data):
        # Basic properties
        self.content = chunk_data['content']
        self.source_file = chunk_data['source_file']
        self.chunk_id = chunk_data['chunk_id']
        self.start_line = chunk_data['start_line']
        self.end_line = chunk_data['end_line']
        self.procedure_name = chunk_data['procedure_name']
        
        # Flow analysis results
        self.detected_networks = {PaymentNetwork(net) for net in chunk_data['detected_networks']}
        self.flow_capabilities = {FlowType(flow): score for flow, score in chunk_data['flow_capabilities'].items()}
        self.primary_flow = FlowType(chunk_data['primary_flow']) if chunk_data['primary_flow'] else None
        self.secondary_flows = [FlowType(flow) for flow in chunk_data['secondary_flows']]
        self.flow_summary = chunk_data['flow_summary']
        
        # Pattern data
        self.message_patterns = chunk_data['message_patterns']
        self.transaction_types = chunk_data['transaction_types']
        self.function_calls = chunk_data['function_calls']
        
        # Vector data
        self.flow_vector = chunk_data['flow_vector']
        self.network_vector = chunk_data['network_vector']
        self.tfidf_vector = chunk_data['tfidf_vector']
    
    def __hash__(self):
        """Make chunk hashable for use in sets."""
        return hash((self.source_file, self.chunk_id, self.start_line, self.end_line))
    
    def __eq__(self, other):
        """Define equality for chunks."""
        if not isinstance(other, SearchableChunk):
            return False
        return (self.source_file == other.source_file and 
                self.chunk_id == other.chunk_id and
                self.start_line == other.start_line and
                self.end_line == other.end_line)
    
    def __repr__(self):
        """String representation for debugging."""
        return f"SearchableChunk(file={os.path.basename(self.source_file)}, id={self.chunk_id}, proc={self.procedure_name})"
    
    def __lt__(self, other):
        """Less than comparison for sorting."""
        if not isinstance(other, SearchableChunk):
            return NotImplemented
        return (self.source_file, self.chunk_id) < (other.source_file, other.chunk_id)
    
    def __le__(self, other):
        """Less than or equal comparison for sorting."""
        if not isinstance(other, SearchableChunk):
            return NotImplemented
        return (self.source_file, self.chunk_id) <= (other.source_file, other.chunk_id)
    
    def __gt__(self, other):
        """Greater than comparison for sorting."""
        if not isinstance(other, SearchableChunk):
            return NotImplemented
        return (self.source_file, self.chunk_id) > (other.source_file, other.chunk_id)
    
    def __ge__(self, other):
        """Greater than or equal comparison for sorting."""
        if not isinstance(other, SearchableChunk):
            return NotImplemented
        return (self.source_file, self.chunk_id) >= (other.source_file, other.chunk_id)

# ===== MAIN SEARCHER CLASS =====

class PaymentFlowSearcher:
    """Advanced searcher for payment flow-indexed corpus."""
    
    def __init__(self, corpus_path: str):
        self.chunks = []
        self.vocabulary = {}
        self.corpus_stats = {}
        self.search_indexes = {}
        
        self.load_corpus(corpus_path)
        self.build_search_indexes()
        
        print(f"✅ Payment Flow Searcher initialized")
        print(f"   📦 {len(self.chunks)} chunks loaded")
        print(f"   🔄 {len([c for c in self.chunks if c.primary_flow])} chunks with primary flows")
        print(f"   🌐 {len([c for c in self.chunks if c.detected_networks])} chunks with detected networks")
    
    def load_corpus(self, corpus_path: str):
        """Load payment flow corpus from saved file."""
        if not os.path.exists(corpus_path):
            raise FileNotFoundError(f"Corpus file not found: {corpus_path}")
        
        print(f"📖 Loading corpus from: {corpus_path}")
        
        with open(corpus_path, 'rb') as f:
            corpus_data = pickle.load(f)
        
        # Validate corpus version - updated to match indexer version format
        if 'version' not in corpus_data or not corpus_data['version'].startswith('1.0-payment-flow'):
            print("⚠️  Warning: Corpus may not be compatible with this searcher version")
        
        # Load chunks
        for chunk_data in corpus_data['chunks']:
            chunk = SearchableChunk(chunk_data)
            self.chunks.append(chunk)
        
        # Load vocabulary and statistics - updated to match indexer format
        self.vocabulary = corpus_data.get('vocabulary', {})
        self.corpus_stats = corpus_data.get('statistics', {})
        
        print(f"📊 Corpus statistics:")
        print(f"   Files: {self.corpus_stats.get('total_files', 'unknown')}")
        print(f"   Chunks with procedures: {self.corpus_stats.get('chunks_with_procedures', 'unknown')}")
        print(f"   Vocabulary size: {self.corpus_stats.get('vocabulary_size', 'unknown')}")
    
    def build_search_indexes(self):
        """Build search indexes for efficient querying."""
        print("🔍 Building search indexes...")
        
        # Index by flow type
        self.search_indexes['by_flow'] = defaultdict(list)
        for chunk in self.chunks:
            if chunk.primary_flow:
                self.search_indexes['by_flow'][chunk.primary_flow].append(chunk)
            for secondary_flow in chunk.secondary_flows:
                self.search_indexes['by_flow'][secondary_flow].append(chunk)
        
        # Index by network
        self.search_indexes['by_network'] = defaultdict(list)
        for chunk in self.chunks:
            for network in chunk.detected_networks:
                self.search_indexes['by_network'][network].append(chunk)
        
        # Index by message pattern
        self.search_indexes['by_message'] = defaultdict(list)
        for chunk in self.chunks:
            for pattern in chunk.message_patterns:
                self.search_indexes['by_message'][pattern].append(chunk)
        
        # Index by procedure name
        self.search_indexes['by_procedure'] = defaultdict(list)
        for chunk in self.chunks:
            if chunk.procedure_name:
                # Index by full name and prefix
                self.search_indexes['by_procedure'][chunk.procedure_name.lower()].append(chunk)
                # Index by prefix (first part before underscore)
                if '_' in chunk.procedure_name:
                    prefix = chunk.procedure_name.split('_')[0].lower()
                    self.search_indexes['by_procedure'][prefix].append(chunk)
        
        # Index by function calls
        self.search_indexes['by_function'] = defaultdict(list)
        for chunk in self.chunks:
            for func_call in chunk.function_calls:
                self.search_indexes['by_function'][func_call.lower()].append(chunk)
        
        print(f"   🔄 Flow index: {len(self.search_indexes['by_flow'])} flow types")
        print(f"   🌐 Network index: {len(self.search_indexes['by_network'])} networks")
        print(f"   📨 Message index: {len(self.search_indexes['by_message'])} message patterns")
        print(f"   🔧 Procedure index: {len(self.search_indexes['by_procedure'])} procedure names")
        print(f"   📞 Function index: {len(self.search_indexes['by_function'])} function calls")
    
    # ===== CORE SEARCH METHODS =====
    
    def search_by_flow(self, flow_type: FlowType, 
                      network: PaymentNetwork = None,
                      min_score: float = 0.0,
                      top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Search for chunks by payment flow type."""
        candidates = self.search_indexes['by_flow'].get(flow_type, [])
        
        # Filter by network if specified
        if network:
            candidates = [chunk for chunk in candidates if network in chunk.detected_networks]
        
        # Score and filter
        scored_results = []
        for chunk in candidates:
            score = chunk.flow_capabilities.get(flow_type, 0.0)
            if score >= min_score:
                scored_results.append((score, chunk))
        
        # Sort by score
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def search_by_network(self, network: PaymentNetwork,
                         flow_type: FlowType = None,
                         top_k: int = 15) -> List[SearchableChunk]:
        """Search for chunks by payment network."""
        candidates = self.search_indexes['by_network'].get(network, [])
        
        # Filter by flow type if specified
        if flow_type:
            candidates = [chunk for chunk in candidates 
                         if chunk.primary_flow == flow_type or flow_type in chunk.secondary_flows]
        
        return candidates[:top_k]
    
    def search_by_message_type(self, message_pattern: str,
                              network: PaymentNetwork = None,
                              top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Search for chunks that process specific message types."""
        candidates = []
        
        # Direct message pattern search
        for pattern, chunks in self.search_indexes['by_message'].items():
            if message_pattern.lower() in pattern.lower():
                candidates.extend(chunks)
        
        # Content-based search for message patterns not in index
        for chunk in self.chunks:
            if message_pattern.lower() in chunk.content.lower():
                candidates.append(chunk)
        
        # Remove duplicates manually to avoid sorting issues
        seen_chunks = set()
        candidates_unique = []
        for chunk in candidates:
            chunk_key = (chunk.source_file, chunk.chunk_id, chunk.start_line)
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                candidates_unique.append(chunk)
        
        candidates = candidates_unique
        
        # Filter by network if specified
        if network:
            candidates = [chunk for chunk in candidates if network in chunk.detected_networks]
        
        # Score by relevance
        scored_results = []
        for chunk in candidates:
            score = self._calculate_message_relevance_score(message_pattern, chunk)
            scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def search_by_procedure(self, procedure_pattern: str,
                           flow_type: FlowType = None,
                           top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Search for procedures by name pattern."""
        candidates = []
        pattern_lower = procedure_pattern.lower()
        
        # Search by exact match and partial match
        for proc_name, chunks in self.search_indexes['by_procedure'].items():
            if pattern_lower in proc_name or proc_name in pattern_lower:
                candidates.extend(chunks)
        
        # Remove duplicates manually
        seen_chunks = set()
        candidates_unique = []
        for chunk in candidates:
            chunk_key = (chunk.source_file, chunk.chunk_id, chunk.start_line)
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                candidates_unique.append(chunk)
        
        candidates = candidates_unique
        
        # Filter by flow type if specified
        if flow_type:
            candidates = [chunk for chunk in candidates 
                         if chunk.primary_flow == flow_type or flow_type in chunk.secondary_flows]
        
        # Score by name similarity
        scored_results = []
        for chunk in candidates:
            score = self._calculate_procedure_similarity_score(procedure_pattern, chunk.procedure_name)
            scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def search_by_function(self, function_pattern: str,
                          flow_type: FlowType = None,
                          top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Search for chunks that call specific functions."""
        candidates = []
        pattern_lower = function_pattern.lower()
        
        # Search function call index
        for func_name, chunks in self.search_indexes['by_function'].items():
            if pattern_lower in func_name or func_name in pattern_lower:
                candidates.extend(chunks)
        
        # Remove duplicates manually
        seen_chunks = set()
        candidates_unique = []
        for chunk in candidates:
            chunk_key = (chunk.source_file, chunk.chunk_id, chunk.start_line)
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                candidates_unique.append(chunk)
        
        candidates = candidates_unique
        
        # Filter by flow type if specified
        if flow_type:
            candidates = [chunk for chunk in candidates 
                         if chunk.primary_flow == flow_type or flow_type in chunk.secondary_flows]
        
        # Score by function call relevance
        scored_results = []
        for chunk in candidates:
            score = self._calculate_function_relevance_score(function_pattern, chunk)
            scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def search_by_keywords(self, keywords: List[str],
                          flow_type: FlowType = None,
                          network: PaymentNetwork = None,
                          top_k: int = 15) -> List[Tuple[float, SearchableChunk]]:
        """Search for chunks by keywords in content."""
        scored_results = []
        
        for chunk in self.chunks:
            # Filter by flow type if specified
            if flow_type and chunk.primary_flow != flow_type and flow_type not in chunk.secondary_flows:
                continue
            
            # Filter by network if specified
            if network and network not in chunk.detected_networks:
                continue
            
            # Calculate keyword match score
            score = self._calculate_keyword_score(keywords, chunk)
            if score > 0:
                scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    # ===== SPECIALIZED SEARCH METHODS =====
    
    def find_validation_patterns(self, validation_type: str = None,
                                message_type: str = None,
                                field_name: str = None,
                                top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Find validation patterns for ISO messages and fields."""
        # Start with validation flow chunks
        validation_chunks = self.search_indexes['by_flow'].get(FlowType.VALIDATION, [])
        
        candidates = []
        
        # Search validation chunks
        for chunk in validation_chunks:
            content_lower = chunk.content.lower()
            
            # Filter by validation type
            if validation_type and validation_type.lower() not in content_lower:
                continue
            
            # Filter by message type
            if message_type and message_type.lower() not in content_lower:
                continue
            
            # Filter by field name
            if field_name and field_name.lower() not in content_lower:
                continue
            
            candidates.append(chunk)
        
        # Also search content for validation keywords
        validation_keywords = ['validate', 'validation', 'verify', 'check', 'format', 'mandatory', 'optional']
        for chunk in self.chunks:
            if chunk in candidates:
                continue
            
            content_lower = chunk.content.lower()
            if any(keyword in content_lower for keyword in validation_keywords):
                # Apply same filters
                if validation_type and validation_type.lower() not in content_lower:
                    continue
                if message_type and message_type.lower() not in content_lower:
                    continue
                if field_name and field_name.lower() not in content_lower:
                    continue
                
                candidates.append(chunk)
        
        # Score validation candidates
        scored_results = []
        for chunk in candidates:
            score = self._calculate_validation_score(chunk, validation_type, message_type, field_name)
            scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def find_iso_message_processing(self, message_type: ISOMessageType,
                                   processing_stage: str = None,
                                   top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Find chunks that process specific ISO 20022 message types."""
        message_pattern = message_type.value.lower().replace('.', '')
        
        # Search by message pattern
        message_results = self.search_by_message_type(message_pattern, top_k=top_k*2)
        
        candidates = []
        
        # Filter and score results
        for score, chunk in message_results:
            content_lower = chunk.content.lower()
            
            # Additional scoring for ISO message processing
            iso_score = score
            
            # Boost for message type in function names
            if any(message_pattern in func.lower() for func in chunk.function_calls):
                iso_score += 2.0
            
            # Boost for message type in procedure name
            if chunk.procedure_name and message_pattern in chunk.procedure_name.lower():
                iso_score += 3.0
            
            # Filter by processing stage if specified
            if processing_stage:
                if processing_stage.lower() not in content_lower:
                    continue
                # Boost for processing stage
                iso_score += 1.0
            
            candidates.append((iso_score, chunk))
        
        candidates.sort(reverse=True)
        return candidates[:top_k]
    
    def find_error_handling_patterns(self, error_type: str = None,
                                   network: PaymentNetwork = None,
                                   top_k: int = 10) -> List[Tuple[float, SearchableChunk]]:
        """Find error handling and exception processing patterns."""
        # Start with exception handling flow chunks
        exception_chunks = self.search_indexes['by_flow'].get(FlowType.EXCEPTION_HANDLING, [])
        
        candidates = []
        
        # Search exception handling chunks
        for chunk in exception_chunks:
            if network and network not in chunk.detected_networks:
                continue
            
            content_lower = chunk.content.lower()
            if error_type and error_type.lower() not in content_lower:
                continue
            
            candidates.append(chunk)
        
        # Search all chunks for error handling keywords
        error_keywords = ['error', 'exception', 'fault', 'fail', 'reject', 'return', 'repair']
        for chunk in self.chunks:
            if chunk in candidates:
                continue
            
            content_lower = chunk.content.lower()
            if any(keyword in content_lower for keyword in error_keywords):
                if network and network not in chunk.detected_networks:
                    continue
                if error_type and error_type.lower() not in content_lower:
                    continue
                
                candidates.append(chunk)
        
        # Score error handling candidates
        scored_results = []
        for chunk in candidates:
            score = self._calculate_error_handling_score(chunk, error_type)
            scored_results.append((score, chunk))
        
        scored_results.sort(reverse=True)
        return scored_results[:top_k]
    
    def find_similar_procedures(self, reference_procedure: str,
                              flow_type: FlowType = None,
                              top_k: int = 5) -> List[Tuple[float, SearchableChunk]]:
        """Find procedures similar to a reference procedure."""
        candidates = []
        
        # Find the reference chunk first
        reference_chunks = [chunk for chunk in self.chunks 
                          if chunk.procedure_name and reference_procedure.lower() in chunk.procedure_name.lower()]
        
        if not reference_chunks:
            return []
        
        reference_chunk = reference_chunks[0]  # Use first match as reference
        
        # Find similar chunks by comparing flow vectors
        for chunk in self.chunks:
            if chunk == reference_chunk or not chunk.procedure_name:
                continue
            
            # Filter by flow type if specified
            if flow_type and chunk.primary_flow != flow_type and flow_type not in chunk.secondary_flows:
                continue
            
            # Calculate similarity
            similarity = self._calculate_vector_similarity(reference_chunk.flow_vector, chunk.flow_vector)
            
            if similarity > 0.1:  # Minimum similarity threshold
                candidates.append((similarity, chunk))
        
        candidates.sort(reverse=True)
        return candidates[:top_k]
    
    # ===== ANALYSIS METHODS =====
    
    def analyze_flow_coverage(self) -> Dict[str, Any]:
        """Analyze coverage of payment flows in the corpus."""
        analysis = {
            'total_chunks': len(self.chunks),
            'chunks_with_flows': len([c for c in self.chunks if c.primary_flow]),
            'flow_distribution': {},
            'network_distribution': {},
            'flow_network_matrix': {},
            'coverage_gaps': []
        }
        
        # Flow distribution
        flow_counts = defaultdict(int)
        for chunk in self.chunks:
            if chunk.primary_flow:
                flow_counts[chunk.primary_flow.value] += 1
        analysis['flow_distribution'] = dict(flow_counts)
        
        # Network distribution
        network_counts = defaultdict(int)
        for chunk in self.chunks:
            for network in chunk.detected_networks:
                network_counts[network.value] += 1
        analysis['network_distribution'] = dict(network_counts)
        
        # Flow-Network matrix
        for flow in FlowType:
            analysis['flow_network_matrix'][flow.value] = {}
            for network in PaymentNetwork:
                count = len([c for c in self.chunks 
                           if c.primary_flow == flow and network in c.detected_networks])
                analysis['flow_network_matrix'][flow.value][network.value] = count
        
        # Identify coverage gaps
        for flow in FlowType:
            if flow_counts.get(flow.value, 0) == 0:
                analysis['coverage_gaps'].append(f"No implementation found for {flow.value}")
        
        return analysis
    
    def get_corpus_statistics(self) -> Dict[str, Any]:
        """Get comprehensive corpus statistics."""
        stats = {
            'basic_stats': {
                'total_chunks': len(self.chunks),
                'chunks_with_procedures': len([c for c in self.chunks if c.procedure_name]),
                'chunks_with_flows': len([c for c in self.chunks if c.primary_flow]),
                'chunks_with_networks': len([c for c in self.chunks if c.detected_networks])
            },
            'flow_stats': {},
            'network_stats': {},
            'message_stats': {},
            'top_procedures': [],
            'top_functions': []
        }
        
        # Flow statistics
        for flow in FlowType:
            chunks_with_flow = [c for c in self.chunks if c.primary_flow == flow or flow in c.secondary_flows]
            stats['flow_stats'][flow.value] = {
                'total_chunks': len(chunks_with_flow),
                'avg_score': sum(c.flow_capabilities.get(flow, 0) for c in chunks_with_flow) / len(chunks_with_flow) if chunks_with_flow else 0
            }
        
        # Network statistics
        for network in PaymentNetwork:
            chunks_with_network = [c for c in self.chunks if network in c.detected_networks]
            stats['network_stats'][network.value] = len(chunks_with_network)
        
        # Message pattern statistics
        message_counts = defaultdict(int)
        for chunk in self.chunks:
            for pattern in chunk.message_patterns:
                message_counts[pattern] += 1
        stats['message_stats'] = dict(message_counts)
        
        # Top procedures by flow coverage
        procedure_flow_counts = defaultdict(int)
        for chunk in self.chunks:
            if chunk.procedure_name:
                flow_count = len([f for f, score in chunk.flow_capabilities.items() if score > 0.3])
                procedure_flow_counts[chunk.procedure_name] = flow_count
        
        top_procedures = sorted(procedure_flow_counts.items(), key=lambda x: x[1], reverse=True)
        stats['top_procedures'] = top_procedures[:10]
        
        # Top functions by usage
        function_counts = defaultdict(int)
        for chunk in self.chunks:
            for func in chunk.function_calls:
                function_counts[func] += 1
        
        top_functions = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)
        stats['top_functions'] = top_functions[:15]
        
        return stats
    
    # ===== SCORING METHODS =====
    
    def _calculate_message_relevance_score(self, message_pattern: str, chunk: SearchableChunk) -> float:
        """Calculate relevance score for message type searches."""
        score = 0.0
        content_lower = chunk.content.lower()
        message_lower = message_pattern.lower()
        
        # Direct content matches
        if message_lower in content_lower:
            score += 2.0
        
        # Message pattern matches
        for pattern in chunk.message_patterns:
            if message_lower in pattern.lower():
                score += 3.0
        
        # Function call matches
        for func in chunk.function_calls:
            if message_lower in func.lower():
                score += 2.5
        
        # Procedure name matches
        if chunk.procedure_name and message_lower in chunk.procedure_name.lower():
            score += 4.0
        
        return score
    
    def _calculate_procedure_similarity_score(self, pattern: str, procedure_name: str) -> float:
        """Calculate similarity score for procedure names."""
        if not procedure_name:
            return 0.0
        
        pattern_lower = pattern.lower()
        proc_lower = procedure_name.lower()
        
        # Exact match
        if pattern_lower == proc_lower:
            return 10.0
        
        # Substring match
        if pattern_lower in proc_lower:
            return 8.0
        
        # Reverse substring match
        if proc_lower in pattern_lower:
            return 6.0
        
        # Word overlap
        pattern_words = set(pattern_lower.split('_'))
        proc_words = set(proc_lower.split('_'))
        
        if pattern_words and proc_words:
            overlap = len(pattern_words & proc_words)
            total = len(pattern_words | proc_words)
            return (overlap / total) * 5.0
        
        return 0.0
    
    def _calculate_function_relevance_score(self, function_pattern: str, chunk: SearchableChunk) -> float:
        """Calculate relevance score for function searches."""
        score = 0.0
        pattern_lower = function_pattern.lower()
        
        for func in chunk.function_calls:
            func_lower = func.lower()
            if pattern_lower == func_lower:
                score += 5.0
            elif pattern_lower in func_lower:
                score += 3.0
            elif func_lower in pattern_lower:
                score += 2.0
        
        return score
    
    def _calculate_keyword_score(self, keywords: List[str], chunk: SearchableChunk) -> float:
        """Calculate keyword match score."""
        score = 0.0
        content_lower = chunk.content.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Count occurrences in content
            occurrences = content_lower.count(keyword_lower)
            score += occurrences * 0.5
            
            # Boost for function names
            if any(keyword_lower in func.lower() for func in chunk.function_calls):
                score += 1.0
            
            # Boost for procedure name
            if chunk.procedure_name and keyword_lower in chunk.procedure_name.lower():
                score += 2.0
        
        return score
    
    def _calculate_validation_score(self, chunk: SearchableChunk, 
                                  validation_type: str = None,
                                  message_type: str = None,
                                  field_name: str = None) -> float:
        """Calculate validation relevance score."""
        score = 0.0
        content_lower = chunk.content.lower()
        
        # Base validation score
        validation_keywords = ['validate', 'validation', 'verify', 'check', 'format']
        for keyword in validation_keywords:
            if keyword in content_lower:
                score += 1.0
        
        # Boost for validation flow
        if chunk.primary_flow == FlowType.VALIDATION:
            score += 3.0
        elif FlowType.VALIDATION in chunk.secondary_flows:
            score += 1.5
        
        # Boost for specific validation type
        if validation_type and validation_type.lower() in content_lower:
            score += 2.0
        
        # Boost for message type
        if message_type and message_type.lower() in content_lower:
            score += 2.0
        
        # Boost for field name
        if field_name and field_name.lower() in content_lower:
            score += 2.0
        
        return score
    
    def _calculate_error_handling_score(self, chunk: SearchableChunk, error_type: str = None) -> float:
        """Calculate error handling relevance score."""
        score = 0.0
        content_lower = chunk.content.lower()
        
        # Base error handling score
        error_keywords = ['error', 'exception', 'fault', 'fail', 'reject', 'return', 'repair']
        for keyword in error_keywords:
            if keyword in content_lower:
                score += 1.0
        
        # Boost for exception handling flow
        if chunk.primary_flow == FlowType.EXCEPTION_HANDLING:
            score += 3.0
        elif FlowType.EXCEPTION_HANDLING in chunk.secondary_flows:
            score += 1.5
        
        # Boost for specific error type
        if error_type and error_type.lower() in content_lower:
            score += 2.0
        
        return score
    
    def _calculate_vector_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vector1 or not vector2 or len(vector1) != len(vector2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(a * a for a in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    # ===== UTILITY METHODS =====
    
    def print_search_results(self, results: List[Tuple[float, SearchableChunk]], 
                            title: str = "Search Results",
                            show_content: bool = False):
        """Print search results in a formatted way."""
        print(f"\n{'='*70}")
        print(f"🔍 {title.upper()}")
        print(f"{'='*70}")
        
        if not results:
            print("No results found.")
            return
        
        print(f"Found {len(results)} results:")
        
        for i, (score, chunk) in enumerate(results, 1):
            print(f"\n{i}. 📄 {os.path.basename(chunk.source_file)}")
            print(f"   🔧 Procedure: {chunk.procedure_name or 'None'}")
            print(f"   📍 Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"   🎯 Flow: {chunk.flow_summary}")
            print(f"   📊 Score: {score:.2f}")
            
            if chunk.detected_networks:
                networks = [net.value.upper() for net in chunk.detected_networks]
                print(f"   🌐 Networks: {', '.join(networks)}")
            
            if chunk.message_patterns:
                print(f"   📨 Messages: {', '.join(chunk.message_patterns[:3])}")
            
            if show_content:
                print(f"   📄 Content preview:")
                lines = chunk.content.split('\n')[:3]
                for line in lines:
                    clean_line = line.strip()
                    if clean_line:
                        print(f"      {clean_line[:60]}{'...' if len(clean_line) > 60 else ''}")
    
    def save_search_results(self, results: List[Tuple[float, SearchableChunk]], 
                           output_file: str = "search_results.json"):
        """Save search results to a JSON file."""
        result_data = []
        
        for score, chunk in results:
            result_data.append({
                'score': score,
                'source_file': chunk.source_file,
                'procedure_name': chunk.procedure_name,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'flow_summary': chunk.flow_summary,
                'detected_networks': [net.value for net in chunk.detected_networks],
                'message_patterns': chunk.message_patterns,
                'function_calls': chunk.function_calls[:5]  # First 5 function calls
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"💾 Search results saved to: {output_file}")

# ===== COMMAND LINE INTERFACE =====

def main():
    """Interactive command line interface for the searcher."""
    print("="*70)
    print("🔍 PAYMENT FLOW CORPUS SEARCHER")
    print("="*70)
    print("Interactive search for Federal Reserve, SWIFT, and CHIPS payment processing code")
    
    # Get corpus file
    if len(sys.argv) > 1:
        corpus_file = sys.argv[1]
    else:
        corpus_file = input("\n📁 Enter corpus file path (.pkl): ").strip()
    
    if not corpus_file or not os.path.exists(corpus_file):
        print(f"❌ Corpus file not found: {corpus_file}")
        return
    
    try:
        # Initialize searcher
        searcher = PaymentFlowSearcher(corpus_file)
        
        # Interactive search loop
        while True:
            print(f"\n{'='*50}")
            print("🔍 SEARCH OPTIONS:")
            print("1. Search by payment flow")
            print("2. Search by payment network") 
            print("3. Search by message type")
            print("4. Search by procedure name")
            print("5. Search by function calls")
            print("6. Search by keywords")
            print("7. Find validation patterns")
            print("8. Find ISO message processing")
            print("9. Find error handling patterns")
            print("10. Find similar procedures")
            print("11. Analyze flow coverage")
            print("12. Show corpus statistics")
            print("0. Exit")
            
            choice = input("\nSelect option (0-12): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                search_by_flow_interactive(searcher)
            elif choice == '2':
                search_by_network_interactive(searcher)
            elif choice == '3':
                search_by_message_interactive(searcher)
            elif choice == '4':
                search_by_procedure_interactive(searcher)
            elif choice == '5':
                search_by_function_interactive(searcher)
            elif choice == '6':
                search_by_keywords_interactive(searcher)
            elif choice == '7':
                search_validation_interactive(searcher)
            elif choice == '8':
                search_iso_interactive(searcher)
            elif choice == '9':
                search_error_handling_interactive(searcher)
            elif choice == '10':
                search_similar_procedures_interactive(searcher)
            elif choice == '11':
                analyze_coverage_interactive(searcher)
            elif choice == '12':
                show_statistics_interactive(searcher)
            else:
                print("❌ Invalid choice")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def search_by_flow_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by payment flow."""
    print("\n🔄 Available payment flows:")
    for i, flow in enumerate(FlowType, 1):
        print(f"  {i}. {flow.value.replace('_', ' ').title()}")
    
    try:
        choice = int(input("\nSelect flow (1-10): ")) - 1
        flow_type = list(FlowType)[choice]
        
        network_choice = input("Filter by network? (fedwire/swift/chips/enter for all): ").strip().lower()
        network = None
        if network_choice in ['fedwire', 'swift', 'chips']:
            network = PaymentNetwork(network_choice)
        
        min_score = float(input("Minimum score (0.0-5.0, default 0.5): ") or "0.5")
        top_k = int(input("Number of results (default 10): ") or "10")
        
        results = searcher.search_by_flow(flow_type, network, min_score, top_k)
        searcher.print_search_results(results, f"Payment Flow: {flow_type.value}")
        
        save = input("\nSave results to file? (y/n): ").strip().lower()
        if save.startswith('y'):
            filename = f"flow_search_{flow_type.value}.json"
            searcher.save_search_results(results, filename)
    
    except (ValueError, IndexError):
        print("❌ Invalid input")

def search_by_network_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by payment network."""
    print("\n🌐 Available payment networks:")
    for i, network in enumerate(PaymentNetwork, 1):
        print(f"  {i}. {network.value.upper()}")
    
    try:
        choice = int(input("\nSelect network (1-4): ")) - 1
        network = list(PaymentNetwork)[choice]
        
        flow_choice = input("Filter by flow? (validation/customer_transfer/etc, enter for all): ").strip().lower()
        flow_type = None
        if flow_choice:
            try:
                flow_type = FlowType(flow_choice)
            except ValueError:
                print(f"⚠️  Invalid flow type: {flow_choice}")
        
        top_k = int(input("Number of results (default 15): ") or "15")
        
        results = searcher.search_by_network(network, flow_type, top_k)
        scored_results = [(1.0, chunk) for chunk in results]  # Add dummy scores
        searcher.print_search_results(scored_results, f"Payment Network: {network.value.upper()}")
    
    except (ValueError, IndexError):
        print("❌ Invalid input")

def search_by_message_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by message type."""
    message_type = input("\n📨 Enter message type (mt103, pacs008, fedwire_1000, etc.): ").strip()
    if not message_type:
        print("❌ Message type required")
        return
    
    network_choice = input("Filter by network? (fedwire/swift/chips/enter for all): ").strip().lower()
    network = None
    if network_choice in ['fedwire', 'swift', 'chips']:
        network = PaymentNetwork(network_choice)
    
    top_k = int(input("Number of results (default 10): ") or "10")
    
    results = searcher.search_by_message_type(message_type, network, top_k)
    searcher.print_search_results(results, f"Message Type: {message_type}")

def search_by_procedure_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by procedure name."""
    procedure = input("\n🔧 Enter procedure name pattern: ").strip()
    if not procedure:
        print("❌ Procedure pattern required")
        return
    
    flow_choice = input("Filter by flow? (validation/customer_transfer/etc, enter for all): ").strip().lower()
    flow_type = None
    if flow_choice:
        try:
            flow_type = FlowType(flow_choice)
        except ValueError:
            print(f"⚠️  Invalid flow type: {flow_choice}")
    
    top_k = int(input("Number of results (default 10): ") or "10")
    
    results = searcher.search_by_procedure(procedure, flow_type, top_k)
    searcher.print_search_results(results, f"Procedure: {procedure}")

def search_by_function_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by function calls."""
    function = input("\n📞 Enter function name pattern: ").strip()
    if not function:
        print("❌ Function pattern required")
        return
    
    flow_choice = input("Filter by flow? (validation/customer_transfer/etc, enter for all): ").strip().lower()
    flow_type = None
    if flow_choice:
        try:
            flow_type = FlowType(flow_choice)
        except ValueError:
            print(f"⚠️  Invalid flow type: {flow_choice}")
    
    top_k = int(input("Number of results (default 10): ") or "10")
    
    results = searcher.search_by_function(function, flow_type, top_k)
    searcher.print_search_results(results, f"Function: {function}")

def search_by_keywords_interactive(searcher: PaymentFlowSearcher):
    """Interactive search by keywords."""
    keywords_input = input("\n🔑 Enter keywords (comma-separated): ").strip()
    if not keywords_input:
        print("❌ Keywords required")
        return
    
    keywords = [kw.strip() for kw in keywords_input.split(',')]
    
    flow_choice = input("Filter by flow? (validation/customer_transfer/etc, enter for all): ").strip().lower()
    flow_type = None
    if flow_choice:
        try:
            flow_type = FlowType(flow_choice)
        except ValueError:
            print(f"⚠️  Invalid flow type: {flow_choice}")
    
    network_choice = input("Filter by network? (fedwire/swift/chips/enter for all): ").strip().lower()
    network = None
    if network_choice in ['fedwire', 'swift', 'chips']:
        network = PaymentNetwork(network_choice)
    
    top_k = int(input("Number of results (default 15): ") or "15")
    
    results = searcher.search_by_keywords(keywords, flow_type, network, top_k)
    searcher.print_search_results(results, f"Keywords: {', '.join(keywords)}")

def search_validation_interactive(searcher: PaymentFlowSearcher):
    """Interactive search for validation patterns."""
    validation_type = input("\n✅ Validation type (field/message/business/enter for all): ").strip()
    message_type = input("Message type (pacs008/mt103/etc, enter for all): ").strip()
    field_name = input("Field name (amount/bic/etc, enter for all): ").strip()
    top_k = int(input("Number of results (default 10): ") or "10")
    
    results = searcher.find_validation_patterns(
        validation_type if validation_type else None,
        message_type if message_type else None, 
        field_name if field_name else None,
        top_k
    )
    searcher.print_search_results(results, "Validation Patterns", show_content=True)

def search_iso_interactive(searcher: PaymentFlowSearcher):
    """Interactive search for ISO message processing."""
    print("\n📨 Available ISO message types:")
    for i, msg_type in enumerate(ISOMessageType, 1):
        print(f"  {i}. {msg_type.value}")
    
    try:
        choice = int(input("\nSelect message type (1-11): ")) - 1
        message_type = list(ISOMessageType)[choice]
        
        processing_stage = input("Processing stage (parse/validate/transform/enter for all): ").strip()
        top_k = int(input("Number of results (default 10): ") or "10")
        
        results = searcher.find_iso_message_processing(
            message_type,
            processing_stage if processing_stage else None,
            top_k
        )
        searcher.print_search_results(results, f"ISO Message: {message_type.value}", show_content=True)
    
    except (ValueError, IndexError):
        print("❌ Invalid input")

def search_error_handling_interactive(searcher: PaymentFlowSearcher):
    """Interactive search for error handling patterns."""
    error_type = input("\n⚠️  Error type (validation/timeout/reject/etc, enter for all): ").strip()
    
    network_choice = input("Filter by network? (fedwire/swift/chips/enter for all): ").strip().lower()
    network = None
    if network_choice in ['fedwire', 'swift', 'chips']:
        network = PaymentNetwork(network_choice)
    
    top_k = int(input("Number of results (default 10): ") or "10")
    
    results = searcher.find_error_handling_patterns(
        error_type if error_type else None,
        network,
        top_k
    )
    searcher.print_search_results(results, "Error Handling Patterns", show_content=True)

def search_similar_procedures_interactive(searcher: PaymentFlowSearcher):
    """Interactive search for similar procedures."""
    reference = input("\n🔧 Enter reference procedure name: ").strip()
    if not reference:
        print("❌ Reference procedure required")
        return
    
    flow_choice = input("Filter by flow? (validation/customer_transfer/etc, enter for all): ").strip().lower()
    flow_type = None
    if flow_choice:
        try:
            flow_type = FlowType(flow_choice)
        except ValueError:
            print(f"⚠️  Invalid flow type: {flow_choice}")
    
    top_k = int(input("Number of results (default 5): ") or "5")
    
    results = searcher.find_similar_procedures(reference, flow_type, top_k)
    searcher.print_search_results(results, f"Similar to: {reference}")

def analyze_coverage_interactive(searcher: PaymentFlowSearcher):
    """Interactive flow coverage analysis."""
    print("\n📊 Analyzing payment flow coverage...")
    analysis = searcher.analyze_flow_coverage()
    
    print(f"\n{'='*50}")
    print("📈 FLOW COVERAGE ANALYSIS")
    print(f"{'='*50}")
    
    print(f"Total chunks: {analysis['total_chunks']}")
    print(f"Chunks with flows: {analysis['chunks_with_flows']}")
    print(f"Coverage rate: {analysis['chunks_with_flows']/analysis['total_chunks']*100:.1f}%")
    
    print(f"\n🔄 Flow Distribution:")
    for flow, count in sorted(analysis['flow_distribution'].items(), key=lambda x: x[1], reverse=True):
        flow_name = flow.replace('_', ' ').title()
        print(f"  {flow_name}: {count} chunks")
    
    print(f"\n🌐 Network Distribution:")
    for network, count in sorted(analysis['network_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {network.upper()}: {count} chunks")
    
    if analysis['coverage_gaps']:
        print(f"\n⚠️  Coverage Gaps:")
        for gap in analysis['coverage_gaps']:
            print(f"  {gap}")
    
    print(f"\n📊 Flow-Network Matrix:")
    print("Flow\\Network    Fedwire  SWIFT  CHIPS  General")
    print("-" * 45)
    for flow, networks in analysis['flow_network_matrix'].items():
        flow_short = flow.replace('_', ' ').title()[:12].ljust(12)
        fedwire = str(networks.get('fedwire', 0)).rjust(7)
        swift = str(networks.get('swift', 0)).rjust(6)
        chips = str(networks.get('chips', 0)).rjust(6)
        general = str(networks.get('general', 0)).rjust(8)
        print(f"{flow_short} {fedwire} {swift} {chips} {general}")

def show_statistics_interactive(searcher: PaymentFlowSearcher):
    """Interactive corpus statistics display."""
    print("\n📊 Generating corpus statistics...")
    stats = searcher.get_corpus_statistics()
    
    print(f"\n{'='*50}")
    print("📈 CORPUS STATISTICS")
    print(f"{'='*50}")
    
    # Basic stats
    basic = stats['basic_stats']
    print(f"Total chunks: {basic['total_chunks']}")
    print(f"Chunks with procedures: {basic['chunks_with_procedures']}")
    print(f"Chunks with flows: {basic['chunks_with_flows']}")
    print(f"Chunks with networks: {basic['chunks_with_networks']}")
    
    # Flow stats
    print(f"\n🔄 Flow Statistics:")
    for flow, data in sorted(stats['flow_stats'].items(), key=lambda x: x[1]['total_chunks'], reverse=True):
        flow_name = flow.replace('_', ' ').title()
        print(f"  {flow_name}: {data['total_chunks']} chunks (avg score: {data['avg_score']:.2f})")
    
    # Network stats
    print(f"\n🌐 Network Statistics:")
    for network, count in sorted(stats['network_stats'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {network.upper()}: {count} chunks")
    
    # Top message patterns
    if stats['message_stats']:
        print(f"\n📨 Top Message Patterns:")
        for pattern, count in sorted(stats['message_stats'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pattern}: {count} chunks")
    
    # Top procedures
    print(f"\n🔧 Top Procedures (by flow coverage):")
    for proc, flow_count in stats['top_procedures'][:10]:
        print(f"  {proc}: {flow_count} flows")
    
    # Top functions
    print(f"\n📞 Top Function Calls:")
    for func, count in stats['top_functions'][:10]:
        print(f"  {func}(): {count} references")

if __name__ == "__main__":
    main()
