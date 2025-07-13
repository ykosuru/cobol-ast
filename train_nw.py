#!/usr/bin/env python3
"""
AI Model Trainer for Indexed TAL Wire Processing Code

Trains multiple AI models using your indexed corpus for:
1. Code understanding and explanation
2. Semantic search improvement
3. Wire processing classification
4. Code generation assistance
"""

import os
import json
import pickle
import random
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import pandas as pd

# ML/AI imports
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    from transformers import (
        AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
        T5ForConditionalGeneration, T5Tokenizer,
        TrainingArguments, Trainer
    )
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  Install transformers: pip install torch transformers scikit-learn")

@dataclass
class TrainingExample:
    """Training example for various model types."""
    input_text: str
    target_text: str
    metadata: Dict[str, Any]
    task_type: str  # 'classification', 'generation', 'understanding'

class TALCorpusDataExtractor:
    """Extract training data from your indexed corpus."""
    
    def __init__(self, corpus_path: str):
        self.corpus_path = corpus_path
        self.chunks = []
        self.vectorizer_data = {}
        self.functionality_groups = {}
        self.load_corpus()
    
    def load_corpus(self):
        """Load your indexed corpus."""
        print(f"📚 Loading indexed corpus from: {self.corpus_path}")
        
        with open(self.corpus_path, 'rb') as f:
            corpus_data = pickle.load(f)
        
        # Reconstruct chunks (simplified)
        for chunk_data in corpus_data['chunks']:
            chunk = type('Chunk', (), {})()
            for key, value in chunk_data.items():
                setattr(chunk, key, value)
            self.chunks.append(chunk)
        
        self.vectorizer_data = corpus_data.get('vectorizer', {})
        self.functionality_groups = corpus_data.get('functionality_groups', {})
        
        print(f"✅ Loaded {len(self.chunks)} chunks with rich metadata")
    
    def create_classification_dataset(self) -> List[TrainingExample]:
        """Create dataset for wire processing classification."""
        examples = []
        
        for chunk in self.chunks:
            if hasattr(chunk, 'semantic_category') and chunk.semantic_category:
                # Clean and prepare code text
                code_text = self.clean_code_for_training(chunk.content)
                
                # Add context from metadata
                context = f"Procedure: {chunk.procedure_name or 'None'}\n"
                if hasattr(chunk, 'keywords'):
                    context += f"Keywords: {', '.join(chunk.keywords[:5])}\n"
                if hasattr(chunk, 'function_calls'):
                    context += f"Functions: {', '.join(chunk.function_calls[:3])}\n"
                
                input_text = context + "Code:\n" + code_text
                
                example = TrainingExample(
                    input_text=input_text,
                    target_text=chunk.semantic_category,
                    metadata={
                        'file': chunk.source_file,
                        'procedure': chunk.procedure_name,
                        'topic_prob': getattr(chunk, 'dominant_topic_prob', 0.0)
                    },
                    task_type='classification'
                )
                examples.append(example)
        
        print(f"📊 Created {len(examples)} classification examples")
        return examples
    
    def create_understanding_dataset(self) -> List[TrainingExample]:
        """Create dataset for code understanding (code -> explanation)."""
        examples = []
        
        for chunk in self.chunks:
            if (hasattr(chunk, 'keywords') and chunk.keywords and 
                hasattr(chunk, 'semantic_category')):
                
                code_text = self.clean_code_for_training(chunk.content)
                
                # Generate explanation from metadata
                explanation = self.generate_code_explanation(chunk)
                
                example = TrainingExample(
                    input_text=f"Explain this TAL wire processing code:\n{code_text}",
                    target_text=explanation,
                    metadata={
                        'category': chunk.semantic_category,
                        'complexity': len(chunk.content.split('\n'))
                    },
                    task_type='understanding'
                )
                examples.append(example)
        
        print(f"🧠 Created {len(examples)} understanding examples")
        return examples
    
    def create_search_improvement_dataset(self) -> List[TrainingExample]:
        """Create dataset for improving semantic search."""
        examples = []
        
        # Group chunks by semantic category
        category_groups = {}
        for chunk in self.chunks:
            if hasattr(chunk, 'semantic_category'):
                category = chunk.semantic_category
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(chunk)
        
        # Create search query -> relevant code examples
        for category, chunks in category_groups.items():
            if len(chunks) >= 3:  # Need multiple examples
                
                # Generate queries for this category
                queries = self.generate_category_queries(category, chunks[0])
                
                for query in queries:
                    # Pick a relevant chunk
                    relevant_chunk = random.choice(chunks)
                    code_text = self.clean_code_for_training(relevant_chunk.content)
                    
                    example = TrainingExample(
                        input_text=f"Query: {query}\nCode: {code_text}",
                        target_text="relevant",  # Binary relevance
                        metadata={
                            'query': query,
                            'category': category,
                            'procedure': relevant_chunk.procedure_name
                        },
                        task_type='search'
                    )
                    examples.append(example)
        
        print(f"🔍 Created {len(examples)} search improvement examples")
        return examples
    
    def create_code_generation_dataset(self) -> List[TrainingExample]:
        """Create dataset for code generation."""
        examples = []
        
        for chunk in self.chunks:
            if (chunk.procedure_name and 
                hasattr(chunk, 'semantic_category') and
                len(chunk.content.split('\n')) < 50):  # Focus on smaller, clearer procedures
                
                # Generate requirement from procedure name and category
                requirement = self.generate_requirement_from_procedure(chunk)
                code_text = self.clean_code_for_training(chunk.content)
                
                example = TrainingExample(
                    input_text=f"Generate TAL code for: {requirement}",
                    target_text=code_text,
                    metadata={
                        'category': chunk.semantic_category,
                        'original_procedure': chunk.procedure_name
                    },
                    task_type='generation'
                )
                examples.append(example)
        
        print(f"⚡ Created {len(examples)} generation examples")
        return examples
    
    def clean_code_for_training(self, code: str) -> str:
        """Clean code for training (remove comments, normalize whitespace)."""
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove full-line comments
            stripped = line.strip()
            if stripped and not stripped.startswith('!') and not stripped.startswith('//'):
                # Remove inline comments
                if '!' in line:
                    line = line[:line.index('!')].rstrip()
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def generate_code_explanation(self, chunk) -> str:
        """Generate explanation from chunk metadata."""
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
        
        # Add procedure-specific info
        if chunk.procedure_name:
            explanation_parts.append(f"The procedure '{chunk.procedure_name}' ")
            
            # Infer purpose from name
            name_lower = chunk.procedure_name.lower()
            if 'validate' in name_lower:
                explanation_parts.append("validates input data and formats")
            elif 'process' in name_lower:
                explanation_parts.append("processes payment transactions")
            elif 'screen' in name_lower:
                explanation_parts.append("screens transactions for compliance")
            elif 'send' in name_lower or 'transmit' in name_lower:
                explanation_parts.append("transmits payment messages")
        
        # Add technical details
        if hasattr(chunk, 'function_calls') and chunk.function_calls:
            key_functions = [f for f in chunk.function_calls[:3] if len(f) > 3]
            if key_functions:
                explanation_parts.append(f"It calls functions like {', '.join(key_functions)}")
        
        # Add keywords context
        if hasattr(chunk, 'keywords') and chunk.keywords:
            wire_keywords = [k for k in chunk.keywords if k.lower() in 
                           {'wire', 'payment', 'swift', 'fedwire', 'chips', 'iso20022', 
                            'pacs', 'mt103', 'ofac', 'sanctions', 'aml'}]
            if wire_keywords:
                explanation_parts.append(f"Key concepts include: {', '.join(wire_keywords[:3])}")
        
        return '. '.join(explanation_parts) + '.'
    
    def generate_category_queries(self, category: str, sample_chunk) -> List[str]:
        """Generate search queries for a semantic category."""
        category_queries = {
            'iso20022_messages': [
                'ISO 20022 message processing',
                'pacs.008 credit transfer',
                'pain.001 payment initiation',
                'XML message validation'
            ],
            'swift_processing': [
                'SWIFT MT103 processing',
                'MT202 bank transfer',
                'SWIFT gpi tracking',
                'BIC validation'
            ],
            'fedwire_operations': [
                'Fedwire funds transfer',
                'IMAD generation',
                'Federal Reserve wire',
                'type code processing'
            ],
            'compliance_screening': [
                'OFAC sanctions screening',
                'AML compliance check',
                'KYC validation',
                'watchlist screening'
            ]
        }
        
        queries = category_queries.get(category, [f"{category.replace('_', ' ')} processing"])
        
        # Add procedure-specific queries
        if sample_chunk.procedure_name:
            proc_words = sample_chunk.procedure_name.lower().replace('_', ' ')
            queries.append(proc_words)
        
        return queries[:3]  # Limit to 3 queries per category
    
    def generate_requirement_from_procedure(self, chunk) -> str:
        """Generate a requirement description from procedure metadata."""
        proc_name = chunk.procedure_name.lower()
        category = getattr(chunk, 'semantic_category', '')
        
        # Map procedure patterns to requirements
        if 'validate' in proc_name:
            if 'swift' in proc_name or 'mt103' in proc_name:
                return "Validate SWIFT MT103 message format and required fields"
            elif 'iso' in proc_name or 'pacs' in proc_name:
                return "Validate ISO 20022 payment message structure"
            else:
                return "Validate payment message format and content"
        
        elif 'process' in proc_name:
            if 'fedwire' in proc_name:
                return "Process Fedwire funds transfer request"
            elif 'chips' in proc_name:
                return "Process CHIPS clearing and settlement"
            else:
                return "Process payment transaction"
        
        elif 'screen' in proc_name:
            return "Screen payment for OFAC sanctions and AML compliance"
        
        elif 'send' in proc_name or 'transmit' in proc_name:
            return "Send payment message to destination system"
        
        else:
            # Fallback: use category
            category_requirements = {
                'iso20022_messages': "Handle ISO 20022 message processing",
                'swift_processing': "Process SWIFT message",
                'fedwire_operations': "Execute Fedwire operation",
                'compliance_screening': "Perform compliance screening"
            }
            return category_requirements.get(category, f"Implement {proc_name.replace('_', ' ')}")

class WireProcessingModelTrainer:
    """Train various AI models on your indexed data."""
    
    def __init__(self, corpus_path: str):
        self.extractor = TALCorpusDataExtractor(corpus_path)
        self.models = {}
        
    def train_classification_model(self):
        """Train a model to classify wire processing code."""
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers not available")
            return None
        
        print("🏗️ Training wire processing classification model...")
        
        # Get training data
        examples = self.extractor.create_classification_dataset()
        
        # Get unique categories
        categories = list(set(ex.target_text for ex in examples))
        category_to_id = {cat: idx for idx, cat in enumerate(categories)}
        
        # Prepare data
        texts = [ex.input_text for ex in examples]
        labels = [category_to_id[ex.target_text] for ex in examples]
        
        # Split data
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        # Initialize model
        model_name = "microsoft/codebert-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, 
            num_labels=len(categories)
        )
        
        # Create dataset
        class ClassificationDataset(Dataset):
            def __init__(self, texts, labels, tokenizer, max_length=512):
                self.texts = texts
                self.labels = labels
                self.tokenizer = tokenizer
                self.max_length = max_length
            
            def __len__(self):
                return len(self.texts)
            
            def __getitem__(self, idx):
                encoding = self.tokenizer(
                    self.texts[idx],
                    truncation=True,
                    padding='max_length',
                    max_length=self.max_length,
                    return_tensors='pt'
                )
                return {
                    'input_ids': encoding['input_ids'].flatten(),
                    'attention_mask': encoding['attention_mask'].flatten(),
                    'labels': torch.tensor(self.labels[idx], dtype=torch.long)
                }
        
        train_dataset = ClassificationDataset(train_texts, train_labels, tokenizer)
        val_dataset = ClassificationDataset(val_texts, val_labels, tokenizer)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir='./wire_classification_model',
            num_train_epochs=3,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir='./logs',
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
        )
        
        # Train
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer,
        )
        
        trainer.train()
        
        # Save model
        model.save_pretrained('./wire_classification_model')
        tokenizer.save_pretrained('./wire_classification_model')
        
        # Save category mapping
        with open('./wire_classification_model/categories.json', 'w') as f:
            json.dump(categories, f)
        
        print("✅ Classification model trained and saved!")
        return model, tokenizer, categories
    
    def train_understanding_model(self):
        """Train a model to explain TAL code."""
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers not available")
            return None
        
        print("🧠 Training code understanding model...")
        
        examples = self.extractor.create_understanding_dataset()
        
        # Use T5 for text generation
        model_name = "t5-small"
        tokenizer = T5Tokenizer.from_pretrained(model_name)
        model = T5ForConditionalGeneration.from_pretrained(model_name)
        
        # Prepare data
        inputs = [ex.input_text for ex in examples]
        targets = [ex.target_text for ex in examples]
        
        train_inputs, val_inputs, train_targets, val_targets = train_test_split(
            inputs, targets, test_size=0.2, random_state=42
        )
        
        class UnderstandingDataset(Dataset):
            def __init__(self, inputs, targets, tokenizer, max_length=512):
                self.inputs = inputs
                self.targets = targets
                self.tokenizer = tokenizer
                self.max_length = max_length
            
            def __len__(self):
                return len(self.inputs)
            
            def __getitem__(self, idx):
                input_encoding = self.tokenizer(
                    self.inputs[idx],
                    truncation=True,
                    padding='max_length',
                    max_length=self.max_length,
                    return_tensors='pt'
                )
                
                target_encoding = self.tokenizer(
                    self.targets[idx],
                    truncation=True,
                    padding='max_length',
                    max_length=128,
                    return_tensors='pt'
                )
                
                return {
                    'input_ids': input_encoding['input_ids'].flatten(),
                    'attention_mask': input_encoding['attention_mask'].flatten(),
                    'labels': target_encoding['input_ids'].flatten()
                }
        
        train_dataset = UnderstandingDataset(train_inputs, train_targets, tokenizer)
        val_dataset = UnderstandingDataset(val_inputs, val_targets, tokenizer)
        
        # Training
        training_args = TrainingArguments(
            output_dir='./wire_understanding_model',
            num_train_epochs=3,
            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir='./logs',
            evaluation_strategy="epoch",
            save_strategy="epoch",
        )
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer,
        )
        
        trainer.train()
        
        model.save_pretrained('./wire_understanding_model')
        tokenizer.save_pretrained('./wire_understanding_model')
        
        print("✅ Understanding model trained and saved!")
        return model, tokenizer
    
    def generate_training_report(self):
        """Generate a comprehensive training report."""
        print("\n📊 TRAINING DATA ANALYSIS")
        print("="*50)
        
        # Classification data
        class_examples = self.extractor.create_classification_dataset()
        categories = {}
        for ex in class_examples:
            cat = ex.target_text
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"🏷️ Classification Examples: {len(class_examples)}")
        print("   Categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"     {cat}: {count} examples")
        
        # Understanding data
        understand_examples = self.extractor.create_understanding_dataset()
        print(f"\n🧠 Understanding Examples: {len(understand_examples)}")
        
        # Search data
        search_examples = self.extractor.create_search_improvement_dataset()
        print(f"🔍 Search Improvement Examples: {len(search_examples)}")
        
        # Generation data
        gen_examples = self.extractor.create_code_generation_dataset()
        print(f"⚡ Code Generation Examples: {len(gen_examples)}")
        
        print(f"\n✅ Total Training Examples: {len(class_examples) + len(understand_examples) + len(search_examples) + len(gen_examples)}")

def main():
    """Main training function."""
    print("🤖 AI MODEL TRAINER FOR INDEXED TAL CODE")
    print("="*60)
    
    if not TRANSFORMERS_AVAILABLE:
        print("❌ Missing dependencies. Install with:")
        print("   pip install torch transformers scikit-learn")
        return
    
    # Get corpus path
    corpus_path = input("📚 Enter path to indexed corpus (.pkl): ").strip()
    
    if not os.path.exists(corpus_path):
        print(f"❌ Corpus not found: {corpus_path}")
        return
    
    # Initialize trainer
    trainer = WireProcessingModelTrainer(corpus_path)
    
    # Generate report
    trainer.generate_training_report()
    
    # Training options
    print(f"\n🎯 Training Options:")
    print("1. Train classification model (categorize code by wire processing type)")
    print("2. Train understanding model (explain what code does)")
    print("3. Train both models")
    print("4. Just analyze training data")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        trainer.train_classification_model()
    elif choice == "2":
        trainer.train_understanding_model()
    elif choice == "3":
        print("🚀 Training both models...")
        trainer.train_classification_model()
        trainer.train_understanding_model()
    elif choice == "4":
        print("📊 Training data analysis complete!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
