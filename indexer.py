#!/usr/bin/env python3
"""
Simple TAL Source Code Indexer - Standalone Version

This is a simplified, standalone version that avoids import issues.
Run this to index TAL files and save to local directory.
"""

import os
import re
import json
import pickle
import sys
from pathlib import Path

# Check and install required packages
def check_packages():
    required = ['scikit-learn', 'numpy']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        import subprocess
        for pkg in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

check_packages()

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class CodeFragment:
    """Represents a fragment of TAL code with metadata."""
    def __init__(self, file_path, start_line, end_line, content, 
                 procedure_name=None, function_name=None, comments=None, variables=None):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.procedure_name = procedure_name
        self.function_name = function_name
        self.comments = comments or []
        self.variables = variables or []

class TALParser:
    """Parser for TAL source code to extract semantic components."""
    
    def __init__(self):
        # Regex patterns for TAL constructs
        self.patterns = {
            'procedure': re.compile(r'^\s*(?:PROC|SUBPROC)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'function': re.compile(r'^\s*(\w+)\s*\([^)]*\)\s*;', re.IGNORECASE | re.MULTILINE),
            'comment': re.compile(r'!\s*(.*)$', re.MULTILINE),
            'variable': re.compile(r'^\s*(?:INT|REAL|STRING|STRUCT)\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'define': re.compile(r'^\s*\?DEFINE\s+(\w+)', re.IGNORECASE | re.MULTILINE),
            'literal': re.compile(r'^\s*LITERAL\s+(\w+)', re.IGNORECASE | re.MULTILINE)
        }
    
    def parse_file(self, file_path):
        """Parse a TAL file and extract code fragments."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
        
        fragments = []
        blocks = self._split_into_blocks(content)
        
        for block in blocks:
            fragment = self._create_fragment(file_path, block)
            if fragment:
                fragments.append(fragment)
        
        return fragments
    
    def _split_into_blocks(self, content):
        """Split content into logical code blocks."""
        lines = content.split('\n')
        blocks = []
        current_block = []
        block_start = 0
        in_proc = False
        proc_depth = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip().upper()
            
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
        
        if current_block:
            blocks.append({
                'content': '\n'.join(current_block),
                'start_line': block_start,
                'end_line': len(lines) - 1
            })
        
        return blocks
    
    def _create_fragment(self, file_path, block):
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

class SimpleTALIndexer:
    """Simple TAL code indexer using TF-IDF only."""
    
    def __init__(self):
        self.parser = TALParser()
        self.fragments = []
        
        # Enhanced TF-IDF for code
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 4),
            lowercase=True,
            min_df=1,
            max_df=0.95,
            sublinear_tf=True
        )
        
        self.code_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            lowercase=False,
            token_pattern=r'\b[A-Za-z_][A-Za-z0-9_]*\b',
            min_df=1
        )
        
        self.tfidf_matrix = None
        self.code_matrix = None
        self.metadata = {}
    
    def index_directory(self, directory_path, file_extensions=None):
        """Index all TAL files in a directory."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h']
        
        tal_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    tal_files.append(os.path.join(root, file))
        
        if not tal_files:
            raise Exception(f"No TAL files found in {directory_path}")
        
        print(f"Found {len(tal_files)} TAL files to index...")
        
        self.fragments = []
        for file_path in tal_files:
            print(f"Indexing: {file_path}")
            file_fragments = self.parser.parse_file(file_path)
            self.fragments.extend(file_fragments)
        
        print(f"Extracted {len(self.fragments)} code fragments")
        
        # Update metadata
        import datetime
        self.metadata = {
            'created_at': datetime.datetime.now().isoformat(),
            'total_files': len(tal_files),
            'total_fragments': len(self.fragments),
            'file_extensions': file_extensions,
            'model_name': 'tfidf-only'
        }
        
        self._create_representations()
    
    def _create_representations(self):
        """Create TF-IDF representations for all code fragments."""
        if not self.fragments:
            return
        
        print("Creating TF-IDF representations...")
        
        texts = []
        code_texts = []
        
        for fragment in self.fragments:
            # General text (content + comments + identifiers)
            text_parts = [fragment.content]
            text_parts.extend(fragment.comments)
            if fragment.procedure_name:
                text_parts.append(fragment.procedure_name)
            if fragment.function_name:
                text_parts.append(fragment.function_name)
            text_parts.extend(fragment.variables)
            
            texts.append(' '.join(text_parts))
            
            # Code-specific (identifiers only)
            code_parts = []
            if fragment.procedure_name:
                code_parts.append(fragment.procedure_name)
            if fragment.function_name:
                code_parts.append(fragment.function_name)
            code_parts.extend(fragment.variables)
            
            # Extract identifiers from content
            identifiers = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', fragment.content)
            code_parts.extend(identifiers)
            
            code_texts.append(' '.join(code_parts))
        
        # Create matrices
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        self.code_matrix = self.code_vectorizer.fit_transform(code_texts)
        
        print("Index creation complete!")
    
    def save_index(self, file_path):
        """Save the index to disk."""
        index_data = {
            'fragments': self.fragments,
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'tfidf_matrix': self.tfidf_matrix,
            'code_vectorizer': self.code_vectorizer,
            'code_matrix': self.code_matrix,
            'metadata': self.metadata
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        # Save readable statistics
        stats = self.get_statistics()
        stats_file = file_path.replace('.pkl', '_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return stats_file
    
    def get_statistics(self):
        """Get statistics about the index."""
        if not self.fragments:
            return {"status": "empty"}
        
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
            "total_files": self.metadata.get('total_files', 0),
            "file_types": file_types,
            "procedures_found": procedure_count,
            "functions_found": function_count,
            "created_at": self.metadata.get('created_at'),
            "model_name": self.metadata.get('model_name')
        }

def main():
    """Main indexer function."""
    print("="*60)
    print("SIMPLE TAL CODE INDEXER")
    print("="*60)
    
    # Get TAL directory
    if len(sys.argv) > 1:
        tal_directory = sys.argv[1]
    else:
        tal_directory = input("Enter path to TAL source directory: ").strip()
    
    if not os.path.exists(tal_directory):
        print(f"❌ ERROR: Directory not found: {tal_directory}")
        return False
    
    # Check for TAL files
    extensions = ['.tal', '.TAL', '.c', '.h']
    tal_files = []
    for root, dirs, files in os.walk(tal_directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                tal_files.append(file)
    
    if not tal_files:
        print(f"❌ ERROR: No TAL files found in directory")
        print(f"   Looking for: {', '.join(extensions)}")
        return False
    
    print(f"📁 Found {len(tal_files)} TAL files")
    
    try:
        # Create indexer and index directory
        indexer = SimpleTALIndexer()
        indexer.index_directory(tal_directory)
        
        # Save index
        dir_name = os.path.basename(os.path.abspath(tal_directory))
        output_file = f"tal_index_{dir_name}.pkl"
        
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
        
        stats_file = indexer.save_index(output_file)
        stats = indexer.get_statistics()
        
        # Success message
        print(f"\n" + "="*60)
        print("✅ INDEXING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"📁 Source directory: {tal_directory}")
        print(f"💾 Index saved to: {output_file}")
        print(f"📋 Statistics saved to: {stats_file}")
        print(f"📊 Results:")
        print(f"   - Files processed: {stats['total_files']}")
        print(f"   - Code fragments: {stats['total_fragments']}")
        print(f"   - Procedures found: {stats['procedures_found']}")
        print(f"   - Functions found: {stats['functions_found']}")
        print(f"\n🎉 Ready to use with TAL JIRA searcher!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
