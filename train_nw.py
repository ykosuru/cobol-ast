#!/usr/bin/env python3
"""
Standalone AI Model Trainer for Indexed TAL Code

No external model downloads - uses only scikit-learn and built-in libraries.
Trains lightweight but effective models for wire processing code analysis.
"""

import os
import json
import pickle
import random
import re
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
    
    def __init__(self, corpus_path: str):
        self.corpus_path = corpus_path
        self.chunks = []
        self.vectorizer_data = {}
        self.functionality_groups = {}
        self.feature_extractor = WireProcessingFeatureExtractor()
        self.load_corpus()
    
    def load_corpus(self):
        """Load indexed corpus with error handling."""
        print(f"📚 Loading indexed corpus from: {self.corpus_path}")
        
        # Add SimpleChunk to global namespace for pickle compatibility
        import sys
        globals()['SimpleChunk'] = SimpleChunk
        sys.modules[__name__].SimpleChunk = SimpleChunk
        
        try:
            with open(self.corpus_path, 'rb') as f:
                corpus_data = pickle.load(f)
            
            # Reconstruct chunks with error handling
            for i, chunk_data in enumerate(corpus_data.get('chunks', [])):
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
                    
                    self.chunks.append(chunk)
                    
                except Exception as e:
                    print(f"⚠️  Warning: Error loading chunk {i}: {e}")
                    continue
            
            self.vectorizer_data = corpus_data.get('vectorizer', {})
            self.functionality_groups = corpus_data.get('functionality_groups', {})
            
            print(f"✅ Loaded {len(self.chunks)} chunks with rich metadata")
            
        except Exception as e:
            print(f"❌ Error loading corpus: {e}")
            raise
    
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

class StandaloneWireProcessingTrainer:
    """Train models using only scikit-learn - no external downloads."""
    
    def __init__(self, corpus_path: str):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required. Install with: pip install scikit-learn numpy")
        
        self.extractor = StandaloneCorpusDataExtractor(corpus_path)
        self.models = {}
        self.vectorizers = {}
    
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
        from sklearn.metrics.pairwise import cosine_similarity
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

def main():
    """Main function for standalone training."""
    print("🤖 STANDALONE AI TRAINER (No External Downloads)")
    print("="*60)
    print("Uses only scikit-learn - no Hugging Face or external models")
    
    if not SKLEARN_AVAILABLE:
        print("❌ Missing dependencies. Install with:")
        print("   pip install scikit-learn numpy")
        return
    
    # Get corpus path
    corpus_path = input("📚 Enter path to indexed corpus (.pkl): ").strip()
    
    if not os.path.exists(corpus_path):
        print(f"❌ Corpus not found: {corpus_path}")
        return
    
    # Initialize trainer
    trainer = StandaloneWireProcessingTrainer(corpus_path)
    
    # Training options
    print(f"\n🎯 Standalone Training Options:")
    print("1. Train classification model (Random Forest + TF-IDF)")
    print("2. Train understanding model (Similarity-based)")
    print("3. Train both models")
    print("4. Test existing models")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        model = trainer.train_classification_model()
        if model:
            print("\n🧪 Testing with sample code...")
            test_code = """
PROC VALIDATE_SWIFT_MT103(message);
BEGIN
    CALL EXTRACT_BIC_CODE(message, bic_field);
    IF NOT VALIDATE_BIC_FORMAT(bic_field) THEN
        RETURN 0;
    END;
END;
"""
            trainer.test_classification_model(test_code)
    
    elif choice == "2":
        model = trainer.train_understanding_model()
        if model:
            print("\n🧪 Testing understanding...")
            test_code = """
PROC VALIDATE_SWIFT_MT103(message);
BEGIN
    CALL EXTRACT_BIC_CODE(message, bic_field);
END;
"""
            trainer.test_understanding_model(test_code)
    
    elif choice == "3":
        print("🚀 Training both models...")
        trainer.train_classification_model()
        trainer.train_understanding_model()
        print("✅ Both models trained!")
    
    elif choice == "4":
        print("🧪 Testing existing models...")
        test_code = input("Enter TAL code to test: ").strip()
        if test_code:
            print("\n🏷️ Classification test:")
            trainer.test_classification_model(test_code)
            print("\n🧠 Understanding test:")
            trainer.test_understanding_model(test_code)
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
