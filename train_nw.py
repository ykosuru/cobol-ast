#!/usr/bin/env python3
"""
Complete Standalone AI Trainer for Indexed TAL Code

Wire Processing Development Assistant - No external model downloads.
Uses only scikit-learn and built-in libraries for AI-powered code generation.
"""

import os
import json
import pickle
import random
import re
import sys
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from collections import Counter, defaultdict
import math

# Only use libraries that don't download external models
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.pipeline import Pipeline
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("❌ Install scikit-learn: pip install scikit-learn numpy")

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

@dataclass
class TrainingExample:
    """Training example for various model types."""
    input_text: str
    target_text: str
    metadata: Dict[str, Any]
    task_type: str

class WireProcessingFeatureExtractor:
    """Extract features from TAL code for machine learning."""
    
    def __init__(self):
        # Wire processing specific patterns
        self.wire_keywords = {
            'iso20022': ['iso20022', 'pacs', 'pain', 'camt', 'pacs008', 'pacs009', 'xml'],
            'swift': ['swift', 'mt103', 'mt202', 'gpi', 'uetr', 'bic', 'fin'],
            'fedwire': ['fedwire', 'imad', 'omad', 'federal', 'reserve', 'typecode'],
            'chips': ['chips', 'uid', 'netting', 'clearing', 'house'],
            'compliance': ['ofac', 'sanctions', 'aml', 'kyc', 'screening', 'compliance'],
            'exception': ['exception', 'error', 'repair', 'investigation', 'return']
        }
        
        # Technical patterns
        self.technical_patterns = {
            'validation': r'(?i)\b(validat|verify|check)\w*',
            'processing': r'(?i)\b(process|handle|execute)\w*',
            'screening': r'(?i)\b(screen|monitor|detect)\w*',
            'transmission': r'(?i)\b(send|transmit|forward)\w*'
        }
    
    def extract_features(self, chunk) -> Dict[str, Any]:
        """Extract comprehensive features from a code chunk."""
        features = {}
        content_lower = chunk.content.lower()
        
        # Basic metrics
        features['word_count'] = getattr(chunk, 'word_count', 0)
        features['char_count'] = getattr(chunk, 'char_count', 0)
        features['line_count'] = len(chunk.content.split('\n'))
        
        # Procedure-based features
        features['has_procedure'] = 1 if getattr(chunk, 'procedure_name', '') else 0
        if chunk.procedure_name:
            proc_name = chunk.procedure_name.lower()
            features['proc_validate'] = 1 if 'validate' in proc_name else 0
            features['proc_process'] = 1 if 'process' in proc_name else 0
            features['proc_screen'] = 1 if 'screen' in proc_name else 0
            features['proc_send'] = 1 if 'send' in proc_name or 'transmit' in proc_name else 0
        else:
            features['proc_validate'] = 0
            features['proc_process'] = 0
            features['proc_screen'] = 0
            features['proc_send'] = 0
        
        # Wire processing domain features
        for domain, keywords in self.wire_keywords.items():
            count = sum(1 for keyword in keywords if keyword in content_lower)
            features[f'wire_{domain}_count'] = count
            features[f'wire_{domain}_present'] = 1 if count > 0 else 0
        
        # Technical pattern features
        for pattern_name, pattern in self.technical_patterns.items():
            matches = len(re.findall(pattern, chunk.content))
            features[f'pattern_{pattern_name}'] = matches
        
        # Function call features
        function_calls = getattr(chunk, 'function_calls', [])
        features['function_count'] = len(function_calls)
        features['has_functions'] = 1 if function_calls else 0
        
        # Common wire processing function patterns
        wire_functions = ['validate', 'process', 'send', 'receive', 'screen', 'check']
        for func_pattern in wire_functions:
            count = sum(1 for func in function_calls if func_pattern in func.lower())
            features[f'func_{func_pattern}'] = count
        
        # Variable declaration features
        var_declarations = getattr(chunk, 'variable_declarations', [])
        features['variable_count'] = len(var_declarations)
        
        # Control structure features
        control_structures = getattr(chunk, 'control_structures', [])
        features['control_count'] = len(control_structures)
        features['has_if'] = 1 if 'if' in control_structures else 0
        features['has_while'] = 1 if 'while' in control_structures else 0
        features['has_for'] = 1 if 'for' in control_structures else 0
        
        # Keyword density features
        keywords = getattr(chunk, 'keywords', [])
        if keywords:
            wire_keyword_count = sum(1 for kw in keywords 
                                   if any(wire_kw in kw.lower() 
                                         for wire_kws in self.wire_keywords.values() 
                                         for wire_kw in wire_kws))
            features['wire_keyword_density'] = wire_keyword_count / len(keywords)
        else:
            features['wire_keyword_density'] = 0
        
        return features

class StandaloneCorpusDataExtractor:
    """Extract training data using only built-in libraries."""
    
    def __init__(self, corpus_paths):
        # Handle both single string and list of paths
        if isinstance(corpus_paths, str):
            self.corpus_paths = [corpus_paths]
        else:
            self.corpus_paths = corpus_paths
        
        self.chunks = []
        self.vectorizer_data = {}
        self.functionality_groups = {}
        self.feature_extractor = WireProcessingFeatureExtractor()
        self.corpus_metadata = {}
        self.load_multiple_corpora()

    def load_multiple_corpora(self):
        """Load multiple indexed corpora and combine them."""
        print(f"📚 Loading {len(self.corpus_paths)} corpus files...")
        
        # Add SimpleChunk to global namespace for pickle compatibility
        globals()['SimpleChunk'] = SimpleChunk
        sys.modules[__name__].SimpleChunk = SimpleChunk
        
        all_chunks = []
        combined_functionality_groups = defaultdict(list)
        corpus_info = []
        
        for i, corpus_path in enumerate(self.corpus_paths):
            print(f"   📖 Loading corpus {i+1}/{len(self.corpus_paths)}: {os.path.basename(corpus_path)}")
            
            try:
                with open(corpus_path, 'rb') as f:
                    corpus_data = pickle.load(f)
                
                corpus_chunks = []
                
                # Reconstruct chunks with error handling
                for j, chunk_data in enumerate(corpus_data.get('chunks', [])):
                    try:
                        # Handle both object and dictionary formats
                        if hasattr(chunk_data, '__dict__'):
                            chunk = chunk_data
                        else:
                            chunk = type('Chunk', (), {})()
                            for key, value in chunk_data.items():
                                setattr(chunk, key, value)
                        
                        # Ensure required attributes exist
                        if not hasattr(chunk, 'semantic_category'):
                            chunk.semantic_category = 'general_processing'
                        if not hasattr(chunk, 'keywords'):
                            chunk.keywords = []
                        if not hasattr(chunk, 'function_calls'):
                            chunk.function_calls = []
                        
                        # Add corpus source information
                        chunk.corpus_source = os.path.basename(corpus_path)
                        chunk.corpus_index = i
                        
                        corpus_chunks.append(chunk)
                        
                    except Exception as e:
                        print(f"⚠️  Warning: Error loading chunk {j} from {corpus_path}: {e}")
                        continue
                
                all_chunks.extend(corpus_chunks)
                
                # Combine functionality groups
                func_groups = corpus_data.get('functionality_groups', {})
                for group_type, groups in func_groups.items():
                    if isinstance(groups, dict):
                        for group_name, group_chunks in groups.items():
                            combined_functionality_groups[f"{group_type}_{group_name}"].extend(group_chunks)
                
                # Store corpus metadata
                corpus_info.append({
                    'path': corpus_path,
                    'version': corpus_data.get('version', 'unknown'),
                    'created_at': corpus_data.get('created_at', 'unknown'),
                    'chunk_count': len(corpus_chunks),
                    'stats': corpus_data.get('stats', {})
                })
                
                # Use vectorizer data from the first corpus (they should be compatible)
                if i == 0:
                    self.vectorizer_data = corpus_data.get('vectorizer', {})
                
                print(f"      ✅ Loaded {len(corpus_chunks)} chunks")
                
            except Exception as e:
                print(f"      ❌ Error loading {corpus_path}: {e}")
                continue
        
        self.chunks = all_chunks
        self.functionality_groups = dict(combined_functionality_groups)
        self.corpus_metadata = {
            'combined_corpora': corpus_info,
            'total_files': len(self.corpus_paths),
            'successful_loads': len([info for info in corpus_info if info['chunk_count'] > 0])
        }
        
        print(f"✅ Combined corpus loaded:")
        print(f"   📦 Total chunks: {len(self.chunks)}")
        print(f"   📁 Successful corpus files: {self.corpus_metadata['successful_loads']}/{len(self.corpus_paths)}")
        
        # Show corpus breakdown
        if len(corpus_info) > 1:
            print(f"   📊 Corpus breakdown:")
            for info in corpus_info:
                if info['chunk_count'] > 0:
                    print(f"      {os.path.basename(info['path'])}: {info['chunk_count']} chunks")
    
    def get_corpus_statistics(self):
        """Get statistics across all loaded corpora."""
        stats = {
            'total_chunks': len(self.chunks),
            'corpus_sources': {},
            'semantic_categories': {},
            'combined_functionality_groups': len(self.functionality_groups)
        }
        
        # Count chunks by source
        for chunk in self.chunks:
            source = getattr(chunk, 'corpus_source', 'unknown')
            stats['corpus_sources'][source] = stats['corpus_sources'].get(source, 0) + 1
        
        # Count semantic categories
        for chunk in self.chunks:
            category = getattr(chunk, 'semantic_category', 'unknown')
            stats['semantic_categories'][category] = stats['semantic_categories'].get(category, 0) + 1
        
        return stats

    def create_classification_dataset(self) -> Tuple[List[Dict], List[str], List[Dict]]:
        """Create feature vectors and labels for classification."""
        features_list = []
        labels = []
        metadata_list = []
        
        print("🔧 Extracting features for classification...")
        
        for chunk in self.chunks:
            if hasattr(chunk, 'semantic_category') and chunk.semantic_category:
                # Extract features
                features = self.feature_extractor.extract_features(chunk)
                
                # Add text content for TF-IDF
                features['content'] = self.clean_code_for_training(chunk.content)
                
                features_list.append(features)
                labels.append(chunk.semantic_category)
                
                metadata_list.append({
                    'file': chunk.source_file,
                    'procedure': getattr(chunk, 'procedure_name', ''),
                    'topic_prob': getattr(chunk, 'dominant_topic_prob', 0.0)
                })
        
        print(f"📊 Created {len(features_list)} feature vectors")
        return features_list, labels, metadata_list
    
    def create_understanding_dataset(self) -> List[Tuple[str, str]]:
        """Create simple rule-based code explanations."""
        examples = []
        
        print("🧠 Creating understanding examples...")
        
        for chunk in self.chunks:
            if (hasattr(chunk, 'keywords') and chunk.keywords and 
                hasattr(chunk, 'semantic_category')):
                
                code_text = self.clean_code_for_training(chunk.content)
                explanation = self.generate_rule_based_explanation(chunk)
                
                examples.append((code_text, explanation))
        
        print(f"🧠 Created {len(examples)} understanding examples")
        return examples
    
    def clean_code_for_training(self, code: str) -> str:
        """Clean code for training."""
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('!') and not stripped.startswith('//'):
                if '!' in line:
                    line = line[:line.index('!')].rstrip()
                if line.strip():
                    cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def generate_rule_based_explanation(self, chunk) -> str:
        """Generate explanation using rules instead of AI."""
        explanation_parts = []
        
        # Category-based explanation
        category_explanations = {
            'iso20022_messages': 'This code processes ISO 20022 payment messages',
            'swift_processing': 'This code handles SWIFT message processing', 
            'fedwire_operations': 'This code manages Fedwire operations',
            'chips_processing': 'This code handles CHIPS processing',
            'compliance_screening': 'This code performs compliance and screening functions',
            'investigation_exceptions': 'This code handles payment exceptions and investigations'
        }
        
        if hasattr(chunk, 'semantic_category'):
            base_explanation = category_explanations.get(
                chunk.semantic_category,
                f"This code implements {chunk.semantic_category.replace('_', ' ')}"
            )
            explanation_parts.append(base_explanation)
        
        # Procedure-based explanation
        if getattr(chunk, 'procedure_name', ''):
            proc_name = chunk.procedure_name.lower()
            if 'validate' in proc_name:
                explanation_parts.append("It validates input data and message formats")
            elif 'process' in proc_name:
                explanation_parts.append("It processes payment transactions")
            elif 'screen' in proc_name:
                explanation_parts.append("It screens transactions for compliance")
            elif 'send' in proc_name or 'transmit' in proc_name:
                explanation_parts.append("It transmits payment messages")
        
        # Function-based explanation
        function_calls = getattr(chunk, 'function_calls', [])
        if function_calls:
            key_functions = [f for f in function_calls[:3] if len(f) > 3]
            if key_functions:
                explanation_parts.append(f"Key functions include: {', '.join(key_functions)}")
        
        return '. '.join(explanation_parts) + '.'

class CodeSnippetGenerator:
    """Generate TAL code snippets from developer questions."""
    
    def __init__(self, corpus_paths):
        self.extractor = StandaloneCorpusDataExtractor(corpus_paths)
        self.template_library = {}
        self.pattern_library = {}
        self.build_code_libraries()
    
    def build_code_libraries(self):
        """Build libraries of code templates and patterns from corpus."""
        print("🔧 Building code snippet libraries...")
        
        # Organize chunks by semantic category and patterns
        for chunk in self.extractor.chunks:
            category = getattr(chunk, 'semantic_category', 'general')
            
            # Build template library by category
            if category not in self.template_library:
                self.template_library[category] = []
            
            # Store clean, reusable code snippets
            if (chunk.procedure_name and 
                len(chunk.content.split('\n')) < 30 and  # Not too long
                len(chunk.content.split('\n')) > 5):     # Not too short
                
                template = {
                    'name': chunk.procedure_name,
                    'code': self.extract_reusable_code(chunk.content),
                    'description': self.generate_template_description(chunk),
                    'keywords': getattr(chunk, 'keywords', []),
                    'functions': getattr(chunk, 'function_calls', [])
                }
                self.template_library[category].append(template)
        
        # Build pattern library for common constructs
        self.build_pattern_library()
        
        print(f"✅ Built {len(self.template_library)} category libraries")
        total_templates = sum(len(templates) for templates in self.template_library.values())
        print(f"📚 {total_templates} code templates available")
    
    def build_pattern_library(self):
        """Build library of common TAL patterns."""
        self.pattern_library = {
            'validation': {
                'description': 'Validate input data or message format',
                'template': '''PROC VALIDATE_{TYPE}({param});
BEGIN
    ! Validate {type} format and content
    IF NOT CHECK_{TYPE}_FORMAT({param}) THEN
        CALL LOG_ERROR("Invalid {type} format");
        RETURN 0;
    END;
    
    ! Additional validation logic here
    
    RETURN 1;
END;''',
                'variables': ['{TYPE}', '{param}', '{type}']
            },
            
            'swift_processing': {
                'description': 'Process SWIFT message',
                'template': '''PROC PROCESS_SWIFT_{MESSAGE_TYPE}(message_buffer);
BEGIN
    STRING bic_field[11];
    STRING amount_field[15];
    INT result := 0;
    
    ! Extract key fields
    CALL EXTRACT_BIC_CODE(message_buffer, bic_field);
    CALL EXTRACT_AMOUNT(message_buffer, amount_field);
    
    ! Validate message format
    IF VALIDATE_SWIFT_FORMAT(message_buffer) THEN
        ! Process the message
        result := EXECUTE_SWIFT_PROCESSING(message_buffer);
    ELSE
        CALL LOG_SWIFT_ERROR("Invalid format", message_buffer);
    END;
    
    RETURN result;
END;''',
                'variables': ['{MESSAGE_TYPE}']
            },
            
            'fedwire_processing': {
                'description': 'Process Fedwire transaction',
                'template': '''PROC PROCESS_FEDWIRE_{TYPE}(wire_data);
BEGIN
    STRING imad[9];
    STRING omad[9];
    INT status := 0;
    
    ! Generate IMAD/OMAD
    CALL GENERATE_IMAD(imad);
    CALL GENERATE_OMAD(omad);
    
    ! Validate Fedwire format
    IF VALIDATE_FEDWIRE_FORMAT(wire_data) THEN
        ! Execute wire transfer
        status := EXECUTE_FEDWIRE_TRANSFER(wire_data, imad, omad);
    ELSE
        CALL REJECT_FEDWIRE("Format error", wire_data);
        status := -1;
    END;
    
    RETURN status;
END;''',
                'variables': ['{TYPE}']
            },
            
            'ofac_screening': {
                'description': 'Screen for OFAC sanctions',
                'template': '''PROC SCREEN_OFAC_{ENTITY}({entity}_data);
BEGIN
    INT match_result := 0;
    STRING match_info[100];
    
    ! Screen against OFAC list
    match_result := CHECK_OFAC_LIST({entity}_data, match_info);
    
    IF match_result > 0 THEN
        ! OFAC match found - hold transaction
        CALL HOLD_FOR_OFAC_REVIEW({entity}_data, match_info);
        CALL LOG_OFAC_HIT({entity}_data, match_result);
        RETURN 0;  ! Blocked
    ELSE
        ! No match - allow processing
        CALL LOG_OFAC_CLEAR({entity}_data);
        RETURN 1;  ! Approved
    END;
END;''',
                'variables': ['{ENTITY}', '{entity}']
            },
            
            'error_handling': {
                'description': 'Handle errors and exceptions',
                'template': '''PROC HANDLE_{ERROR_TYPE}_ERROR(error_code, error_data);
BEGIN
    STRING error_msg[200];
    INT recovery_action := 0;
    
    ! Log the error
    CALL FORMAT_ERROR_MESSAGE(error_code, error_data, error_msg);
    CALL LOG_ERROR(error_msg);
    
    ! Determine recovery action
    CASE error_code OF
        BEGIN
        1000 TO 1999:  ! Validation errors
            recovery_action := REPAIR_DATA_ERROR(error_data);
        2000 TO 2999:  ! Network errors  
            recovery_action := RETRY_TRANSMISSION(error_data);
        OTHERWISE:
            recovery_action := ESCALATE_ERROR(error_code, error_data);
        END;
    
    RETURN recovery_action;
END;''',
                'variables': ['{ERROR_TYPE}']
            },
            
            'iso20022_processing': {
                'description': 'Process ISO 20022 message',
                'template': '''PROC PROCESS_ISO20022_{MSG_TYPE}(xml_message);
BEGIN
    STRING parsed_data[1000];
    INT validation_result := 0;
    
    ! Parse XML message
    validation_result := PARSE_ISO20022_XML(xml_message, parsed_data);
    
    IF validation_result = 1 THEN
        ! Validate business rules
        IF VALIDATE_ISO20022_BUSINESS_RULES(parsed_data) THEN
            ! Process the payment
            CALL EXECUTE_ISO20022_PAYMENT(parsed_data);
        ELSE
            CALL REJECT_ISO20022("Business rule violation", xml_message);
        END;
    ELSE
        CALL REJECT_ISO20022("XML parsing error", xml_message);
    END;
END;''',
                'variables': ['{MSG_TYPE}']
            }
        }
    
    def generate_code_snippet(self, question: str) -> Dict[str, Any]:
        """Generate code snippet from developer question with enhanced explanations."""
        print(f"🤖 Generating implementation for: '{question}'")
        
        # Analyze the question to determine intent and category
        intent_analysis = self.analyze_question_intent(question)
        
        # Find best matching pattern or template
        if intent_analysis['pattern_match']:
            # Use pattern-based generation
            snippet = self.generate_from_pattern(intent_analysis)
        else:
            # Use template-based generation from corpus
            snippet = self.generate_from_templates(intent_analysis)
        
        # Add implementation guidance
        implementation_guidance = self.generate_implementation_guidance(intent_analysis, snippet)
        
        return {
            'question': question,
            'generated_code': snippet['code'],
            'description': snippet['description'],
            'category': intent_analysis['category'],
            'confidence': intent_analysis['confidence'],
            'suggestions': snippet.get('suggestions', []),
            'implementation_steps': implementation_guidance['steps'],
            'integration_notes': implementation_guidance['integration'],
            'testing_approach': implementation_guidance['testing'],
            'related_procedures': implementation_guidance['related']
        }
    
    def generate_implementation_guidance(self, intent_analysis: Dict[str, Any], snippet: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive implementation guidance for developers."""
        category = intent_analysis['category']
        
        guidance = {
            'steps': [],
            'integration': [],
            'testing': [],
            'related': []
        }
        
        # Category-specific implementation steps
        if category == 'swift_processing':
            guidance['steps'] = [
                "1. Set up SWIFT message parsing infrastructure",
                "2. Implement BIC validation and lookup functions",
                "3. Add message format validation (MT103, MT202, etc.)",
                "4. Implement gpi UETR tracking if required",
                "5. Add error handling for malformed messages"
            ]
            guidance['integration'] = [
                "• Integrate with SWIFT Alliance Access or similar gateway",
                "• Connect to BIC directory service for validation",
                "• Link to your core payment processing system",
                "• Set up message queuing for high-volume processing"
            ]
            guidance['testing'] = [
                "• Test with sample SWIFT MT messages",
                "• Validate BIC format checking",
                "• Test error handling with malformed messages",
                "• Performance test with message volumes"
            ]
            guidance['related'] = [
                "EXTRACT_BIC_CODE", "VALIDATE_SWIFT_FORMAT", 
                "LOG_SWIFT_ERROR", "EXECUTE_SWIFT_PROCESSING"
            ]
        
        elif category == 'fedwire_operations':
            guidance['steps'] = [
                "1. Set up Fedwire type code processing",
                "2. Implement IMAD/OMAD generation logic",
                "3. Add Federal Reserve participant validation",
                "4. Implement cutoff time checking",
                "5. Add settlement and confirmation handling"
            ]
            guidance['integration'] = [
                "• Connect to FedLine Advantage or similar Fed interface",
                "• Integrate with your settlement accounting system",
                "• Link to participant directory for validation",
                "• Set up real-time status reporting"
            ]
            guidance['testing'] = [
                "• Test IMAD/OMAD generation uniqueness",
                "• Validate type code processing",
                "• Test cutoff time handling",
                "• Verify settlement confirmation processing"
            ]
            guidance['related'] = [
                "GENERATE_IMAD", "GENERATE_OMAD", "VALIDATE_FEDWIRE_FORMAT",
                "EXECUTE_FEDWIRE_TRANSFER"
            ]
        
        elif category == 'ofac_screening':
            guidance['steps'] = [
                "1. Set up OFAC SDN list access and updates",
                "2. Implement fuzzy matching algorithms",
                "3. Add name normalization and cleansing",
                "4. Implement scoring and threshold logic",
                "5. Add review workflow for manual processing"
            ]
            guidance['integration'] = [
                "• Connect to OFAC SDN list updates (daily/real-time)",
                "• Integrate with case management system",
                "• Link to transaction hold/release mechanisms",
                "• Set up compliance reporting interfaces"
            ]
            guidance['testing'] = [
                "• Test with known OFAC match scenarios",
                "• Validate false positive handling",
                "• Test performance with large transaction volumes",
                "• Verify audit trail completeness"
            ]
            guidance['related'] = [
                "CHECK_OFAC_LIST", "HOLD_FOR_OFAC_REVIEW",
                "LOG_OFAC_HIT", "LOG_OFAC_CLEAR"
            ]
        
        elif category == 'validation':
            guidance['steps'] = [
                "1. Define validation rules and business logic",
                "2. Implement field-level format checking",
                "3. Add cross-field validation rules",
                "4. Implement business rule validation",
                "5. Add comprehensive error reporting"
            ]
            guidance['integration'] = [
                "• Integrate with your data dictionary/schema",
                "• Connect to reference data services",
                "• Link to error handling and notification systems",
                "• Set up validation rule configuration"
            ]
            guidance['testing'] = [
                "• Test each validation rule individually",
                "• Test with valid and invalid data sets",
                "• Verify error message clarity",
                "• Performance test validation logic"
            ]
            guidance['related'] = [
                "CHECK_FORMAT", "VALIDATE_BUSINESS_RULES",
                "LOG_VALIDATION_ERROR", "FORMAT_ERROR_MESSAGE"
            ]
        
        elif category == 'iso20022_processing':
            guidance['steps'] = [
                "1. Set up XML parsing and validation infrastructure",
                "2. Implement ISO 20022 schema validation",
                "3. Add business rule validation per message type",
                "4. Implement message transformation logic",
                "5. Add comprehensive error handling"
            ]
            guidance['integration'] = [
                "• Connect to ISO 20022 schema repositories",
                "• Integrate with XML processing libraries",
                "• Link to your payment processing core",
                "• Set up message routing and queuing"
            ]
            guidance['testing'] = [
                "• Test with ISO 20022 sample messages",
                "• Validate XML schema compliance",
                "• Test business rule validation",
                "• Performance test with large XML messages"
            ]
            guidance['related'] = [
                "PARSE_ISO20022_XML", "VALIDATE_ISO20022_BUSINESS_RULES",
                "EXECUTE_ISO20022_PAYMENT", "REJECT_ISO20022"
            ]
        
        elif category == 'error_handling':
            guidance['steps'] = [
                "1. Define error codes and categories",
                "2. Implement error logging and tracking",
                "3. Add error recovery and retry logic",
                "4. Implement escalation procedures",
                "5. Add comprehensive error reporting"
            ]
            guidance['integration'] = [
                "• Connect to centralized logging system",
                "• Integrate with monitoring and alerting",
                "• Link to case management for escalations",
                "• Set up error analytics and reporting"
            ]
            guidance['testing'] = [
                "• Test each error scenario individually",
                "• Verify error recovery mechanisms",
                "• Test escalation procedures",
                "• Validate error reporting accuracy"
            ]
            guidance['related'] = [
                "LOG_ERROR", "FORMAT_ERROR_MESSAGE", 
                "REPAIR_DATA_ERROR", "ESCALATE_ERROR"
            ]
        
        else:
            # Generic guidance
            guidance['steps'] = [
                "1. Analyze business requirements thoroughly",
                "2. Design the procedure interface and parameters",
                "3. Implement core business logic",
                "4. Add comprehensive error handling",
                "5. Implement logging and monitoring"
            ]
            guidance['integration'] = [
                "• Integrate with existing system architecture",
                "• Connect to required data sources",
                "• Link to downstream processing systems",
                "• Set up monitoring and alerting"
            ]
            guidance['testing'] = [
                "• Unit test individual components",
                "• Integration test with related systems",
                "• Performance test under load",
                "• User acceptance testing"
            ]
            guidance['related'] = ["Related procedures will depend on your specific implementation"]
        
        return guidance
    
    def analyze_question_intent(self, question: str) -> Dict[str, Any]:
        """Analyze developer question to determine intent."""
        question_lower = question.lower()
        
        # Pattern matching for specific intents
        intent_patterns = {
            'validation': ['validate', 'check', 'verify', 'format'],
            'swift_processing': ['swift', 'mt103', 'mt202', 'bic', 'gpi'],
            'fedwire_processing': ['fedwire', 'imad', 'omad', 'federal reserve'],
            'ofac_screening': ['ofac', 'sanctions', 'aml', 'screening', 'watchlist'],
            'error_handling': ['error', 'exception', 'handle', 'catch', 'recover'],
            'iso20022_processing': ['iso20022', 'pacs', 'pain', 'camt', 'xml']
        }
        
        # Score each category
        category_scores = {}
        for category, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                category_scores[category] = score
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[best_category] / len(intent_patterns[best_category])
            pattern_match = best_category in self.pattern_library
        else:
            best_category = 'general'
            confidence = 0.5
            pattern_match = False
        
        # Extract specific entities (message types, etc.)
        entities = self.extract_entities_from_question(question)
        
        return {
            'category': best_category,
            'confidence': confidence,
            'pattern_match': pattern_match,
            'entities': entities,
            'action_type': self.determine_action_type(question_lower)
        }
    
    def extract_entities_from_question(self, question: str) -> Dict[str, str]:
        """Extract specific entities like message types from question."""
        entities = {}
        question_upper = question.upper()
        
        # SWIFT message types
        swift_patterns = ['MT103', 'MT202', 'MT202COV', 'MT199', 'MT299']
        for pattern in swift_patterns:
            if pattern in question_upper:
                entities['swift_message_type'] = pattern
        
        # ISO 20022 message types
        iso_patterns = ['PACS.008', 'PACS.009', 'PAIN.001', 'CAMT.056', 'CAMT.029']
        for pattern in iso_patterns:
            if pattern.replace('.', '') in question_upper.replace('.', ''):
                entities['iso_message_type'] = pattern
        
        # Fedwire type codes
        if 'TYPE CODE' in question_upper or 'TYPECODE' in question_upper:
            entities['fedwire_type'] = 'TYPE_CODE'
        
        return entities
    
    def determine_action_type(self, question_lower: str) -> str:
        """Determine what type of action the developer wants."""
        if any(word in question_lower for word in ['create', 'generate', 'build', 'make']):
            return 'create'
        elif any(word in question_lower for word in ['validate', 'check', 'verify']):
            return 'validate'
        elif any(word in question_lower for word in ['process', 'handle', 'execute']):
            return 'process'
        elif any(word in question_lower for word in ['screen', 'filter', 'check']):
            return 'screen'
        else:
            return 'general'
    
    def generate_from_pattern(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using predefined patterns."""
        category = intent_analysis['category']
        pattern = self.pattern_library[category]
        
        # Customize the template based on entities
        customized_code = pattern['template']
        variables = pattern.get('variables', [])
        
        # Replace variables with extracted entities or defaults
        for variable in variables:
            if variable == '{TYPE}' or variable == '{MESSAGE_TYPE}':
                if 'swift_message_type' in intent_analysis['entities']:
                    replacement = intent_analysis['entities']['swift_message_type']
                elif 'iso_message_type' in intent_analysis['entities']:
                    replacement = intent_analysis['entities']['iso_message_type'].replace('.', '')
                else:
                    replacement = 'GENERIC'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{type}':
                # Lowercase version
                if 'swift_message_type' in intent_analysis['entities']:
                    replacement = intent_analysis['entities']['swift_message_type'].lower()
                else:
                    replacement = 'message'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{param}':
                replacement = 'input_data'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{ENTITY}':
                replacement = 'CUSTOMER'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{entity}':
                replacement = 'customer'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{ERROR_TYPE}':
                replacement = 'VALIDATION'
                customized_code = customized_code.replace(variable, replacement)
            
            elif variable == '{MSG_TYPE}':
                if 'iso_message_type' in intent_analysis['entities']:
                    replacement = intent_analysis['entities']['iso_message_type'].replace('.', '_')
                else:
                    replacement = 'PACS008'
                customized_code = customized_code.replace(variable, replacement)
        
        return {
            'code': customized_code,
            'description': pattern['description'],
            'suggestions': [
                "Customize the variable names for your specific use case",
                "Add additional validation logic as needed",
                "Update error handling for your system's requirements"
            ]
        }
    
    def generate_from_templates(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code using corpus templates."""
        category = intent_analysis['category']
        
        # Find templates in this category
        templates = self.template_library.get(category, [])
        
        if not templates:
            # Fallback to general templates
            all_templates = []
            for cat_templates in self.template_library.values():
                all_templates.extend(cat_templates)
            templates = all_templates[:5]  # Take first 5 as examples
        
        if templates:
            # Pick the best template (for now, just the first one)
            best_template = templates[0]
            
            return {
                'code': best_template['code'],
                'description': f"Based on {best_template['name']}: {best_template['description']}",
                'suggestions': [
                    f"This template is based on the procedure: {best_template['name']}",
                    f"Key functions used: {', '.join(best_template['functions'][:3])}",
                    "Modify the procedure name and parameters for your needs"
                ]
            }
        else:
            # Fallback generic template
            return {
                'code': '''PROC YOUR_PROCEDURE_NAME(input_parameter);
BEGIN
    ! Add your implementation here
    ! This is a generic template
    
    INT result := 0;
    
    ! Your code logic
    
    RETURN result;
END;''',
                'description': "Generic TAL procedure template",
                'suggestions': [
                    "Replace YOUR_PROCEDURE_NAME with a meaningful name",
                    "Add appropriate parameters and return type",
                    "Implement your specific business logic"
                ]
            }
    
    def extract_reusable_code(self, content: str) -> str:
        """Extract clean, reusable code from chunk content."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Keep meaningful code lines, remove comments
            if (stripped and 
                not stripped.startswith('!') and 
                not stripped.startswith('//') and
                len(stripped) > 3):
                # Remove inline comments
                if '!' in line:
                    line = line[:line.index('!')].rstrip()
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def generate_template_description(self, chunk) -> str:
        """Generate description for a code template."""
        proc_name = chunk.procedure_name or "procedure"
        category = getattr(chunk, 'semantic_category', 'general')
        
        # Generate description based on procedure name and category
        if 'validate' in proc_name.lower():
            return f"Validates data for {category.replace('_', ' ')}"
        elif 'process' in proc_name.lower():
            return f"Processes {category.replace('_', ' ')}"
        elif 'screen' in proc_name.lower():
            return f"Screens for {category.replace('_', ' ')}"
        else:
            return f"Handles {category.replace('_', ' ')} functionality"

class StandaloneWireProcessingTrainer:
    """Train models using only scikit-learn - no external downloads."""
    
    def __init__(self, corpus_paths):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required. Install with: pip install scikit-learn numpy")
        
        self.extractor = StandaloneCorpusDataExtractor(corpus_paths)
        self.models = {}
        self.vectorizers = {}
    
    def show_corpus_overview(self):
        """Show overview of loaded corpora."""
        stats = self.extractor.get_corpus_statistics()
        
        print(f"\n{'='*60}")
        print("📊 COMBINED CORPUS OVERVIEW")
        print("="*60)
        print(f"Total chunks: {stats['total_chunks']}")
        
        if len(stats['corpus_sources']) > 1:
            print(f"\n📁 Corpus Sources:")
            for source, count in sorted(stats['corpus_sources'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / stats['total_chunks']) * 100
                print(f"   {source}: {count} chunks ({percentage:.1f}%)")
        
        print(f"\n🏷️ Semantic Categories:")
        for category, count in sorted(stats['semantic_categories'].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / stats['total_chunks']) * 100
            print(f"   {category}: {count} chunks ({percentage:.1f}%)")
        
        print(f"\n🔗 Combined functionality groups: {stats['combined_functionality_groups']}")
        
        return stats

    def train_classification_model(self):
        """Train classification model using Random Forest."""
        print("🏗️ Training wire processing classification model (standalone)...")
        
        # Get training data
        features_list, labels, metadata_list = self.extractor.create_classification_dataset()
        
        if not features_list:
            print("❌ No training data available")
            return None
        
        # Analyze label distribution
        label_counts = Counter(labels)
        print(f"📊 Label distribution:")
        for label, count in label_counts.most_common():
            print(f"   {label}: {count} examples")
        
        # Prepare text features for TF-IDF
        text_content = [features['content'] for features in features_list]
        
        # Remove content from feature dictionaries (will be handled by TF-IDF)
        numerical_features = []
        for features in features_list:
            num_features = {k: v for k, v in features.items() if k != 'content'}
            numerical_features.append(num_features)
        
        # Convert to arrays
        feature_names = list(numerical_features[0].keys())
        X_numerical = np.array([[features[name] for name in feature_names] 
                               for features in numerical_features])
        
        # Create TF-IDF features
        tfidf = TfidfVectorizer(max_features=500, stop_words='english', 
                               ngram_range=(1, 2), min_df=2, max_df=0.8)
        X_text = tfidf.fit_transform(text_content)
        
        # Combine numerical and text features
        X_combined = np.hstack([X_numerical, X_text.toarray()])
        y = np.array(labels)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"📊 Training set: {len(X_train)} examples")
        print(f"📊 Test set: {len(X_test)} examples")
        
        # Train multiple models and pick the best
        models_to_try = {
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
            'Naive Bayes': MultinomialNB(alpha=0.1)
        }
        
        best_model = None
        best_score = 0
        best_name = ""
        
        for name, model in models_to_try.items():
            print(f"\n🔧 Training {name}...")
            
            try:
                model.fit(X_train, y_train)
                
                # Evaluate
                train_score = model.score(X_train, y_train)
                test_score = model.score(X_test, y_test)
                
                print(f"   Training accuracy: {train_score:.3f}")
                print(f"   Test accuracy: {test_score:.3f}")
                
                if test_score > best_score:
                    best_score = test_score
                    best_model = model
                    best_name = name
                    
            except Exception as e:
                print(f"   ❌ Error training {name}: {e}")
        
        if best_model is None:
            print("❌ No models trained successfully")
            return None
        
        print(f"\n✅ Best model: {best_name} (accuracy: {best_score:.3f})")
        
        # Detailed evaluation of best model
        y_pred = best_model.predict(X_test)
        
        print(f"\n📊 Detailed Classification Report:")
        print(classification_report(y_test, y_pred))
        
        # Feature importance (if available)
        if hasattr(best_model, 'feature_importances_'):
            print(f"\n🔍 Top Features:")
            feature_importance = best_model.feature_importances_
            
            # Combine feature names
            all_feature_names = feature_names + [f"tfidf_{i}" for i in range(X_text.shape[1])]
            
            # Get top features
            top_indices = np.argsort(feature_importance)[-10:][::-1]
            for idx in top_indices:
                if idx < len(all_feature_names):
                    print(f"   {all_feature_names[idx]}: {feature_importance[idx]:.3f}")
        
        # Save model and metadata
        model_data = {
            'model': best_model,
            'tfidf_vectorizer': tfidf,
            'feature_names': feature_names,
            'label_names': list(set(labels)),
            'model_type': best_name,
            'accuracy': best_score
        }
        
        with open('standalone_classification_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Model saved to: standalone_classification_model.pkl")
        
        self.models['classification'] = model_data
        return model_data
    
    def train_understanding_model(self):
        """Train simple understanding model using similarity matching."""
        print("🧠 Training understanding model (rule-based)...")
        
        examples = self.extractor.create_understanding_dataset()
        
        if not examples:
            print("❌ No understanding examples available")
            return None
        
        # Create a simple similarity-based understanding system
        understanding_data = {
            'examples': examples,
            'vectorizer': TfidfVectorizer(max_features=200, stop_words='english')
        }
        
        # Fit vectorizer on code examples
        code_texts = [example[0] for example in examples]
        understanding_data['code_vectors'] = understanding_data['vectorizer'].fit_transform(code_texts)
        
        # Save understanding model
        with open('standalone_understanding_model.pkl', 'wb') as f:
            pickle.dump(understanding_data, f)
        
        print(f"✅ Understanding model saved: standalone_understanding_model.pkl")
        print(f"📊 {len(examples)} code-explanation pairs indexed")
        
        self.models['understanding'] = understanding_data
        return understanding_data
    
    def test_classification_model(self, test_code: str):
        """Test the classification model with sample code."""
        if 'classification' not in self.models:
            try:
                with open('standalone_classification_model.pkl', 'rb') as f:
                    self.models['classification'] = pickle.load(f)
            except FileNotFoundError:
                print("❌ No classification model found. Train first.")
                return None
        
        model_data = self.models['classification']
        model = model_data['model']
        tfidf = model_data['tfidf_vectorizer']
        feature_names = model_data['feature_names']
        label_names = model_data['label_names']
        
        # Create a dummy chunk for feature extraction
        test_chunk = type('TestChunk', (), {})()
        test_chunk.content = test_code
        test_chunk.procedure_name = ""
        test_chunk.keywords = []
        test_chunk.function_calls = []
        test_chunk.word_count = len(test_code.split())
        test_chunk.char_count = len(test_code)
        
        # Extract features
        features = self.extractor.feature_extractor.extract_features(test_chunk)
        
        # Prepare features
        X_numerical = np.array([[features.get(name, 0) for name in feature_names]])
        X_text = tfidf.transform([test_code])
        X_combined = np.hstack([X_numerical, X_text.toarray()])
        
        # Predict
        prediction = model.predict(X_combined)[0]
        probabilities = model.predict_proba(X_combined)[0] if hasattr(model, 'predict_proba') else None
        
        print(f"🎯 Predicted category: {prediction}")
        if probabilities is not None:
            confidence = max(probabilities)
            print(f"🎯 Confidence: {confidence:.3f}")
        
        return prediction
    
    def test_understanding_model(self, test_code: str):
        """Test the understanding model with sample code."""
        if 'understanding' not in self.models:
            try:
                with open('standalone_understanding_model.pkl', 'rb') as f:
                    self.models['understanding'] = pickle.load(f)
            except FileNotFoundError:
                print("❌ No understanding model found. Train first.")
                return None
        
        model_data = self.models['understanding']
        examples = model_data['examples']
        vectorizer = model_data['vectorizer']
        code_vectors = model_data['code_vectors']
        
        # Vectorize test code
        test_vector = vectorizer.transform([test_code])
        
        # Find most similar code
        similarities = cosine_similarity(test_vector, code_vectors)[0]
        best_match_idx = np.argmax(similarities)
        
        if similarities[best_match_idx] > 0.1:  # Minimum similarity threshold
            explanation = examples[best_match_idx][1]
            similarity = similarities[best_match_idx]
            print(f"🧠 Explanation: {explanation}")
            print(f"🎯 Similarity: {similarity:.3f}")
            return explanation
        else:
            print("🧠 No similar code found in training data")
            return "Code analysis: Unable to provide explanation based on training data."

def get_corpus_files():
    """Interactive function to get corpus file paths."""
    print("📚 CORPUS FILE SELECTION")
    print("="*30)
    print("Options:")
    print("1. Single corpus file")
    print("2. Multiple corpus files")
    print("3. All .pkl files in a directory")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        # Single file
        corpus_path = input("📁 Enter corpus file path (.pkl): ").strip()
        if os.path.exists(corpus_path) and corpus_path.endswith('.pkl'):
            return [corpus_path]
        else:
            print(f"❌ File not found or not a .pkl file: {corpus_path}")
            return None
    
    elif choice == "2":
        # Multiple files
        corpus_paths = []
        print("\n📁 Enter corpus file paths (one per line, empty line to finish):")
        while True:
            path = input("Corpus file: ").strip()
            if not path:
                break
            if os.path.exists(path) and path.endswith('.pkl'):
                corpus_paths.append(path)
                print(f"   ✅ Added: {os.path.basename(path)}")
            else:
                print(f"   ❌ File not found or not a .pkl file: {path}")
        
        if corpus_paths:
            return corpus_paths
        else:
            print("❌ No valid corpus files provided")
            return None
    
    elif choice == "3":
        # All .pkl files in directory
        directory = input("📁 Enter directory path: ").strip()
        if not os.path.exists(directory) or not os.path.isdir(directory):
            print(f"❌ Directory not found: {directory}")
            return None
        
        pkl_files = []
        for file in os.listdir(directory):
            if file.endswith('.pkl'):
                full_path = os.path.join(directory, file)
                pkl_files.append(full_path)
        
        if pkl_files:
            print(f"\n📦 Found {len(pkl_files)} .pkl files:")
            for i, file_path in enumerate(pkl_files, 1):
                print(f"   {i}. {os.path.basename(file_path)}")
            
            use_all = input(f"\nUse all {len(pkl_files)} files? (y/n): ").strip().lower()
            if use_all in ['y', 'yes', '']:
                return pkl_files
            else:
                # Let user select specific files
                selected_files = []
                for i, file_path in enumerate(pkl_files, 1):
                    use_file = input(f"Use {os.path.basename(file_path)}? (y/n): ").strip().lower()
                    if use_file in ['y', 'yes']:
                        selected_files.append(file_path)
                
                return selected_files if selected_files else None
        else:
            print(f"❌ No .pkl files found in directory: {directory}")
            return None
    
    else:
        print("❌ Invalid choice")
        return None

def show_example_questions():
    """Show example questions developers can ask."""
    examples = [
        "How do I validate a SWIFT MT103 message?",
        "Create a procedure to process Fedwire transfers",
        "How to screen for OFAC sanctions?",
        "Generate code to handle ISO 20022 PACS.008 messages",
        "Create error handling for validation failures",
        "How do I process CHIPS clearing transactions?",
        "Validate BIC codes in wire transfers",
        "Create a procedure for correspondent banking",
        "How to generate IMAD for Fedwire?",
        "Screen customer data for AML compliance"
    ]
    
    print("\n💡 Example Questions You Can Ask:")
    for i, example in enumerate(examples, 1):
        print(f"   {i}. {example}")

def main():
    """Main function for wire processing AI assistant."""
    print("🤖 WIRE PROCESSING AI ASSISTANT")
    print("="*60)
    print("Powered by your indexed TAL codebase - No external downloads needed!")
    print("🆕 Now supports multiple corpus files!")
    
    if not SKLEARN_AVAILABLE:
        print("❌ Missing dependencies. Install with:")
        print("   pip install scikit-learn numpy")
        return
    
    # Get corpus file(s)
    if len(sys.argv) > 1:
        # Command line arguments - support multiple files
        corpus_paths = []
        for arg in sys.argv[1:]:
            if os.path.exists(arg) and arg.endswith('.pkl'):
                corpus_paths.append(arg)
            else:
                print(f"⚠️  Skipping invalid file: {arg}")
        
        if not corpus_paths:
            print("❌ No valid .pkl files provided in command line")
            corpus_paths = get_corpus_files()
    else:
        # Interactive mode
        corpus_paths = get_corpus_files()
    
    if not corpus_paths:
        print("❌ No corpus files to process")
        return
    
    print(f"\n🚀 Initializing AI assistant with {len(corpus_paths)} corpus file(s)...")
    
    # Initialize trainer with multiple files
    try:
        trainer = StandaloneWireProcessingTrainer(corpus_paths)
        
        # Show combined corpus overview
        trainer.show_corpus_overview()
        
    except Exception as e:
        print(f"❌ Error initializing assistant: {e}")
        return
    
    # Main menu loop
    while True:
        print(f"\n🎯 AI ASSISTANT OPTIONS:")
        print("1. 💬 Ask coding questions & get implementations")
        print("2. Train classification model (Random Forest + TF-IDF)")
        print("3. Train understanding model (Similarity-based)")
        print("4. Train both models")
        print("5. Test existing models with TAL code")
        print("6. Show detailed corpus statistics")
        print("7. Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == "1":
            print("\n🤖 WIRE PROCESSING DEVELOPMENT ASSISTANT")
            print("="*50)
            print("Ask any questions about implementing wire processing code!")
            
            # Initialize code generator with multiple corpus files
            generator = CodeSnippetGenerator(corpus_paths)
            
            print(f"💡 Assistant initialized with {len(corpus_paths)} corpus file(s)")
            show_example_questions()
            
            while True:
                question = input("\n💬 What do you want to implement? (or 'quit' to go back): ").strip()
                
                if question.lower() in ['quit', 'exit', 'q', 'back']:
                    break
                
                if question:
                    try:
                        result = generator.generate_code_snippet(question)
                        
                        print(f"\n{'='*70}")
                        print(f"🎯 IMPLEMENTATION GUIDE & CODE")
                        print(f"{'='*70}")
                        print(f"📝 Question: {result['question']}")
                        print(f"🏷️ Category: {result['category']}")
                        print(f"🎯 Confidence: {result['confidence']:.2f}")
                        print(f"📖 Description: {result['description']}")
                        
                        print(f"\n💻 Generated TAL Code:")
                        print("-" * 50)
                        print(result['generated_code'])
                        print("-" * 50)
                        
                        # Implementation steps
                        if result.get('implementation_steps'):
                            print(f"\n🚀 Implementation Steps:")
                            for step in result['implementation_steps']:
                                print(f"   {step}")
                        
                        # Integration guidance
                        if result.get('integration_notes'):
                            print(f"\n🔗 Integration Notes:")
                            for note in result['integration_notes']:
                                print(f"   {note}")
                        
                        # Testing approach
                        if result.get('testing_approach'):
                            print(f"\n🧪 Testing Approach:")
                            for test in result['testing_approach']:
                                print(f"   {test}")
                        
                        # Related procedures
                        if result.get('related_procedures'):
                            print(f"\n🔧 Related Procedures You May Need:")
                            for proc in result['related_procedures']:
                                print(f"   • {proc}")
                        
                        # General suggestions
                        if result.get('suggestions'):
                            print(f"\n💡 Code Customization Tips:")
                            for i, suggestion in enumerate(result['suggestions'], 1):
                                print(f"   {i}. {suggestion}")
                        
                        # Ask if they want to generate related code
                        print(f"\n" + "="*50)
                        follow_up = input("💬 Need help with any related procedures? (y/n): ").strip().lower()
                        if follow_up in ['y', 'yes']:
                            related_question = input("What specifically do you need help with? ").strip()
                            if related_question:
                                # Generate related code
                                related_result = generator.generate_code_snippet(related_question)
                                print(f"\n🔗 Related Implementation:")
                                print("-" * 30)
                                print(related_result['generated_code'])
                                print("-" * 30)
                        
                    except Exception as e:
                        print(f"❌ Error generating code: {e}")
                        print("Please try rephrasing your question or check the corpus files.")
        
        elif choice == "2":
            print("\n🏗️ Training Classification Model...")
            try:
                model = trainer.train_classification_model()
                if model:
                    print(f"✅ Classification model trained successfully!")
                    print(f"📊 Model type: {model['model_type']}")
                    print(f"🎯 Accuracy: {model['accuracy']:.3f}")
            except Exception as e:
                print(f"❌ Error training classification model: {e}")
        
        elif choice == "3":
            print("\n🧠 Training Understanding Model...")
            try:
                model = trainer.train_understanding_model()
                if model:
                    print(f"✅ Understanding model trained successfully!")
                    print(f"📊 Examples indexed: {len(model['examples'])}")
            except Exception as e:
                print(f"❌ Error training understanding model: {e}")
        
        elif choice == "4":
            print("\n🚀 Training Both Models...")
            try:
                print("Step 1/2: Training classification model...")
                classification_model = trainer.train_classification_model()
                
                print("\nStep 2/2: Training understanding model...")
                understanding_model = trainer.train_understanding_model()
                
                if classification_model and understanding_model:
                    print("\n✅ Both models trained successfully!")
                    print(f"🎯 Classification accuracy: {classification_model['accuracy']:.3f}")
                    print(f"📊 Understanding examples: {len(understanding_model['examples'])}")
                else:
                    print("⚠️ Some models failed to train. Check error messages above.")
            except Exception as e:
                print(f"❌ Error training models: {e}")
        
        elif choice == "5":
            print("\n🧪 TEST TRAINED MODELS")
            print("="*30)
            
            # Get test code from user
            print("Enter TAL code to test (end with empty line):")
            test_lines = []
            while True:
                line = input()
                if not line.strip():
                    break
                test_lines.append(line)
            
            if test_lines:
                test_code = '\n'.join(test_lines)
                
                print(f"\n🔍 Testing with code:")
                print("-" * 30)
                print(test_code)
                print("-" * 30)
                
                # Test classification model
                print(f"\n🎯 Classification Model Results:")
                try:
                    prediction = trainer.test_classification_model(test_code)
                except Exception as e:
                    print(f"❌ Classification test failed: {e}")
                
                # Test understanding model
                print(f"\n🧠 Understanding Model Results:")
                try:
                    explanation = trainer.test_understanding_model(test_code)
                except Exception as e:
                    print(f"❌ Understanding test failed: {e}")
            else:
                print("❌ No test code provided")
        
        elif choice == "6":
            print("\n📊 DETAILED CORPUS STATISTICS")
            print("="*40)
            
            stats = trainer.extractor.get_corpus_statistics()
            
            # Show detailed breakdown
            print(f"\n📁 Corpus Files Loaded:")
            for corpus_info in trainer.extractor.corpus_metadata['combined_corpora']:
                print(f"   📄 {os.path.basename(corpus_info['path'])}")
                print(f"      Version: {corpus_info['version']}")
                print(f"      Created: {corpus_info['created_at']}")
                print(f"      Chunks: {corpus_info['chunk_count']}")
                if corpus_info['stats']:
                    print(f"      Original stats: {corpus_info['stats']}")
                print()
            
            # Show functionality groups
            if trainer.extractor.functionality_groups:
                print(f"🔗 Functionality Groups:")
                for group_name, group_chunks in list(trainer.extractor.functionality_groups.items())[:10]:
                    print(f"   {group_name}: {len(group_chunks)} chunks")
            
            # Show sample procedures
            procedures = [chunk.procedure_name for chunk in trainer.extractor.chunks 
                         if hasattr(chunk, 'procedure_name') and chunk.procedure_name]
            if procedures:
                print(f"\n🔧 Sample Procedures ({len(procedures)} total):")
                for proc in procedures[:15]:
                    print(f"   • {proc}")
                if len(procedures) > 15:
                    print(f"   ... and {len(procedures) - 15} more")
            
            # Show keyword analysis
            all_keywords = []
            for chunk in trainer.extractor.chunks:
                if hasattr(chunk, 'keywords') and chunk.keywords:
                    all_keywords.extend(chunk.keywords)
            
            if all_keywords:
                keyword_counts = Counter(all_keywords)
                print(f"\n🏷️ Top Keywords:")
                for keyword, count in keyword_counts.most_common(20):
                    print(f"   {keyword}: {count}")
        
        elif choice == "7":
            print("\n👋 Goodbye! Thanks for using the Wire Processing AI Assistant!")
            break
        
        else:
            print("❌ Invalid choice. Please select 1-7.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your corpus files and try again.")
