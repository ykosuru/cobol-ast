#!/usr/bin/env python3
"""
TAL Corpus Indexer

Creates semantic indexes of TAL source code files with chunks, vectors, and topics.
Saves the processed corpus for later searching.
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

class SimpleChunk:
    """Simplified chunk representation."""
    def __init__(self, content, source_file, chunk_id, start_line=0, end_line=0, procedure_name=""):
        self.content = content
        self.source_file = source_file
        self.chunk_id = chunk_id
        self.start_line = start_line
        self.end_line = end_line
        self.procedure_name = procedure_name
        
        # Extract basic info
        self.words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content.lower())
        self.word_count = len(self.words)
        self.char_count = len(content)
        
        # Will be filled by vectorizer
        self.tfidf_vector = []
        self.topic_distribution = []
        self.dominant_topic = -1
        self.dominant_topic_prob = 0.0
        self.keywords = []

class TALChunker:
    """Chunks TAL files by procedures and logical blocks."""
    
    def __init__(self):
        self.procedure_pattern = re.compile(r'^\s*(?:PROC|SUBPROC)\s+(\w+)', re.IGNORECASE | re.MULTILINE)
    
    def chunk_file(self, file_path):
        """Chunk a single TAL file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        if not content.strip():
            return []
        
        return self._chunk_tal_content(content, file_path)
    
    def _chunk_tal_content(self, content, file_path):
        """Chunk TAL content by procedures."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        chunk_start_line = 0
        chunk_id = 0
        current_proc_name = ""
        
        for line_no, line in enumerate(lines):
            # Check for procedure start
            proc_match = self.procedure_pattern.search(line)
            
            if proc_match and current_chunk:
                # Save previous chunk
                chunk_content = '\n'.join(current_chunk)
                if chunk_content.strip():
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
                current_proc_name = proc_match.group(1)
            else:
                current_chunk.append(line)
                
                # If we haven't found a procedure yet and this line has one
                if proc_match and not current_proc_name:
                    current_proc_name = proc_match.group(1)
                
                # Split large chunks
                if len(current_chunk) > 100:  # lines
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
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if chunk_content.strip():
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

class SimpleVectorizer:
    """Creates TF-IDF vectors and basic topic modeling."""
    
    def __init__(self, max_features=3000, n_topics=10):
        self.max_features = max_features
        self.n_topics = n_topics
        self.vocabulary = {}
        self.idf_values = {}
        self.topic_labels = []
        self.document_count = 0
    
    def fit_transform(self, chunks):
        """Create vectors and topics for chunks."""
        print(f"Creating vectors for {len(chunks)} chunks...")
        
        if not chunks:
            print("No chunks to process")
            return
        
        # Extract documents
        documents = [chunk.content for chunk in chunks]
        doc_words = [chunk.words for chunk in chunks]
        
        # Build vocabulary
        self._build_vocabulary(doc_words)
        
        # Create TF-IDF vectors
        self._create_tfidf_vectors(chunks, doc_words)
        
        # Create simple topics
        self._create_simple_topics(chunks, doc_words)
        
        print(f"✅ Created vectors with {len(self.vocabulary)} features and {self.n_topics} topics")
    
    def _build_vocabulary(self, doc_words):
        """Build vocabulary from document words."""
        # Count word frequencies across documents
        word_doc_freq = defaultdict(int)
        for words in doc_words:
            unique_words = set(words)
            for word in unique_words:
                word_doc_freq[word] += 1
        
        self.document_count = len(doc_words)
        
        # Filter vocabulary (appear in at least 1 doc, but not more than 90%)
        min_df = 1
        max_df = int(0.9 * self.document_count)
        
        vocab_candidates = [
            (word, freq) for word, freq in word_doc_freq.items()
            if min_df <= freq <= max_df and len(word) >= 2
        ]
        
        # Sort by frequency and take top features
        vocab_candidates.sort(key=lambda x: x[1], reverse=True)
        if len(vocab_candidates) > self.max_features:
            vocab_candidates = vocab_candidates[:self.max_features]
        
        self.vocabulary = {word: idx for idx, (word, _) in enumerate(vocab_candidates)}
        
        # Calculate IDF values
        for word, doc_freq in vocab_candidates:
            self.idf_values[word] = math.log(self.document_count / doc_freq) if doc_freq > 0 else 0
        
        print(f"  Built vocabulary: {len(self.vocabulary)} words")
    
    def _create_tfidf_vectors(self, chunks, doc_words):
        """Create TF-IDF vectors for chunks."""
        for chunk, words in zip(chunks, doc_words):
            vector = [0.0] * len(self.vocabulary)
            word_counts = Counter(words)
            total_words = len(words)
            
            if total_words > 0:
                for word, count in word_counts.items():
                    if word in self.vocabulary:
                        tf = count / total_words
                        idf = self.idf_values[word]
                        tfidf = tf * idf
                        vector[self.vocabulary[word]] = tfidf
            
            chunk.tfidf_vector = vector
            
            # Extract keywords (top TF-IDF terms)
            word_scores = [(word, vector[idx]) for word, idx in self.vocabulary.items() if vector[idx] > 0]
            word_scores.sort(key=lambda x: x[1], reverse=True)
            chunk.keywords = [word for word, _ in word_scores[:8]]
    
    def _create_simple_topics(self, chunks, doc_words):
        """Create simple topic assignments based on word co-occurrence."""
        # For simplicity, create topics based on common word patterns
        all_words = []
        for words in doc_words:
            all_words.extend(words)
        
        word_freq = Counter(all_words)
        
        # Create topic labels based on most common words
        common_words = [word for word, _ in word_freq.most_common(50)]
        
        # Group words into topics
        topic_words = []
        for i in range(self.n_topics):
            start_idx = i * (len(common_words) // self.n_topics)
            end_idx = (i + 1) * (len(common_words) // self.n_topics)
            topic_word_group = common_words[start_idx:end_idx]
            topic_words.append(topic_word_group)
            self.topic_labels.append(" + ".join(topic_word_group[:4]))
        
        # Assign topics to chunks based on word overlap
        for chunk in chunks:
            chunk_words_set = set(chunk.words)
            topic_scores = []
            
            for topic_word_group in topic_words:
                overlap = len(chunk_words_set & set(topic_word_group))
                score = overlap / len(topic_word_group) if topic_word_group else 0
                topic_scores.append(score)
            
            # Normalize to create distribution
            total_score = sum(topic_scores) if sum(topic_scores) > 0 else 1
            chunk.topic_distribution = [score / total_score for score in topic_scores]
            
            # Find dominant topic
            if topic_scores:
                max_score = max(topic_scores)
                chunk.dominant_topic = topic_scores.index(max_score)
                chunk.dominant_topic_prob = max_score / total_score
            else:
                chunk.dominant_topic = 0
                chunk.dominant_topic_prob = 1.0 / self.n_topics

class CorpusIndexer:
    """Main corpus indexing class."""
    
    def __init__(self, max_features=3000, n_topics=10):
        self.chunker = TALChunker()
        self.vectorizer = SimpleVectorizer(max_features, n_topics)
        self.chunks = []
        self.stats = {
            'total_files': 0,
            'total_chunks': 0,
            'total_procedures': 0,
            'avg_chunk_size': 0,
            'file_types': {},
            'largest_chunk': 0,
            'smallest_chunk': 0
        }
    
    def index_directory(self, directory_path, file_extensions=None):
        """Index all files in directory."""
        if file_extensions is None:
            file_extensions = ['.tal', '.TAL', '.c', '.h']
        
        print(f"📁 Indexing corpus from: {directory_path}")
        
        # Find all matching files
        matching_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    matching_files.append(os.path.join(root, file))
        
        if not matching_files:
            print(f"❌ No files found with extensions: {file_extensions}")
            return []
        
        print(f"📄 Found {len(matching_files)} files to process")
        
        # Process each file
        all_chunks = []
        file_type_counts = defaultdict(int)
        
        for file_path in matching_files:
            file_ext = Path(file_path).suffix.lower()
            file_type_counts[file_ext] += 1
            
            print(f"  Processing: {os.path.basename(file_path)}")
            file_chunks = self.chunker.chunk_file(file_path)
            all_chunks.extend(file_chunks)
            print(f"    Created {len(file_chunks)} chunks")
        
        self.chunks = all_chunks
        
        if not self.chunks:
            print("❌ No chunks created from files")
            return []
        
        print(f"\n📊 Total chunks created: {len(self.chunks)}")
        
        # Create vectors and topics
        self.vectorizer.fit_transform(self.chunks)
        
        # Update statistics
        chunk_sizes = [c.word_count for c in self.chunks]
        self.stats.update({
            'total_files': len(matching_files),
            'total_chunks': len(self.chunks),
            'total_procedures': len([c for c in self.chunks if c.procedure_name]),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            'file_types': dict(file_type_counts),
            'largest_chunk': max(chunk_sizes) if chunk_sizes else 0,
            'smallest_chunk': min(chunk_sizes) if chunk_sizes else 0
        })
        
        return self.chunks
    
    def print_statistics(self):
        """Print comprehensive indexing statistics."""
        print(f"\n{'='*60}")
        print("📊 CORPUS INDEXING STATISTICS")
        print("="*60)
        print(f"Files processed: {self.stats['total_files']}")
        print(f"Chunks created: {self.stats['total_chunks']}")
        print(f"Procedures found: {self.stats['total_procedures']}")
        print(f"Average chunk size: {self.stats['avg_chunk_size']:.1f} words")
        print(f"Largest chunk: {self.stats['largest_chunk']} words")
        print(f"Smallest chunk: {self.stats['smallest_chunk']} words")
        print(f"Vocabulary size: {len(self.vectorizer.vocabulary)}")
        print(f"Topics created: {len(self.vectorizer.topic_labels)}")
        
        if self.stats['file_types']:
            print(f"\nFile types processed:")
            for ext, count in self.stats['file_types'].items():
                print(f"  {ext}: {count} files")
    
    def print_topics(self):
        """Print discovered topics."""
        print(f"\n{'='*60}")
        print("🏷️  DISCOVERED TOPICS")
        print("="*60)
        for i, label in enumerate(self.vectorizer.topic_labels):
            print(f"Topic {i:2d}: {label}")
    
    def print_sample_chunks(self, n=3):
        """Print sample chunks with details."""
        print(f"\n{'='*60}")
        print(f"📋 SAMPLE CHUNKS (showing first {n})")
        print("="*60)
        
        for i, chunk in enumerate(self.chunks[:n]):
            print(f"\nChunk {i}:")
            print(f"  📁 File: {os.path.basename(chunk.source_file)}")
            print(f"  📍 Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"  🔧 Procedure: {chunk.procedure_name or 'None'}")
            print(f"  📝 Words: {chunk.word_count} characters: {chunk.char_count}")
            print(f"  🏷️  Dominant Topic: {chunk.dominant_topic} ({chunk.dominant_topic_prob:.3f})")
            if chunk.dominant_topic < len(self.vectorizer.topic_labels):
                print(f"     Topic Label: {self.vectorizer.topic_labels[chunk.dominant_topic]}")
            print(f"  🔑 Keywords: {', '.join(chunk.keywords[:6])}")
            print(f"  📄 Content preview:")
            
            lines = chunk.content.split('\n')[:4]
            for line in lines:
                clean_line = line.strip()
                if clean_line:
                    print(f"     {clean_line[:65]}{'...' if len(clean_line) > 65 else ''}")
    
    def save_corpus(self, output_path):
        """Save the processed corpus with metadata."""
        print(f"\n💾 Saving corpus...")
        
        corpus_data = {
            'version': '1.0',
            'created_at': __import__('datetime').datetime.now().isoformat(),
            'chunks': [
                {
                    'content': chunk.content,
                    'source_file': chunk.source_file,
                    'chunk_id': chunk.chunk_id,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'procedure_name': chunk.procedure_name,
                    'word_count': chunk.word_count,
                    'char_count': chunk.char_count,
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
                'idf_values': self.vectorizer.idf_values,
                'topic_labels': self.vectorizer.topic_labels,
                'max_features': self.vectorizer.max_features,
                'n_topics': self.vectorizer.n_topics,
                'document_count': self.vectorizer.document_count
            },
            'stats': self.stats
        }
        
        # Save main corpus file
        with open(output_path, 'wb') as f:
            pickle.dump(corpus_data, f)
        
        # Save human-readable summary
        summary_path = output_path.replace('.pkl', '_summary.json')
        summary = {
            'created_at': corpus_data['created_at'],
            'statistics': self.stats,
            'topics': [
                {'id': i, 'label': label} 
                for i, label in enumerate(self.vectorizer.topic_labels)
            ],
            'sample_procedures': [
                chunk.procedure_name for chunk in self.chunks 
                if chunk.procedure_name
            ][:10],
            'vocabulary_preview': list(self.vectorizer.vocabulary.keys())[:20]
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ Corpus saved to: {output_path}")
        print(f"📋 Summary saved to: {summary_path}")
        print(f"💾 Corpus size: {len(self.chunks)} chunks, {len(self.vectorizer.vocabulary)} vocabulary")

def main():
    """Main indexer function."""
    print("="*60)
    print("📚 TAL CORPUS INDEXER")
    print("="*60)
    print("Creates semantic index with chunks, vectors, and topics")
    
    # Get directory
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = input("📁 Enter directory path: ").strip()
    
    if not directory or not os.path.exists(directory):
        print(f"❌ Invalid directory: {directory}")
        return False
    
    if not os.path.isdir(directory):
        print(f"❌ Path is not a directory: {directory}")
        return False
    
    # Get file extensions
    print(f"\nDefault extensions: .tal, .TAL, .c, .h")
    extensions_input = input("📄 File extensions (Enter for default): ").strip()
    if extensions_input:
        file_extensions = [ext.strip() for ext in extensions_input.split(',')]
        # Ensure extensions start with dot
        file_extensions = [ext if ext.startswith('.') else '.' + ext for ext in file_extensions]
    else:
        file_extensions = ['.tal', '.TAL', '.c', '.h']
    
    # Get processing parameters
    try:
        max_features = int(input("🔧 Max TF-IDF features (default 3000): ") or "3000")
        n_topics = int(input("🏷️  Number of topics (default 10): ") or "10")
    except ValueError:
        print("Invalid input, using defaults")
        max_features, n_topics = 3000, 10
    
    print(f"\n🚀 Starting indexing with {max_features} features and {n_topics} topics...")
    
    # Create indexer and process
    indexer = CorpusIndexer(max_features, n_topics)
    
    try:
        chunks = indexer.index_directory(directory, file_extensions)
        
        if not chunks:
            print("❌ No chunks created - check directory and file extensions")
            return False
        
        # Show results
        indexer.print_statistics()
        indexer.print_topics()
        indexer.print_sample_chunks()
        
        # Save corpus
        dir_name = os.path.basename(os.path.abspath(directory))
        output_file = f"tal_corpus_{dir_name}.pkl"
        
        save_choice = input(f"\n💾 Save corpus to {output_file}? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '']:
            indexer.save_corpus(output_file)
            
            print(f"\n✅ Indexing completed successfully!")
            print(f"📁 Index file: {output_file}")
            print(f"🔍 Use this file with the TAL searcher to query your corpus")
        else:
            print(f"\n✅ Indexing completed (not saved)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ Indexing failed!")
        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")
