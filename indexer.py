#!/usr/bin/env python3
"""
TAL Source Code Indexer

This module creates semantic indexes of TAL source code files
for later analysis and search operations.
"""

import os
import re
import json
import pickle
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


@dataclass
class CodeFragment:
    """Represents a fragment of TAL code with metadata."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    function_name: Optional[str] = None
    procedure_name: Optional[str] = None
    comments: List[str] = None
    variables: List[str] = None
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
        if self.variables is None:
            self.variables = []


class TALParser:
    """Parser for TAL source code to extract semantic components."""
    
    def __init__(self):
        # TAL keywords and patterns
        self.tal_keywords = {
            'BEGIN', 'END', 'PROC', 'SUBPROC', 'FORWARD', 'EXTERNAL',
            'IF', 'THEN', 'ELSE', 'CASE', 'OF', 'OTHERWISE',
            'FOR', 'WHILE', 'DO', 'UNTIL', 'REPEAT',
            'CALL', 'RETURN', 'EXIT', 'STOP',
            'INT', 'REAL', 'STRING', 'STRUCT', 'ARRAY',
            'DEFINE', 'LITERAL', 'TEMPLATE'
        }
        
        # Regex patterns for TAL constructs
        self.patterns = {
            'procedure': re.compile(r'^\s*(?:PROC|SUBPROC)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'function': re.compile(r'^\s*(\w+)\s*\([^)]*\)\s*;', re.IGNORECASE | re.MULTILINE),
            'comment': re.compile(r'!\s*(.*)$', re.MULTILINE),
            'variable': re.compile(r'^\s*(?:INT|REAL|STRING|STRUCT)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'define': re.compile(r'^\s*\?DEFINE\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'literal': re.compile(r'^\s*LITERAL\s+(\w+)', re.IGNORECASE | re.MULTILINE)
        }
    
    def parse_file(self, file_path: str) -> List[CodeFragment]:
        """Parse a TAL file and extract code fragments."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        fragments = []
        
        # Split content into logical blocks (procedures, functions, etc.)
        blocks = self._split_into_blocks(content)
        
        for block in blocks:
            fragment = self._create_fragment(file_path, block, content)
            if fragment:
                fragments.append(fragment)
        
        return fragments
    
    def _split_into_blocks(self, content: str) -> List[Dict]:
        """Split content into logical code blocks."""
        lines = content.split('\n')
        blocks = []
        current_block = []
        block_start = 0
        in_proc = False
        proc_depth = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip().upper()
            
            # Track procedure/function boundaries
            if line_stripped.startswith('PROC ') or line_stripped.startswith('SUBPROC '):
                if current_block:
                    blocks.append({
                        'content': '\n'.join(current_block),
                        'start_line': block_start,
                        'end_line': i - 1
                    })
                current_block = [line]
                block_start = i
                in_proc = True
                proc_depth = 1
            elif in_proc:
                current_block.append(line)
                if line_stripped.startswith('BEGIN'):
                    proc_depth += 1
                elif line_stripped.startswith('END'):
                    proc_depth -= 1
                    if proc_depth == 0:
                        blocks.append({
                            'content': '\n'.join(current_block),
                            'start_line': block_start,
                            'end_line': i
                        })
                        current_block = []
                        in_proc = False
            else:
                current_block.append(line)
        
        # Handle remaining content
        if current_block:
            blocks.append({
                'content': '\n'.join(current_block),
                'start_line': block_start,
                'end_line': len(lines) - 1
            })
        
        return blocks
    
    def _create_fragment(self, file_path: str, block: Dict, full_content: str) -> Optional[CodeFragment]:
        """Create a CodeFragment from a code block."""
        content = block['content']
        if not content.strip():
            return None
        
        # Extract semantic information
        procedures = self.patterns['procedure'].findall(content)
        functions = self.patterns['function'].findall(content)
        comments = self.patterns['comment'].findall(content)
        variables = self.patterns['variable'].findall(content)
        defines = self.patterns['define'].findall(content)
        literals = self.patterns['literal'].findall(content)
        
        # Combine all identifiers
        all_vars = variables + defines + literals
        
        return CodeFragment(
            file_path=file_path,
            start_line=block['start_line'],
            end_line=block['end_line'],
            content=content,
            procedure_name=procedures[0] if procedures else None,
            function_name=functions[0] if functions else None,
            comments=comments,
            variables=all_vars
        )


class SemanticIndexer:
    """Creates and manages semantic index of TAL code."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize the semantic indexer."""
        print(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.parser = TALParser()
        self.fragments: List[CodeFragment] = []
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3),
            lowercase=True
        )
        self.tfidf_matrix = None
        self.embeddings = None
        self.index_metadata = {
            'created_at': None,
            'model_name': model_name,
            'total_files': 0,
            'total_fragments': 0,
            'file_extensions': []
        }
    
    def index_directory(self, directory_path: str, file_extensions: List[str] = None) -> None:
        """Index all TAL files in a directory."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h']  # Common TAL extensions
        
        tal_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    tal_files.append(os.path.join(root, file))
        
        print(f"Found {len(tal_files)} TAL files to index...")
        
        self.fragments = []  # Reset fragments
        
        for file_path in tal_files:
            print(f"Indexing: {file_path}")
            file_fragments = self.parser.parse_file(file_path)
            self.fragments.extend(file_fragments)
        
        print(f"Extracted {len(self.fragments)} code fragments")
        
        # Update metadata
        import datetime
        self.index_metadata.update({
            'created_at': datetime.datetime.now().isoformat(),
            'total_files': len(tal_files),
            'total_fragments': len(self.fragments),
            'file_extensions': file_extensions
        })
        
        self._create_embeddings()
    
    def index_file(self, file_path: str) -> None:
        """Index a single TAL file."""
        print(f"Indexing single file: {file_path}")
        fragments = self.parser.parse_file(file_path)
        self.fragments.extend(fragments)
        
        # Update metadata
        self.index_metadata['total_fragments'] = len(self.fragments)
        
        self._create_embeddings()
    
    def _create_embeddings(self) -> None:
        """Create embeddings for all code fragments."""
        if not self.fragments:
            print("No fragments to create embeddings for")
            return
        
        print("Creating semantic embeddings...")
        
        # Prepare text for embedding
        texts = []
        for fragment in self.fragments:
            # Combine code content with comments and identifiers
            text_parts = [fragment.content]
            if fragment.comments:
                text_parts.extend(fragment.comments)
            if fragment.procedure_name:
                text_parts.append(fragment.procedure_name)
            if fragment.function_name:
                text_parts.append(fragment.function_name)
            if fragment.variables:
                text_parts.extend(fragment.variables)
            
            combined_text = ' '.join(text_parts)
            texts.append(combined_text)
        
        # Create sentence embeddings
        print("Generating sentence embeddings...")
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Create TF-IDF matrix for keyword-based similarity
        print("Creating TF-IDF matrix...")
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        
        # Store embeddings in fragments
        for i, fragment in enumerate(self.fragments):
            fragment.embedding = self.embeddings[i]
        
        print("Index creation complete!")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        if not self.fragments:
            return {"status": "empty"}
        
        # Count by file type
        file_types = {}
        procedure_count = 0
        function_count = 0
        
        for fragment in self.fragments:
            ext = Path(fragment.file_path).suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
            
            if fragment.procedure_name:
                procedure_count += 1
            if fragment.function_name:
                function_count += 1
        
        return {
            "total_fragments": len(self.fragments),
            "total_files": self.index_metadata.get('total_files', 0),
            "file_types": file_types,
            "procedures_found": procedure_count,
            "functions_found": function_count,
            "embedding_dimensions": self.embeddings.shape[1] if self.embeddings is not None else 0,
            "created_at": self.index_metadata.get('created_at'),
            "model_name": self.index_metadata.get('model_name')
        }
    
    def save_index(self, file_path: str) -> None:
        """Save the index to disk."""
        index_data = {
            'fragments': self.fragments,
            'embeddings': self.embeddings,
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'tfidf_matrix': self.tfidf_matrix,
            'metadata': self.index_metadata
        }
        
        print(f"Saving index with {len(self.fragments)} fragments...")
        with open(file_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"Index saved to {file_path}")
        
        # Save readable statistics
        stats_file = file_path.replace('.pkl', '_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(self.get_statistics(), f, indent=2)
        print(f"Index statistics saved to {stats_file}")
    
    def load_index(self, file_path: str) -> None:
        """Load the index from disk."""
        print(f"Loading index from {file_path}...")
        
        with open(file_path, 'rb') as f:
            index_data = pickle.load(f)
        
        self.fragments = index_data['fragments']
        self.embeddings = index_data['embeddings']
        self.tfidf_vectorizer = index_data['tfidf_vectorizer']
        self.tfidf_matrix = index_data['tfidf_matrix']
        self.index_metadata = index_data.get('metadata', {})
        
        print(f"Index loaded successfully!")
        
        # Print statistics
        stats = self.get_statistics()
        print(f"- Total fragments: {stats['total_fragments']}")
        print(f"- Total files: {stats['total_files']}")
        print(f"- Procedures: {stats['procedures_found']}")
        print(f"- Functions: {stats['functions_found']}")
        print(f"- Created: {stats['created_at']}")


def main():
    """Main indexer application."""
    
    print("="*60)
    print("TAL CODE SEMANTIC INDEXER")
    print("="*60)
    
    # Initialize indexer
    model_choice = input("Enter model name (default: all-MiniLM-L6-v2): ").strip()
    if not model_choice:
        model_choice = 'all-MiniLM-L6-v2'
    
    indexer = SemanticIndexer(model_name=model_choice)
    
    while True:
        print("\nChoose an option:")
        print("1. Index a directory of TAL files")
        print("2. Index a single TAL file")
        print("3. Load existing index")
        print("4. View index statistics")
        print("5. Save current index")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            # Index directory
            tal_directory = input("Enter path to TAL source directory: ").strip()
            
            if os.path.exists(tal_directory):
                # Get file extensions
                extensions_input = input("Enter file extensions (comma-separated, default: .tal,.TAL,.c,.h): ").strip()
                if extensions_input:
                    extensions = [ext.strip() for ext in extensions_input.split(',')]
                else:
                    extensions = ['.tal', '.TAL', '.c', '.h']
                
                indexer.index_directory(tal_directory, extensions)
                
                # Automatically save
                default_index_file = "tal_semantic_index.pkl"
                save_choice = input(f"Save index to {default_index_file}? (y/n): ").strip().lower()
                if save_choice in ['y', 'yes', '']:
                    indexer.save_index(default_index_file)
            else:
                print(f"Directory not found: {tal_directory}")
        
        elif choice == "2":
            # Index single file
            file_path = input("Enter path to TAL file: ").strip()
            
            if os.path.exists(file_path):
                indexer.index_file(file_path)
            else:
                print(f"File not found: {file_path}")
        
        elif choice == "3":
            # Load existing index
            index_file = input("Enter path to index file (default: tal_semantic_index.pkl): ").strip()
            if not index_file:
                index_file = "tal_semantic_index.pkl"
            
            if os.path.exists(index_file):
                indexer.load_index(index_file)
            else:
                print(f"Index file not found: {index_file}")
        
        elif choice == "4":
            # View statistics
            stats = indexer.get_statistics()
            
            if stats.get("status") == "empty":
                print("No index loaded or created yet.")
            else:
                print("\n" + "="*40)
                print("INDEX STATISTICS")
                print("="*40)
                print(f"Total fragments: {stats['total_fragments']}")
                print(f"Total files: {stats['total_files']}")
                print(f"Procedures found: {stats['procedures_found']}")
                print(f"Functions found: {stats['functions_found']}")
                print(f"Embedding dimensions: {stats['embedding_dimensions']}")
                print(f"Model used: {stats['model_name']}")
                print(f"Created at: {stats['created_at']}")
                
                if stats['file_types']:
                    print("\nFile types indexed:")
                    for ext, count in stats['file_types'].items():
                        print(f"  {ext}: {count} files")
        
        elif choice == "5":
            # Save index
            if not indexer.fragments:
                print("No index to save. Create an index first.")
                continue
            
            save_path = input("Enter save path (default: tal_semantic_index.pkl): ").strip()
            if not save_path:
                save_path = "tal_semantic_index.pkl"
            
            indexer.save_index(save_path)
        
        elif choice == "6":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1-6.")


if __name__ == "__main__":
    # Install required packages if not already installed
    import subprocess
    import sys
    
    required_packages = [
        "sentence-transformers",
        "scikit-learn",
        "numpy"
    ]
    
    print("Checking required packages...")
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    main()
