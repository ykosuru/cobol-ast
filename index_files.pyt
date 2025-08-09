import os
import json
from pathlib import Path
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_user_keywords(num_keywords=100, keywords_file="keywords.txt"):
    """Read 100 unique keywords from file or prompt user."""
    try:
        with open(keywords_file, 'r') as f:
            keywords = []
            for line in f:
                line_keywords = [kw.strip().lower() for kw in line.split() if kw.strip()]
                if not line_keywords:
                    logger.warning(f"Empty or invalid line in {keywords_file}: {line.strip()}")
                keywords.extend(line_keywords)
            keywords = list(set(keywords))  # Remove duplicates
        if not keywords:
            logger.warning(f"No valid keywords found in {keywords_file}; using defaults")
            keywords = [f"keyword{i}" for i in range(1, num_keywords + 1)]
        elif len(keywords) < num_keywords:
            logger.warning(f"Only {len(keywords)} unique keywords found in {keywords_file}; padding with defaults")
            keywords.extend([f"keyword{i}" for i in range(len(keywords) + 1, num_keywords + 1)])
        elif len(keywords) > num_keywords:
            logger.warning(f"More than {num_keywords} keywords in {keywords_file}; using first {num_keywords}")
        return keywords[:num_keywords]
    except FileNotFoundError:
        logger.warning(f"{keywords_file} not found; prompting for keywords")
        return get_user_keywords_manual(num_keywords)

def get_user_keywords_manual(num_keywords=100):
    """Prompt user to input 100 unique keywords."""
    print(f"Please enter {num_keywords} unique keywords (one per line). Press Enter without input to use default keywords.")
    keywords = set()
    default_keywords = [f"keyword{i}" for i in range(1, num_keywords + 1)]
    i = 1
    while len(keywords) < num_keywords:
        keyword = input(f"Enter keyword {i}/{num_keywords}: ").strip().lower()
        if not keyword:
            logger.warning("Not enough keywords provided; filling with defaults")
            keywords.update(default_keywords[len(keywords):num_keywords])
            break
        if keyword not in keywords:
            keywords.add(keyword)
            i += 1
        else:
            print(f"Keyword '{keyword}' already entered; please provide a unique keyword.")
    return list(keywords)[:num_keywords]

def get_valid_directory():
    """Prompt user for a valid directory containing JSON files."""
    while True:
        directory = input("Enter the directory containing JSON files (e.g., /Users/ykosuru/Documents/image_indexing): ").strip()
        if not directory:
            directory = "."
        directory = os.path.expanduser(directory)  # Handle ~ for home directory
        if os.path.isdir(directory):
            json_files = [f for f in os.listdir(directory) if f.lower().endswith('.json')]
            if json_files:
                logger.info(f"Found JSON files in {directory}: {json_files}")
                return directory
            else:
                print(f"No JSON files found in {directory}. Please enter a directory containing .json files.")
        else:
            print(f"Directory {directory} does not exist. Please enter a valid directory.")

def get_output_file():
    """Get the output file path, defaulting to current directory."""
    output_file = input("Enter output file name (default: image_index.json): ").strip()
    if not output_file:
        output_file = "image_index.json"
    
    # Ensure we save in current directory
    output_file = os.path.basename(output_file)  # Remove any path components
    if not output_file.endswith('.json'):
        output_file += '.json'
    
    # Get absolute path for current directory
    current_dir = os.getcwd()
    output_path = os.path.join(current_dir, output_file)
    
    logger.info(f"Output will be saved to: {output_path}")
    return output_path

def index_images(directory=None, output_json=None):
    """Index JSON files with image metadata, computing 100-dimensional quantized vectors."""
    try:
        # Prompt for directory if not provided
        if directory is None:
            directory = get_valid_directory()
        
        # Get output file path if not provided
        if output_json is None:
            output_json = get_output_file()
        
        # Log the directory being scanned
        logger.info(f"Scanning directory: {directory}")
        
        # Get 100 unique keywords
        user_keywords = get_user_keywords(100)
        logger.info(f"Using keywords: {', '.join(user_keywords[:5])}... (first 5 shown)")
        
        # Initialize TF-IDF vectorizer with user-defined vocabulary
        vectorizer = TfidfVectorizer(lowercase=True, stop_words='english', vocabulary=user_keywords)
        if len(vectorizer.vocabulary) != 100:
            logger.error(f"Vocabulary size is {len(vectorizer.vocabulary)}; expected 100")
            return
        
        # Collect metadata
        metadata_list = []
        keyword_list = []
        image_paths = []
        
        # Scan directory for JSON files
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.json'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Validate required fields
                        if not all(key in data for key in ['name', 'full_path', 'keywords']):
                            logger.warning(f"Skipping {file_path}: missing required fields")
                            continue
                        
                        # Handle keywords (list or string)
                        if isinstance(data['keywords'], list):
                            keywords = data['keywords']
                        elif isinstance(data['keywords'], str):
                            logger.warning(f"{file_path}: 'keywords' is a string; splitting into list")
                            keywords = data['keywords'].strip().split()
                        else:
                            logger.warning(f"Skipping {file_path}: 'keywords' must be a string or list")
                            continue
                        
                        metadata = {
                            'name': data['name'],
                            'full_path': data['full_path'],
                            'file_type': data.get('file_type', 'image/png'),
                            'date_created': data.get('date_created', 'Unknown'),
                            'author': data.get('author', 'Unknown'),
                            'keywords': ' '.join(keywords)
                        }
                        
                        keyword_list.append(metadata['keywords'])
                        image_paths.append(data['full_path'])
                        metadata_list.append(metadata)
                        logger.info(f"Indexed: {file_path} (Image: {data['name']})")
                    except Exception as e:
                        logger.warning(f"Error processing {file_path}: {e}")
        
        if not metadata_list:
            logger.warning("No valid JSON files found in directory")
            return
        
        # Compute 100-dimensional TF-IDF vectors
        try:
            vectorizer.fit(keyword_list)
            tfidf_matrix = vectorizer.transform(keyword_list)
            vectors = tfidf_matrix.toarray()
            vectors = np.round(vectors, 4).tolist()
        except Exception as e:
            logger.error(f"Error computing TF-IDF vectors: {e}")
            return
        
        # Add vectors to metadata
        for metadata, vector in zip(metadata_list, vectors):
            metadata['keyword_vector'] = vector
            if len(vector) != 100:
                logger.warning(f"Vector for {metadata['name']} has {len(vector)} dimensions, expected 100")
        
        # Save metadata to JSON in current directory
        try:
            with open(output_json, 'w') as f:
                json.dump({
                    'images': metadata_list,
                    'vectorizer_vocabulary': vectorizer.vocabulary_
                }, f, indent=2)
            logger.info(f"Successfully saved index to {output_json}")
            logger.info(f"Indexed {len(metadata_list)} images with {len(vectorizer.vocabulary_)} keywords")
        except Exception as e:
            logger.error(f"Error saving index to {output_json}: {e}")
            
    except Exception as e:
        logger.error(f"Error indexing directory {directory}: {e}")

if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else None
    index_images(directory)

