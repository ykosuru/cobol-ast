from flask import Flask, request, jsonify, render_template_string
import os
import json
import numpy as np
from docx import Document
import PyPDF2
from anthropic import Anthropic
import subprocess
from sentence_transformers import SentenceTransformer
import tempfile
from werkzeug.utils import secure_filename
import shutil
import hashlib
from datetime import datetime
from tqdm import tqdm
import sys
import logging
import time
import traceback

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = './uploads'
DOCS_DIR = "./docs"
INDEX_FILE = "indexed_docs.json"
CATALOG_FILE = "document_catalog.json"  # New: tracks indexed files
LUCENE_INDEX_DIR = "./lucene_index"
LUCENE_INPUT_FILE = "lucene_input.json"
LUCENE_RESULTS_FILE = "lucene_results.json"
LUCENE_CHUNKS_FILE = "lucene_chunks.json"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-api-key")
NUM_QA_PAIRS = 2
JAVA_CLASS = "LuceneIndexerSearcher"
LIBS = "./libs"

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_search.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create specialized loggers
app_logger = logging.getLogger('DocumentSearchAPI')
indexing_logger = logging.getLogger('Indexing')
query_logger = logging.getLogger('Query')
file_logger = logging.getLogger('FileOps')
java_logger = logging.getLogger('JavaLucene')
ai_logger = logging.getLogger('AI')

# Set log levels
app_logger.setLevel(logging.INFO)
indexing_logger.setLevel(logging.DEBUG)
query_logger.setLevel(logging.INFO)
file_logger.setLevel(logging.DEBUG)
java_logger.setLevel(logging.INFO)
ai_logger.setLevel(logging.INFO)

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(LUCENE_INDEX_DIR, exist_ok=True)

app_logger.info("📁 Created necessary directories")
app_logger.info(f"   • Upload folder: {UPLOAD_FOLDER}")
app_logger.info(f"   • Documents directory: {DOCS_DIR}")
app_logger.info(f"   • Lucene index directory: {LUCENE_INDEX_DIR}")

# Initialize clients
app_logger.info("🚀 Initializing AI clients...")
try:
    anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    ai_logger.info("✅ Anthropic client initialized")
except Exception as e:
    ai_logger.error(f"❌ Failed to initialize Anthropic client: {e}")

try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    ai_logger.info("✅ SentenceTransformer model loaded: all-MiniLM-L6-v2")
except Exception as e:
    ai_logger.error(f"❌ Failed to load SentenceTransformer model: {e}")

def get_file_hash(file_path):
    """Generate MD5 hash of file content for change detection."""
    start_time = time.time()
    file_logger.debug(f"🔍 Computing hash for: {file_path}")
    
    try:
        hash_md5 = hashlib.md5()
        file_size = 0
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
                file_size += len(chunk)
        
        hash_value = hash_md5.hexdigest()
        elapsed = time.time() - start_time
        file_logger.debug(f"✅ Hash computed: {hash_value[:16]}... (size: {file_size:,} bytes, time: {elapsed:.2f}s)")
        return hash_value
    except Exception as e:
        file_logger.error(f"❌ Error hashing file {file_path}: {e}")
        return None

def get_file_info(file_path):
    """Get file metadata for catalog."""
    file_logger.debug(f"📊 Getting file info for: {file_path}")
    
    try:
        stat = os.stat(file_path)
        file_info = {
            "size": stat.st_size,
            "modified_time": stat.st_mtime,
            "hash": get_file_hash(file_path)
        }
        file_logger.debug(f"✅ File info retrieved: size={file_info['size']:,} bytes, modified={datetime.fromtimestamp(file_info['modified_time'])}")
        return file_info
    except Exception as e:
        file_logger.error(f"❌ Error getting file info for {file_path}: {e}")
        return None

def load_document_catalog():
    """Load the document catalog or create new one."""
    file_logger.debug(f"📖 Loading document catalog from: {CATALOG_FILE}")
    
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r") as f:
                catalog = json.load(f)
            file_logger.info(f"✅ Loaded catalog: {len(catalog.get('indexed_files', {}))} files, {catalog.get('total_chunks', 0)} chunks")
            return catalog
        except Exception as e:
            file_logger.error(f"❌ Error loading catalog: {e}")
    
    # Return empty catalog structure
    file_logger.info("📝 Creating new empty catalog")
    return {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "indexed_files": {},  # filename -> {hash, size, modified_time, chunks_count, indexed_time}
        "total_chunks": 0
    }

def save_document_catalog(catalog):
    """Save the document catalog."""
    file_logger.debug(f"💾 Saving document catalog to: {CATALOG_FILE}")
    
    try:
        catalog["last_updated"] = datetime.now().isoformat()
        with open(CATALOG_FILE, "w") as f:
            json.dump(catalog, f, indent=2)
        file_logger.info(f"✅ Catalog saved: {len(catalog.get('indexed_files', {}))} files, {catalog.get('total_chunks', 0)} chunks")
        return True
    except Exception as e:
        file_logger.error(f"❌ Error saving catalog: {e}")
        return False

def get_files_to_index():
    """Determine which files need to be indexed (new or modified)."""
    indexing_logger.info("🔍 Scanning for files that need indexing...")
    
    catalog = load_document_catalog()
    files_to_index = []
    files_to_remove = []
    
    # Get all current document files
    current_files = {}
    if os.path.exists(DOCS_DIR):
        doc_files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(('.pdf', '.docx', '.txt', '.md'))]
        indexing_logger.info(f"📁 Found {len(doc_files)} document files in {DOCS_DIR}")
        
        for i, filename in enumerate(doc_files, 1):
            file_path = os.path.join(DOCS_DIR, filename)
            indexing_logger.debug(f"   📄 [{i}/{len(doc_files)}] Analyzing: {filename}")
            file_info = get_file_info(file_path)
            if file_info:
                current_files[filename] = file_info
            else:
                indexing_logger.warning(f"⚠️  Could not get file info for: {filename}")
    else:
        indexing_logger.warning(f"⚠️  Documents directory does not exist: {DOCS_DIR}")
    
    # Check for new or modified files
    indexing_logger.info("🔍 Checking for new or modified files...")
    for filename, file_info in current_files.items():
        if filename not in catalog["indexed_files"]:
            # New file
            files_to_index.append(filename)
            indexing_logger.info(f"🆕 New file detected: {filename} (size: {file_info['size']:,} bytes)")
        else:
            # Check if file has been modified
            catalog_info = catalog["indexed_files"][filename]
            if (file_info["hash"] != catalog_info.get("hash") or 
                file_info["modified_time"] != catalog_info.get("modified_time")):
                files_to_index.append(filename)
                indexing_logger.info(f"📝 Modified file detected: {filename}")
                indexing_logger.debug(f"   Old hash: {catalog_info.get('hash', 'None')[:16]}...")
                indexing_logger.debug(f"   New hash: {file_info['hash'][:16]}...")
    
    # Check for removed files
    indexing_logger.info("🔍 Checking for removed files...")
    for filename in catalog["indexed_files"]:
        if filename not in current_files:
            files_to_remove.append(filename)
            indexing_logger.info(f"🗑️  Removed file detected: {filename}")
    
    indexing_logger.info(f"📊 Scan results:")
    indexing_logger.info(f"   • Files to index: {len(files_to_index)}")
    indexing_logger.info(f"   • Files to remove: {len(files_to_remove)}")
    indexing_logger.info(f"   • Files up to date: {len(current_files) - len(files_to_index)}")
    
    return files_to_index, files_to_remove, current_files

def rebuild_lucene_index_incremental(files_to_index):
    """Rebuild Lucene index with only new/modified files with progress tracking."""
    if not files_to_index:
        java_logger.info("ℹ️  No files to index")
        return True, "No files to index"
    
    java_logger.info(f"🔍 Starting Lucene indexing for {len(files_to_index)} files")
    java_logger.debug(f"   Files: {files_to_index}")
    
    # Create temporary directory with only files to index
    temp_docs_dir = tempfile.mkdtemp()
    java_logger.debug(f"📁 Created temporary directory: {temp_docs_dir}")
    
    try:
        java_logger.info("📁 Copying files to temporary directory...")
        for i, filename in enumerate(files_to_index, 1):
            src_path = os.path.join(DOCS_DIR, filename)
            dst_path = os.path.join(temp_docs_dir, filename)
            
            copy_start = time.time()
            shutil.copy2(src_path, dst_path)
            copy_time = time.time() - copy_start
            
            # Get file size for logging
            file_size = os.path.getsize(src_path)
            java_logger.info(f"   📄 [{i}/{len(files_to_index)}] Copied: {filename} ({file_size:,} bytes, {copy_time:.2f}s)")
            sys.stdout.flush()
        
        # Create input for Java indexer
        lucene_input = {
            "action": "index-dir",
            "docs_dir": temp_docs_dir,
            "index_dir": LUCENE_INDEX_DIR
        }
        
        java_logger.debug(f"💾 Writing Lucene input file: {LUCENE_INPUT_FILE}")
        with open(LUCENE_INPUT_FILE, "w") as f:
            json.dump(lucene_input, f, indent=2)
        
        # Build classpath
        classpath = (
            f".:"
            f"{LIBS}/lucene-core-9.12.2.jar:"
            f"{LIBS}/lucene-analyzers-common-9.12.2.jar:"
            f"{LIBS}/lucene-queryparser-9.12.2.jar:"
            f"{LIBS}/gson-2.10.1.jar:"
            f"{LIBS}/pdfbox-3.0.5.jar:"
            f"{LIBS}/pdfbox-io-3.0.5.jar:"
            f"{LIBS}/fontbox-3.0.5.jar:"
            f"{LIBS}/poi-4.1.2.jar:"
            f"{LIBS}/poi-ooxml-4.1.2.jar:"
            f"{LIBS}/poi-scratchpad-4.1.2.jar:"
            f"{LIBS}/poi-ooxml-schemas-4.1.2.jar:"
            f"{LIBS}/xmlbeans-3.1.0.jar:"
            f"{LIBS}/compress.1.9.2.jar:"
            f"{LIBS}/commons-collections4-4.4.jar"
        )
        
        java_logger.debug(f"📚 Classpath: {classpath}")
        
        # Run Java indexer
        java_logger.info("🚀 Running Java Lucene indexer...")
        java_start = time.time()
        
        cmd = ["java", "-cp", classpath, JAVA_CLASS, LUCENE_INPUT_FILE]
        java_logger.debug(f"🔧 Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        java_elapsed = time.time() - java_start
        java_logger.info(f"✅ Java indexer completed successfully (time: {java_elapsed:.2f}s)")
        
        if result.stdout:
            java_logger.debug(f"📄 Java stdout: {result.stdout}")
        if result.stderr:
            java_logger.warning(f"⚠️  Java stderr: {result.stderr}")
            
        return True, result.stdout
        
    except subprocess.CalledProcessError as e:
        java_elapsed = time.time() - java_start if 'java_start' in locals() else 0
        java_logger.error(f"❌ Java indexer failed after {java_elapsed:.2f}s")
        java_logger.error(f"   Return code: {e.returncode}")
        java_logger.error(f"   Stderr: {e.stderr}")
        java_logger.error(f"   Stdout: {e.stdout}")
        return False, f"Error running Java Lucene indexer: {e.stderr}"
    except Exception as e:
        java_logger.error(f"❌ Unexpected error in Lucene indexing: {e}")
        java_logger.error(f"   Traceback: {traceback.format_exc()}")
        return False, f"Unexpected error: {str(e)}"
    finally:
        # Clean up temp directory
        java_logger.debug("🧹 Cleaning up temporary directory...")
        try:
            shutil.rmtree(temp_docs_dir, ignore_errors=True)
            java_logger.debug("✅ Temporary directory cleaned up")
        except Exception as e:
            java_logger.warning(f"⚠️  Error cleaning up temp directory: {e}")

def merge_lucene_chunks():
    if not files_to_index:
        return True, "No files to index"
    
    print(f"🔍 Building Lucene index for {len(files_to_index)} files...")
    
    # Create temporary directory with only files to index
    temp_docs_dir = tempfile.mkdtemp()
    try:
        print("📁 Copying files to temporary directory...")
        for i, filename in enumerate(files_to_index, 1):
            src_path = os.path.join(DOCS_DIR, filename)
            dst_path = os.path.join(temp_docs_dir, filename)
            shutil.copy2(src_path, dst_path)
            print(f"   📄 [{i}/{len(files_to_index)}] Copied: {filename}")
            sys.stdout.flush()
        
        # Create input for Java indexer
        lucene_input = {
            "action": "index-dir",
            "docs_dir": temp_docs_dir,
            "index_dir": LUCENE_INDEX_DIR
        }
        
        with open(LUCENE_INPUT_FILE, "w") as f:
            json.dump(lucene_input, f)
        
        # Run Java indexer
        classpath = (
            f".:"
            f"{LIBS}/lucene-core-9.12.2.jar:"
            f"{LIBS}/lucene-analyzers-common-9.12.2.jar:"
            f"{LIBS}/lucene-queryparser-9.12.2.jar:"
            f"{LIBS}/gson-2.10.1.jar:"
            f"{LIBS}/pdfbox-3.0.5.jar:"
            f"{LIBS}/pdfbox-io-3.0.5.jar:"
            f"{LIBS}/fontbox-3.0.5.jar:"
            f"{LIBS}/poi-4.1.2.jar:"
            f"{LIBS}/poi-ooxml-4.1.2.jar:"
            f"{LIBS}/poi-scratchpad-4.1.2.jar:"
            f"{LIBS}/poi-ooxml-schemas-4.1.2.jar:"
            f"{LIBS}/xmlbeans-3.1.0.jar:"
            f"{LIBS}/compress.1.9.2.jar:"
            f"{LIBS}/commons-collections4-4.4.jar"
        )
        
        print("🚀 Running Java Lucene indexer...")
        result = subprocess.run(
            ["java", "-cp", classpath, JAVA_CLASS, LUCENE_INPUT_FILE],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Java indexer completed successfully")
        return True, result.stdout
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Java indexer failed: {e.stderr}")
        return False, f"Error running Java Lucene indexer: {e.stderr}"
    finally:
        # Clean up temp directory
        print("🧹 Cleaning up temporary directory...")
        shutil.rmtree(temp_docs_dir, ignore_errors=True)

def merge_lucene_chunks():
    """Merge new chunks with existing chunk metadata."""
    # Load existing chunks
    existing_chunks = []
    if os.path.exists(LUCENE_CHUNKS_FILE):
        try:
            with open(LUCENE_CHUNKS_FILE, "r") as f:
                existing_chunks = json.load(f)
        except Exception as e:
            print(f"Error loading existing chunks: {e}")
    
    # The Java indexer creates a new lucene_chunks.json with new files
    # We need to merge this with existing chunks
    temp_chunks_file = "lucene_chunks_temp.json"
    if os.path.exists(temp_chunks_file):
        try:
            with open(temp_chunks_file, "r") as f:
                new_chunks = json.load(f)
            
            # Merge chunks (remove old chunks for updated files)
            files_to_index, _, _ = get_files_to_index()
            
            # Remove chunks from files that were re-indexed
            filtered_existing = [chunk for chunk in existing_chunks 
                               if chunk["doc_name"] not in files_to_index]
            
            # Add new chunks
            merged_chunks = filtered_existing + new_chunks
            
            # Save merged chunks
            with open(LUCENE_CHUNKS_FILE, "w") as f:
                json.dump(merged_chunks, f, indent=2)
            
            # Clean up temp file
            os.remove(temp_chunks_file)
            
            return merged_chunks
            
        except Exception as e:
            print(f"Error merging chunks: {e}")
            return existing_chunks
    
    return existing_chunks

# Utility functions
def get_local_embedding(text):
    """Generate embedding using a local sentence-transformers model."""
    ai_logger.debug(f"🧮 Generating embedding for text (length: {len(text)} chars)")
    start_time = time.time()
    
    try:
        embedding = embedding_model.encode(text, convert_to_numpy=True).tolist()
        elapsed = time.time() - start_time
        ai_logger.debug(f"✅ Embedding generated: {len(embedding)} dimensions, time: {elapsed:.2f}s")
        return embedding
    except Exception as e:
        ai_logger.error(f"❌ Error generating embedding: {e}")
        return None

def generate_summary(chunk):
    """Generate a 2-3 sentence summary for a chunk using Claude."""
    ai_logger.debug(f"📝 Generating summary for chunk (length: {len(chunk)} chars)")
    start_time = time.time()
    
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": f"Summarize this in 2-3 sentences:\n{chunk}"}]
        )
        summary = response.content[0].text
        elapsed = time.time() - start_time
        ai_logger.debug(f"✅ Summary generated (length: {len(summary)} chars, time: {elapsed:.2f}s)")
        return summary
    except Exception as e:
        ai_logger.error(f"❌ Error generating summary: {e}")
        ai_logger.error(f"   Traceback: {traceback.format_exc()}")
        return ""

def generate_qa_pairs(chunk, doc_text, num_pairs=NUM_QA_PAIRS):
    """Generate question-answer pairs for a chunk using Claude."""
    ai_logger.debug(f"🤔 Generating {num_pairs} Q&A pairs for chunk (length: {len(chunk)} chars)")
    start_time = time.time()
    
    try:
        prompt = (
            f"Based on the following chunk and its parent document, generate {num_pairs} question-answer pairs "
            "that reflect key information in the chunk. Format as JSON: [{{\"question\": \"\", \"answer\": \"\"}}, ...]\n\n"
            f"Chunk: {chunk}\n\nParent Document (excerpt): {doc_text[:1000]}\n\nQ&A Pairs:"
        )
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        qa_text = response.content[0].text.strip()
        qa_pairs = json.loads(qa_text)[:num_pairs]
        elapsed = time.time() - start_time
        ai_logger.debug(f"✅ Generated {len(qa_pairs)} Q&A pairs (time: {elapsed:.2f}s)")
        return qa_pairs
    except Exception as e:
        ai_logger.error(f"❌ Error generating Q&A pairs: {e}")
        ai_logger.error(f"   Traceback: {traceback.format_exc()}")
        return []

def extract_text_from_file(file_path):
    """Extract text from supported file types."""
    file_logger.info(f"📖 Extracting text from: {file_path}")
    start_time = time.time()
    
    try:
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        file_logger.debug(f"   File type: {ext}")

        text = ""
        if ext == '.docx':
            file_logger.debug("   Using python-docx for DOCX extraction")
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        elif ext == '.pdf':
            file_logger.debug("   Using PyPDF2 for PDF extraction")
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                page_texts = []
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text() or ""
                    page_texts.append(page_text)
                    file_logger.debug(f"      Page {i+1}: {len(page_text)} chars")
                text = "\n".join(page_texts).strip()
        elif ext in ['.txt', '.md']:
            file_logger.debug(f"   Reading as plain text file")
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        else:
            file_logger.warning(f"⚠️  Unsupported file type: {ext}")
            return ""
        
        elapsed = time.time() - start_time
        file_logger.info(f"✅ Text extracted: {len(text):,} characters (time: {elapsed:.2f}s)")
        
        if len(text) == 0:
            file_logger.warning(f"⚠️  No text extracted from {file_path}")
        
        return text
        
    except Exception as e:
        file_logger.error(f"❌ Error processing {file_path}: {e}")
        file_logger.error(f"   Traceback: {traceback.format_exc()}")
        return ""

def index_documents_incremental():
    """Index only new or modified documents with progress tracking."""
    files_to_index, files_to_remove, current_files = get_files_to_index()
    catalog = load_document_catalog()
    
    # Remove deleted files from catalog
    for filename in files_to_remove:
        if filename in catalog["indexed_files"]:
            del catalog["indexed_files"][filename]
            print(f"🗑️  Removed {filename} from catalog")
    
    if not files_to_index:
        print("✅ No new or modified files to index")
        return True, {"message": "No new files to index", "files_processed": 0}
    
    print(f"📁 Found {len(files_to_index)} files to index")
    
    # Show progress for each file being indexed
    for i, filename in enumerate(files_to_index, 1):
        print(f"📄 [{i}/{len(files_to_index)}] Processing: {filename}")
        sys.stdout.flush()  # Ensure immediate output
    
    print(f"🚀 Starting batch indexing of {len(files_to_index)} files...")
    
    # Build Lucene index for new files
    success, message = rebuild_lucene_index_incremental(files_to_index)
    if not success:
        return False, f"Failed to build Lucene index: {message}"
    
    print("✅ Lucene indexing completed")
    
    # Load existing embeddings
    existing_embeddings = []
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r") as f:
                existing_embeddings = json.load(f)
            print(f"📊 Loaded {len(existing_embeddings)} existing embeddings")
        except Exception as e:
            print(f"⚠️  Error loading existing embeddings: {e}")
    
    # Remove embeddings for files that were re-indexed
    existing_embeddings = [emb for emb in existing_embeddings 
                          if emb["doc_name"] not in files_to_index]
    
    # Process new chunk metadata
    chunk_metadata = merge_lucene_chunks()
    
    # Filter chunks for files we're currently indexing
    new_chunks = [chunk for chunk in chunk_metadata 
                  if chunk["doc_name"] in files_to_index]
    
    if not new_chunks:
        print("⚠️  No new chunks found")
        return True, {"message": "No chunks to process", "files_processed": len(files_to_index)}
    
    print(f"📦 Generated {len(new_chunks)} chunks from {len(files_to_index)} files")
    
    # Cache document texts for new files
    print("📖 Reading document texts...")
    doc_texts = {}
    for i, filename in enumerate(files_to_index, 1):
        print(f"   📄 [{i}/{len(files_to_index)}] Reading: {filename}")
        doc_path = os.path.join(DOCS_DIR, filename)
        doc_texts[filename] = extract_text_from_file(doc_path) or ""
        sys.stdout.flush()
    
    # Generate embeddings for new chunks with progress
    print("🧮 Generating embeddings...")
    print("   📝 Creating contextualized chunks...")
    contextualized_chunks = []
    
    # Group chunks by document for progress tracking
    chunks_by_doc = {}
    for chunk in new_chunks:
        doc_name = chunk['doc_name']
        if doc_name not in chunks_by_doc:
            chunks_by_doc[doc_name] = []
        chunks_by_doc[doc_name].append(chunk)
    
    # Process chunks with document-level progress
    for doc_name, doc_chunks in chunks_by_doc.items():
        print(f"   📄 Processing {len(doc_chunks)} chunks from {doc_name}")
        for chunk in doc_chunks:
            contextualized_chunk = (
                f"Document: {chunk['doc_name']}, Chunk {chunk['chunk_id']}\n"
                f"Keywords: {', '.join(chunk['keywords'])}\n"
                f"Summary: {generate_summary(chunk['content'])}\n\n"
                f"{chunk['content']}"
            )
            contextualized_chunks.append(contextualized_chunk)
        sys.stdout.flush()
    
    print(f"🚀 Encoding {len(contextualized_chunks)} chunks to embeddings...")
    embeddings = embedding_model.encode(contextualized_chunks, batch_size=32, show_progress_bar=False)
    print("✅ Embedding generation completed")
    
    # Create new embedding entries with progress
    print("🔗 Creating embedding entries...")
    new_embeddings = []
    
    processed_chunks = 0
    for doc_name, doc_chunks in chunks_by_doc.items():
        print(f"   📄 Processing embeddings for {doc_name}")
        
        for chunk in doc_chunks:
            chunk_id = chunk["chunk_id"]
            content = chunk["content"]
            keywords = chunk["keywords"]
            
            print(f"      🧩 Chunk {chunk_id}: Generating summary and Q&A...")
            summary = generate_summary(content)
            qa_pairs = generate_qa_pairs(content, doc_texts[doc_name])
            
            embedding = embeddings[processed_chunks].tolist() if processed_chunks < len(embeddings) else None
            processed_chunks += 1
            
            if embedding:
                new_embeddings.append({
                    "doc_name": doc_name,
                    "chunk_id": chunk_id,
                    "chunk": content,
                    "summary": summary,
                    "keywords": keywords,
                    "qa_pairs": qa_pairs,
                    "embedding": embedding
                })
            
            sys.stdout.flush()
    
    print(f"✅ Created {len(new_embeddings)} embedding entries")
    
    # Merge with existing embeddings
    all_embeddings = existing_embeddings + new_embeddings
    print(f"💾 Saving {len(all_embeddings)} total embeddings...")
    
    # Save updated embeddings
    with open(INDEX_FILE, "w") as f:
        json.dump(all_embeddings, f)
    
    # Update catalog with progress
    print("📋 Updating document catalog...")
    for filename in files_to_index:
        file_info = current_files[filename]
        chunks_count = len([chunk for chunk in new_chunks if chunk["doc_name"] == filename])
        
        catalog["indexed_files"][filename] = {
            "hash": file_info["hash"],
            "size": file_info["size"],
            "modified_time": file_info["modified_time"],
            "chunks_count": chunks_count,
            "indexed_time": datetime.now().isoformat()
        }
        print(f"   📄 Updated catalog for {filename} ({chunks_count} chunks)")
    
    catalog["total_chunks"] = len(all_embeddings)
    save_document_catalog(catalog)
    
    print("🎉 Incremental indexing completed successfully!")
    print(f"📊 Summary:")
    print(f"   • Files processed: {len(files_to_index)}")
    print(f"   • New chunks: {len(new_embeddings)}")
    print(f"   • Total chunks in index: {len(all_embeddings)}")
    
    return True, {
        "message": "Incremental indexing completed",
        "files_processed": len(files_to_index),
        "new_chunks": len(new_embeddings),
        "total_chunks": len(all_embeddings),
        "processed_files": files_to_index
    }

def query_documents(query, top_k=5):
    """Retrieve and answer a query using Java Lucene and semantic search."""
    # Load indexed documents
    if not os.path.exists(INDEX_FILE):
        return False, "No indexed documents available. Please run indexing first."
    
    with open(INDEX_FILE, "r") as f:
        indexed_docs = json.load(f)
    
    if not indexed_docs:
        return False, "No indexed documents available."
    
    # Embed query for semantic search
    query_embedding = get_local_embedding(query)
    if not query_embedding:
        return False, "Error embedding query."
    
    # Semantic search
    embeddings = np.array([doc["embedding"] for doc in indexed_docs])
    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )
    semantic_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Lucene search via Java
    with open(LUCENE_INPUT_FILE, "w") as f:
        json.dump({"action": "search", "query": query, "index_dir": LUCENE_INDEX_DIR, "top_k": top_k}, f)
    
    classpath = (
        f".:"
        f"{LIBS}/lucene-core-9.12.2.jar:"
        f"{LIBS}/lucene-analyzers-common-9.12.2.jar:"
        f"{LIBS}/lucene-queryparser-9.12.2.jar:"
        f"{LIBS}/gson-2.10.1.jar:"
        f"{LIBS}/pdfbox-3.0.5.jar:"
        f"{LIBS}/pdfbox-io-3.0.5.jar:"
        f"{LIBS}/fontbox-3.0.5.jar:"
        f"{LIBS}/poi-4.1.2.jar:"
        f"{LIBS}/poi-ooxml-4.1.2.jar:"
        f"{LIBS}/poi-scratchpad-4.1.2.jar:"
        f"{LIBS}/poi-ooxml-schemas-4.1.2.jar:"
        f"{LIBS}/xmlbeans-3.1.0.jar:"
        f"{LIBS}/compress.1.9.2.jar:"
        f"{LIBS}/commons-collections4-4.4.jar"
    )
    
    try:
        subprocess.run(
            ["java", "-cp", classpath, JAVA_CLASS, LUCENE_INPUT_FILE],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        return False, f"Error performing Lucene search: {e}"
    
    # Read Lucene search results
    try:
        with open(LUCENE_RESULTS_FILE, "r") as f:
            lucene_results = json.load(f)
    except Exception as e:
        return False, f"Error reading Lucene results: {e}"
    
    lucene_indices = []
    for result in lucene_results.get("hits", []):
        doc_name = result["doc_name"]
        chunk_id = int(result["chunk_id"])
        for i, indexed_doc in enumerate(indexed_docs):
            if indexed_doc["doc_name"] == doc_name and indexed_doc["chunk_id"] == chunk_id:
                lucene_indices.append(i)
                break
    
    # Combine results (union of top-k indices)
    combined_indices = list(set(semantic_indices) | set(lucene_indices))[:top_k]
    retrieved_chunks = [
        f"Document: {indexed_docs[i]['doc_name']}, Chunk {indexed_docs[i]['chunk_id']}\n"
        f"Keywords: {', '.join(indexed_docs[i]['keywords'])}\n"
        f"Summary: {indexed_docs[i]['summary']}\n"
        f"Q&A: {json.dumps(indexed_docs[i]['qa_pairs'], indent=2)}\n\n"
        f"{indexed_docs[i]['chunk']}"
        for i in combined_indices
    ]
    
    # Generate response with Claude
    context = "\n\n".join(retrieved_chunks)
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"}]
        )
        return True, {
            "answer": response.content[0].text,
            "sources": [{"doc_name": indexed_docs[i]["doc_name"], 
                        "chunk_id": indexed_docs[i]["chunk_id"],
                        "summary": indexed_docs[i]["summary"]} for i in combined_indices]
        }
    except Exception as e:
        return False, f"Error generating response: {e}"

# Flask Routes

@app.route('/')
def home():
    """Home page with API documentation."""
    catalog = load_document_catalog()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Document Search API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .endpoint {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .method {{ color: #007bff; font-weight: bold; }}
            .status {{ background: #e8f5e9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            code {{ background: #e9ecef; padding: 2px 5px; border-radius: 3px; }}
            .catalog {{ background: #fff3e0; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>Document Search API</h1>
        
        <div class="status">
            <h3>Current Status:</h3>
            <p><strong>Indexed Files:</strong> {len(catalog['indexed_files'])}</p>
            <p><strong>Total Chunks:</strong> {catalog['total_chunks']}</p>
            <p><strong>Last Updated:</strong> {catalog['last_updated']}</p>
        </div>
        
        <div class="endpoint">
            <h2><span class="method">POST</span> /upload-and-index</h2>
            <p>Upload a single document and index it immediately for querying.</p>
            <h4>Upload and Index File:</h4>
            <form action="/upload-and-index" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".pdf,.docx,.txt,.md" required>
                <button type="submit">Upload & Index Now</button>
            </form>
            <p><small>Supported formats: PDF, DOCX, TXT, MD</small></p>
        </div>
        
        <div class="endpoint">
            <h2><span class="method">POST</span> /index</h2>
            <p>Incrementally index new or modified documents (smart indexing - only processes changes).</p>
            <h4>Upload multiple files:</h4>
            <form action="/index" method="post" enctype="multipart/form-data">
                <input type="file" name="files" multiple accept=".pdf,.docx,.txt,.md">
                <button type="submit">Upload and Index</button>
            </form>
            <h4>Or scan for new/modified docs:</h4>
            <form action="/index" method="post">
                <button type="submit">Scan and Index Changes</button>
            </form>
        </div>
        
        <div class="endpoint">
            <h2><span class="method">POST</span> /query</h2>
            <p>Search indexed documents and get AI-generated answers.</p>
            <h4>Test Query:</h4>
            <form action="/query" method="post" enctype="application/x-www-form-urlencoded">
                <input type="text" name="query" placeholder="Enter your question..." style="width: 300px; padding: 5px;">
                <input type="number" name="top_k" value="5" min="1" max="20" style="width: 60px; padding: 5px;">
                <button type="submit">Search</button>
            </form>
        </div>
        
        <div class="endpoint">
            <h2><span class="method">GET</span> /catalog</h2>
            <p>View detailed catalog of indexed documents.</p>
            <a href="/catalog"><button>View Catalog</button></a>
        </div>
        
        <h3>Indexed Files:</h3>
    """
    
    for filename, info in catalog['indexed_files'].items():
        html += f"""
        <div class="catalog">
            <strong>{filename}</strong><br>
            <small>Chunks: {info.get('chunks_count', 0)} | 
            Size: {info.get('size', 0)} bytes | 
            Indexed: {info.get('indexed_time', 'Unknown')}</small>
        </div>
        """
    
    html += """
        <h3>API Examples:</h3>
        <p><strong>Upload Single Document:</strong><br>
        <code>curl -X POST -F "file=@document.pdf" http://localhost:8000/upload-and-index</code></p>
        
        <p><strong>Incremental Indexing:</strong><br>
        <code>curl -X POST http://localhost:8000/index</code></p>
        
        <p><strong>Querying:</strong><br>
        <code>curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"query": "your question", "top_k": 5}'</code></p>
    </body>
    </html>
    """
    return html

@app.route('/index', methods=['POST'])
def index_documents():
    """Incrementally index documents - only new or modified files."""
    request_id = f"req_{int(time.time())}"
    app_logger.info(f"🚀 [{request_id}] POST /index - Starting document indexing request")
    app_logger.info(f"   Request IP: {request.remote_addr}")
    app_logger.info(f"   User Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    start_time = time.time()
    
    try:
        # Handle file uploads
        if 'files' in request.files:
            files = request.files.getlist('files')
            app_logger.info(f"📁 [{request_id}] File upload detected: {len(files)} files")
            
            if files and files[0].filename != '':
                uploaded_files = []
                for i, file in enumerate(files, 1):
                    if file and file.filename != '':
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(DOCS_DIR, filename)
                        
                        upload_start = time.time()
                        file.save(file_path)
                        upload_time = time.time() - upload_start
                        
                        file_size = os.path.getsize(file_path)
                        uploaded_files.append(filename)
                        app_logger.info(f"   📄 [{i}/{len(files)}] Uploaded: {filename} ({file_size:,} bytes, {upload_time:.2f}s)")
                
                if uploaded_files:
                    app_logger.info(f"✅ [{request_id}] Successfully uploaded {len(uploaded_files)} files")
                    
                    # Incremental indexing
                    indexing_logger.info(f"🔄 [{request_id}] Starting incremental indexing after upload")
                    success, result = index_documents_incremental()
                    
                    elapsed = time.time() - start_time
                    if not success:
                        app_logger.error(f"❌ [{request_id}] Indexing failed after {elapsed:.2f}s: {result}")
                        return jsonify({"error": f"Failed to index documents: {result}"}), 500
                    
                    result["uploaded_files"] = uploaded_files
                    result["request_id"] = request_id
                    result["processing_time"] = elapsed
                    
                    app_logger.info(f"🎉 [{request_id}] Upload and indexing completed successfully in {elapsed:.2f}s")
                    return jsonify(result)
        
        # Scan for new/modified documents in DOCS_DIR
        app_logger.info(f"📂 [{request_id}] Scanning for document changes in {DOCS_DIR}")
        
        if not os.path.exists(DOCS_DIR):
            app_logger.error(f"❌ [{request_id}] Documents directory not found: {DOCS_DIR}")
            return jsonify({"error": f"Documents directory {DOCS_DIR} not found"}), 400
        
        # Check what needs indexing before running
        files_to_index, files_to_remove, current_files = get_files_to_index()
        
        if not files_to_index and not files_to_remove:
            catalog = load_document_catalog()
            elapsed = time.time() - start_time
            
            app_logger.info(f"✅ [{request_id}] No changes detected - all documents up to date ({elapsed:.2f}s)")
            return jsonify({
                "message": "No changes detected - all documents are up to date",
                "indexed_files": len(catalog["indexed_files"]),
                "total_chunks": catalog["total_chunks"],
                "request_id": request_id,
                "processing_time": elapsed
            })
        
        # Perform incremental indexing
        indexing_logger.info(f"🔄 [{request_id}] Starting incremental indexing")
        success, result = index_documents_incremental()
        
        elapsed = time.time() - start_time
        if not success:
            app_logger.error(f"❌ [{request_id}] Indexing failed after {elapsed:.2f}s: {result}")
            return jsonify({"error": f"Failed to index documents: {result}"}), 500
        
        result["request_id"] = request_id
        result["processing_time"] = elapsed
        
        app_logger.info(f"🎉 [{request_id}] Incremental indexing completed successfully in {elapsed:.2f}s")
        return jsonify(result)
        
    except Exception as e:
        elapsed = time.time() - start_time
        app_logger.error(f"❌ [{request_id}] Indexing request failed after {elapsed:.2f}s: {e}")
        app_logger.error(f"   Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Indexing failed: {str(e)}", "request_id": request_id}), 500

@app.route('/query', methods=['POST'])
def search_documents():
    """Query indexed documents and return AI-generated answers."""
    request_id = f"req_{int(time.time())}"
    query_logger.info(f"🔍 [{request_id}] POST /query - Starting search request")
    query_logger.info(f"   Request IP: {request.remote_addr}")
    
    start_time = time.time()
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            query = data.get('query')
            top_k = data.get('top_k', 5)
            query_logger.debug(f"📋 [{request_id}] JSON request - Query: '{query}', top_k: {top_k}")
        else:
            query = request.form.get('query')
            top_k = int(request.form.get('top_k', 5))
            query_logger.debug(f"📋 [{request_id}] Form request - Query: '{query}', top_k: {top_k}")
        
        if not query:
            query_logger.warning(f"⚠️  [{request_id}] Empty query provided")
            return jsonify({"error": "Query parameter is required", "request_id": request_id}), 400
        
        query_logger.info(f"🔍 [{request_id}] Processing query: '{query}' (top_k: {top_k})")
        
        # Perform search
        success, result = query_documents(query, top_k)
        
        elapsed = time.time() - start_time
        
        if not success:
            query_logger.error(f"❌ [{request_id}] Query failed after {elapsed:.2f}s: {result}")
            return jsonify({"error": result, "request_id": request_id}), 500
        
        query_logger.info(f"✅ [{request_id}] Query completed successfully in {elapsed:.2f}s")
        query_logger.info(f"   Sources found: {len(result.get('sources', []))}")
        query_logger.info(f"   Answer length: {len(result.get('answer', ''))} characters")
        
        # Handle form submission (return HTML)
        if not request.is_json:
            html_result = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Search Results</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .query {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .answer {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .sources {{ margin-top: 20px; }}
                    .source {{ background: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 3px; }}
                    a {{ color: #1976d2; text-decoration: none; }}
                    .meta {{ font-size: 0.8em; color: #666; margin-top: 10px; }}
                </style>
            </head>
            <body>
                <a href="/">&larr; Back to Search</a>
                
                <div class="query">
                    <h3>Query:</h3>
                    <p>{query}</p>
                    <div class="meta">Request ID: {request_id} | Processing time: {elapsed:.2f}s</div>
                </div>
                
                <div class="answer">
                    <h3>Answer:</h3>
                    <p>{result['answer'].replace(chr(10), '<br>')}</p>
                </div>
                
                <div class="sources">
                    <h3>Sources:</h3>
            """
            
            for source in result['sources']:
                html_result += f"""
                    <div class="source">
                        <strong>{source['doc_name']}</strong> (Chunk {source['chunk_id']})<br>
                        <em>{source['summary']}</em>
                    </div>
                """
            
            html_result += """
                </div>
            </body>
            </html>
            """
            return html_result
        
        # Return JSON for API calls
        return jsonify({
            "query": query,
            "answer": result['answer'],
            "sources": result['sources'],
            "request_id": request_id,
            "processing_time": elapsed
        })
        
    except Exception as e:
        elapsed = time.time() - start_time
        query_logger.error(f"❌ [{request_id}] Query request failed after {elapsed:.2f}s: {e}")
        query_logger.error(f"   Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Query failed: {str(e)}", "request_id": request_id}), 500

@app.route('/catalog', methods=['GET'])
def view_catalog():
    """View detailed document catalog."""
    try:
        catalog = load_document_catalog()
        files_to_index, files_to_remove, current_files = get_files_to_index()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Document Catalog</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #e3f2fd; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .file-entry {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4caf50; }}
                .file-entry.needs-update {{ border-left-color: #ff9800; }}
                .file-entry.new {{ border-left-color: #2196f3; }}
                .file-entry.removed {{ border-left-color: #f44336; }}
                .status {{ font-weight: bold; padding: 5px 10px; border-radius: 3px; color: white; }}
                .status.indexed {{ background: #4caf50; }}
                .status.needs-update {{ background: #ff9800; }}
                .status.new {{ background: #2196f3; }}
                .status.removed {{ background: #f44336; }}
                .metadata {{ font-size: 0.9em; color: #666; margin-top: 10px; }}
                .actions {{ margin-top: 20px; }}
                button {{ padding: 10px 15px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; }}
                button:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Document Catalog</h1>
                <p><strong>Total Indexed Files:</strong> {len(catalog['indexed_files'])}</p>
                <p><strong>Total Chunks:</strong> {catalog['total_chunks']}</p>
                <p><strong>Last Updated:</strong> {catalog['last_updated']}</p>
                <p><strong>Files Needing Update:</strong> {len(files_to_index)}</p>
                <p><strong>Files to Remove:</strong> {len(files_to_remove)}</p>
            </div>
            
            <div class="actions">
                <a href="/"><button>← Back to Home</button></a>
                <form style="display: inline;" action="/index" method="post">
                    <button type="submit">Update Index</button>
                </form>
                <form style="display: inline;" action="/force-reindex" method="post">
                    <button type="submit" style="background: #dc3545;">Force Full Reindex</button>
                </form>
            </div>
        """
        
        # Show files that need updating
        if files_to_index:
            html += "<h2>Files Needing Update:</h2>"
            for filename in files_to_index:
                status = "new" if filename not in catalog['indexed_files'] else "needs-update"
                status_text = "NEW" if filename not in catalog['indexed_files'] else "MODIFIED"
                
                file_info = current_files.get(filename, {})
                html += f"""
                <div class="file-entry {status}">
                    <h3>{filename} <span class="status {status}">{status_text}</span></h3>
                    <div class="metadata">
                        Size: {file_info.get('size', 0):,} bytes<br>
                        Modified: {datetime.fromtimestamp(file_info.get('modified_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if file_info.get('modified_time') else 'Unknown'}<br>
                        Hash: {file_info.get('hash', 'Unknown')[:16]}...
                    </div>
                </div>
                """
        
        # Show files to be removed
        if files_to_remove:
            html += "<h2>Files to Remove (deleted from disk):</h2>"
            for filename in files_to_remove:
                old_info = catalog['indexed_files'].get(filename, {})
                html += f"""
                <div class="file-entry removed">
                    <h3>{filename} <span class="status removed">DELETED</span></h3>
                    <div class="metadata">
                        Was indexed: {old_info.get('indexed_time', 'Unknown')}<br>
                        Had chunks: {old_info.get('chunks_count', 0)}
                    </div>
                </div>
                """
        
        # Show currently indexed files
        html += "<h2>Currently Indexed Files:</h2>"
        for filename, info in catalog['indexed_files'].items():
            if filename not in files_to_remove:
                status = "indexed"
                if filename in files_to_index:
                    status = "needs-update"
                
                html += f"""
                <div class="file-entry {status}">
                    <h3>{filename} <span class="status {status}">{'NEEDS UPDATE' if status == 'needs-update' else 'INDEXED'}</span></h3>
                    <div class="metadata">
                        Chunks: {info.get('chunks_count', 0)}<br>
                        Size: {info.get('size', 0):,} bytes<br>
                        Indexed: {info.get('indexed_time', 'Unknown')}<br>
                        Hash: {info.get('hash', 'Unknown')[:16]}...
                    </div>
                </div>
                """
        
        html += """
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return jsonify({"error": f"Failed to load catalog: {str(e)}"}), 500

@app.route('/status', methods=['GET'])
def status():
    """Get indexing status and statistics."""
    try:
        catalog = load_document_catalog()
        files_to_index, files_to_remove, current_files = get_files_to_index()
        
        stats = {
            "lucene_index_exists": os.path.exists(LUCENE_INDEX_DIR),
            "embeddings_index_exists": os.path.exists(INDEX_FILE),
            "catalog_exists": os.path.exists(CATALOG_FILE),
            "docs_directory": DOCS_DIR,
            "documents_on_disk": len(current_files),
            "documents_indexed": len(catalog["indexed_files"]),
            "total_chunks": catalog["total_chunks"],
            "files_needing_update": len(files_to_index),
            "files_to_remove": len(files_to_remove),
            "last_updated": catalog["last_updated"],
            "up_to_date": len(files_to_index) == 0 and len(files_to_remove) == 0
        }
        
        # Detailed file information
        stats["file_details"] = {
            "on_disk": list(current_files.keys()),
            "indexed": list(catalog["indexed_files"].keys()),
            "needs_update": files_to_index,
            "to_remove": files_to_remove
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": f"Status check failed: {str(e)}"}), 500

@app.route('/upload-and-index', methods=['POST'])
def upload_and_index_single():
    """Upload a single document, index it immediately, and prepare for querying."""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided. Use 'file' field."}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.txt', '.md'}
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({
                "error": f"Unsupported file type: {file_ext}. Supported: {', '.join(allowed_extensions)}"
            }), 400
        
        # Save file to docs directory
        file_path = os.path.join(DOCS_DIR, filename)
        file.save(file_path)
        
        print(f"📄 Uploaded file: {filename}")
        
        # Get file info before indexing
        file_info = get_file_info(file_path)
        if not file_info:
            return jsonify({"error": "Failed to read file information"}), 500
        
        # Check if this file was already indexed
        catalog = load_document_catalog()
        was_already_indexed = filename in catalog["indexed_files"]
        
        # Extract text to verify file is readable
        extracted_text = extract_text_from_file(file_path)
        if not extracted_text:
            # Clean up the uploaded file
            os.remove(file_path)
            return jsonify({
                "error": f"No text could be extracted from {filename}. File may be corrupted or empty."
            }), 400
        
        text_preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
        
        # Index this specific file
        success, result = index_single_document(filename, file_path, file_info)
        
        if not success:
            # Clean up on failure
            os.remove(file_path)
            return jsonify({"error": f"Failed to index document: {result}"}), 500
        
        # Return detailed response
        response = {
            "message": "Document uploaded and indexed successfully",
            "filename": filename,
            "file_size": file_info["size"],
            "file_type": file_ext,
            "text_preview": text_preview,
            "was_already_indexed": was_already_indexed,
            "indexing_result": result,
            "ready_for_queries": True,
            "next_steps": {
                "query_endpoint": "/query",
                "example_query": f"What is the main topic of {filename}?",
                "view_catalog": "/catalog"
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        # Clean up uploaded file on any error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": f"Upload and indexing failed: {str(e)}"}), 500

def index_single_document(filename, file_path, file_info):
    """Index a single document and update the catalog."""
    try:
        # Create temporary directory with just this file
        temp_docs_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_docs_dir, filename)
        shutil.copy2(file_path, temp_file_path)
        
        # Build Lucene index for this file
        lucene_input = {
            "action": "index-dir",
            "docs_dir": temp_docs_dir,
            "index_dir": LUCENE_INDEX_DIR
        }
        
        with open(LUCENE_INPUT_FILE, "w") as f:
            json.dump(lucene_input, f)
        
        # Run Java indexer
        classpath = (
            f".:"
            f"{LIBS}/lucene-core-9.12.2.jar:"
            f"{LIBS}/lucene-analyzers-common-9.12.2.jar:"
            f"{LIBS}/lucene-queryparser-9.12.2.jar:"
            f"{LIBS}/gson-2.10.1.jar:"
            f"{LIBS}/pdfbox-3.0.5.jar:"
            f"{LIBS}/pdfbox-io-3.0.5.jar:"
            f"{LIBS}/fontbox-3.0.5.jar:"
            f"{LIBS}/poi-4.1.2.jar:"
            f"{LIBS}/poi-ooxml-4.1.2.jar:"
            f"{LIBS}/poi-scratchpad-4.1.2.jar:"
            f"{LIBS}/xmlbeans-3.1.0.jar:"
            f"{LIBS}/compress-1.9.2.jar:"
            f"{LIBS}/commons-collections4-4.4.jar:"
            f"{LIBS}/poi-ooxml-schemas-4.1.2.jar"
        )
        
        result = subprocess.run(
            ["java", "-cp", classpath, JAVA_CLASS, LUCENE_INPUT_FILE],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Load existing embeddings
        existing_embeddings = []
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "r") as f:
                existing_embeddings = json.load(f)
        
        # Remove old embeddings for this file if it was re-uploaded
        existing_embeddings = [emb for emb in existing_embeddings 
                              if emb["doc_name"] != filename]
        
        # Load new chunk metadata
        if not os.path.exists(LUCENE_CHUNKS_FILE):
            return False, "Failed to generate chunks"
        
        with open(LUCENE_CHUNKS_FILE, "r") as f:
            all_chunks = json.load(f)
        
        # Filter chunks for this specific file
        new_chunks = [chunk for chunk in all_chunks if chunk["doc_name"] == filename]
        
        if not new_chunks:
            return False, "No chunks generated for this file"
        
        # Extract document text
        doc_text = extract_text_from_file(file_path)
        
        # Generate embeddings for new chunks
        contextualized_chunks = [
            f"Document: {chunk['doc_name']}, Chunk {chunk['chunk_id']}\n"
            f"Keywords: {', '.join(chunk['keywords'])}\n"
            f"Summary: {generate_summary(chunk['content'])}\n\n"
            f"{chunk['content']}"
            for chunk in new_chunks
        ]
        
        print(f"🧮 Generating embeddings for {len(contextualized_chunks)} chunks...")
        embeddings = embedding_model.encode(contextualized_chunks, batch_size=32, show_progress_bar=False)
        
        # Create embedding entries
        new_embeddings = []
        for i, chunk in enumerate(new_chunks):
            summary = generate_summary(chunk['content'])
            qa_pairs = generate_qa_pairs(chunk['content'], doc_text)
            embedding = embeddings[i].tolist() if i < len(embeddings) else None
            
            if embedding:
                new_embeddings.append({
                    "doc_name": chunk["doc_name"],
                    "chunk_id": chunk["chunk_id"],
                    "chunk": chunk["content"],
                    "summary": summary,
                    "keywords": chunk["keywords"],
                    "qa_pairs": qa_pairs,
                    "embedding": embedding
                })
        
        # Merge with existing embeddings
        all_embeddings = existing_embeddings + new_embeddings
        
        # Save updated embeddings
        with open(INDEX_FILE, "w") as f:
            json.dump(all_embeddings, f)
        
        # Update catalog
        catalog = load_document_catalog()
        catalog["indexed_files"][filename] = {
            "hash": file_info["hash"],
            "size": file_info["size"],
            "modified_time": file_info["modified_time"],
            "chunks_count": len(new_chunks),
            "indexed_time": datetime.now().isoformat()
        }
        catalog["total_chunks"] = len(all_embeddings)
        save_document_catalog(catalog)
        
        # Clean up temp directory
        shutil.rmtree(temp_docs_dir, ignore_errors=True)
        
        return True, {
            "chunks_created": len(new_chunks),
            "embeddings_generated": len(new_embeddings),
            "total_chunks_in_index": len(all_embeddings)
        }
        
    except subprocess.CalledProcessError as e:
        return False, f"Java indexer error: {e.stderr}"
    except Exception as e:
        return False, f"Indexing error: {str(e)}"
    finally:
        # Always clean up temp directory
        if 'temp_docs_dir' in locals():
            shutil.rmtree(temp_docs_dir, ignore_errors=True)
    """Force a complete reindex of all documents."""
    try:
        # Clear existing catalog and indexes
        if os.path.exists(CATALOG_FILE):
            os.remove(CATALOG_FILE)
        if os.path.exists(INDEX_FILE):
            os.remove(INDEX_FILE)
        if os.path.exists(LUCENE_CHUNKS_FILE):
            os.remove(LUCENE_CHUNKS_FILE)
        
        # Remove Lucene index directory
        if os.path.exists(LUCENE_INDEX_DIR):
            shutil.rmtree(LUCENE_INDEX_DIR)
            os.makedirs(LUCENE_INDEX_DIR, exist_ok=True)
        
        # Perform fresh indexing
        success, result = index_documents_incremental()
        if not success:
            return jsonify({"error": f"Failed to reindex documents: {result}"}), 500
        
        result["message"] = "Complete reindex successful"
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Force reindex failed: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "anthropic": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your-anthropic-api-key"),
                "sentence_transformers": True,  # Loaded at startup
                "lucene": os.path.exists(f"{LIBS}/lucene-core-9.12.2.jar"),
                "docs_directory": os.path.exists(DOCS_DIR)
            }
        }
        
        # Check if indexes exist
        health["indexes"] = {
            "lucene": os.path.exists(LUCENE_INDEX_DIR),
            "embeddings": os.path.exists(INDEX_FILE),
            "catalog": os.path.exists(CATALOG_FILE)
        }
        
        return jsonify(health)
        
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Auto-check for changes on startup
def startup_check():
    """Check for changes when the app starts."""
    app_logger.info("=" * 60)
    app_logger.info("🚀 STARTING DOCUMENT SEARCH API")
    app_logger.info("=" * 60)
    
    try:
        # System info
        app_logger.info(f"🖥️  System Information:")
        app_logger.info(f"   • Python version: {sys.version}")
        app_logger.info(f"   • Working directory: {os.getcwd()}")
        app_logger.info(f"   • Log file: document_search.log")
        
        # Check dependencies
        app_logger.info("🔍 Checking dependencies...")
        
        # Check JAR files
        jar_files = [
            "lucene-core-9.12.2.jar",
            "lucene-analyzers-common-9.12.2.jar", 
            "lucene-queryparser-9.12.2.jar",
            "gson-2.10.1.jar",
            "pdfbox-3.0.5.jar",
            "pdfbox-io-3.0.5.jar",
            "fontbox-3.0.5.jar",
            "poi-4.1.2.jar",
            "poi-ooxml-4.1.2.jar",
            "poi-scratchpad-4.1.2.jar",
            "poi-ooxml-schemas-4.1.2.jar",
            "xmlbeans-3.1.0.jar",
            "compress.1.9.2.jar",
            "commons-collections4-4.4.jar"
        ]
        
        missing_jars = []
        for jar in jar_files:
            jar_path = os.path.join(LIBS, jar)
            if os.path.exists(jar_path):
                app_logger.debug(f"   ✅ {jar}")
            else:
                missing_jars.append(jar)
                app_logger.warning(f"   ❌ MISSING: {jar}")
        
        if missing_jars:
            app_logger.error(f"⚠️  Missing {len(missing_jars)} required JAR files!")
            app_logger.error("   Please ensure all dependencies are in ./libs/ directory")
        else:
            app_logger.info("✅ All JAR dependencies found")
        
        # Check API keys
        app_logger.info("🔑 Checking API configuration...")
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your-anthropic-api-key":
            app_logger.info("   ✅ Anthropic API key configured")
        else:
            app_logger.warning("   ⚠️  Anthropic API key not configured - AI features will not work")
        
        # Load catalog and check for changes
        app_logger.info("📊 Loading document catalog...")
        catalog = load_document_catalog()
        app_logger.info(f"   • Indexed files: {len(catalog['indexed_files'])}")
        app_logger.info(f"   • Total chunks: {catalog['total_chunks']}")
        app_logger.info(f"   • Last updated: {catalog['last_updated']}")
        
        # Check for changes
        app_logger.info("🔍 Scanning for document changes...")
        files_to_index, files_to_remove, current_files = get_files_to_index()
        
        if files_to_index or files_to_remove:
            app_logger.info(f"📁 Changes detected:")
            if files_to_index:
                app_logger.info(f"   • Files to index: {len(files_to_index)}")
                for f in files_to_index[:5]:  # Show first 5
                    app_logger.info(f"     - {f}")
                if len(files_to_index) > 5:
                    app_logger.info(f"     ... and {len(files_to_index) - 5} more")
            if files_to_remove:
                app_logger.info(f"   • Files to remove: {len(files_to_remove)}")
                for f in files_to_remove:
                    app_logger.info(f"     - {f}")
            app_logger.info("   💡 Run POST /index to update the index")
        else:
            app_logger.info("✅ All documents are up to date")
        
        # Startup complete
        app_logger.info("=" * 60)
        app_logger.info("🌐 SERVER READY")
        app_logger.info("=" * 60)
        app_logger.info("📍 Available endpoints:")
        app_logger.info("   • GET  /           - Web interface")
        app_logger.info("   • POST /index      - Index documents")
        app_logger.info("   • POST /upload-and-index - Upload & index single file")
        app_logger.info("   • POST /query      - Search documents")
        app_logger.info("   • GET  /catalog    - View document catalog")
        app_logger.info("   • GET  /status     - System status")
        app_logger.info("   • GET  /health     - Health check")
        app_logger.info(f"🌐 Server ready at http://localhost:8000")
        app_logger.info("=" * 60)
        
    except Exception as e:
        app_logger.error(f"⚠️  Startup check failed: {e}")
        app_logger.error(f"   Traceback: {traceback.format_exc()}")

# Run startup check when app context is available
with app.app_context():
    startup_check()

if __name__ == '__main__':
    print("🔍 Document Search API")
    print("=" * 50)
    
    # Additional startup logging
    app_logger.info("🎬 Starting Flask development server...")
    app_logger.info("   • Debug mode: True")
    app_logger.info("   • Host: 0.0.0.0")
    app_logger.info("   • Port: 8000")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
