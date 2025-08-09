import os
import json
from pathlib import Path
import logging
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def extract_keywords_from_jsons(directory):
    """Extract all unique keywords from JSON files in the directory."""
    all_keywords = set()
    
    logger.info(f"Extracting keywords from JSON files in: {directory}")
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.json'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    if 'keywords' in data:
                        if isinstance(data['keywords'], list):
                            keywords = data['keywords']
                        elif isinstance(data['keywords'], str):
                            keywords = data['keywords'].strip().split()
                        else:
                            continue
                        
                        # Add lowercase keywords and log them
                        file_keywords = []
                        for kw in keywords:
                            clean_kw = kw.strip().lower()
                            all_keywords.add(clean_kw)
                            file_keywords.append(clean_kw)
                        
                        logger.info(f"  {file}: {file_keywords}")
                            
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
    
    result = sorted(list(all_keywords))
    logger.info(f"All unique keywords found: {result}")
    return result

def get_user_keywords(num_keywords=100, keywords_file="keywords.txt", directory=None, use_json_keywords=True):
    """Read 100 unique keywords from file, extract from JSON files, or prompt user."""
    
    # First, try to extract keywords from JSON files if enabled and directory is provided
    if use_json_keywords and directory:
        json_keywords = extract_keywords_from_jsons(directory)
        if json_keywords:
            logger.info(f"Found {len(json_keywords)} unique keywords in JSON files: {', '.join(json_keywords)}...")
            if len(json_keywords) >= num_keywords:
                logger.info(f"Using first {num_keywords} keywords from JSON files")
                return json_keywords[:num_keywords]
            else:
                logger.info(f"Using all {len(json_keywords)} keywords from JSON files and padding with defaults")
                padded_keywords = json_keywords[:]
                padded_keywords.extend([f"keyword{i}" for i in range(len(json_keywords) + 1, num_keywords + 1)])
                return padded_keywords
        else:
            logger.warning("No keywords found in JSON files, falling back to keywords file")
    
    # If no JSON keywords or directory not provided, try keywords file
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

def create_binary_vector(keywords_text, vocabulary):
    """Create a binary vector based on keyword presence."""
    # Split keywords and convert to lowercase
    keywords = [kw.strip().lower() for kw in keywords_text.split()]
    
    # Debug logging
    logger.debug(f"Creating vector for keywords: {keywords}")
    logger.debug(f"Vocabulary (first 20): {vocabulary[:20]}")
    
    # Create binary vector
    vector = []
    found_keywords = []
    for vocab_word in vocabulary:
        if vocab_word in keywords:
            vector.append(1)
            found_keywords.append(vocab_word)
        else:
            vector.append(0)
    
    # Also check if any keywords weren't found in vocabulary
    missing_keywords = [kw for kw in keywords if kw not in vocabulary]
    if missing_keywords:
        logger.warning(f"Keywords not in vocabulary: {missing_keywords}")
    
    return vector, found_keywords

def index_images(directory=None, output_json=None, use_json_keywords=True):
    """Index JSON files with image metadata, computing 100-dimensional binary vectors."""
    try:
        # Prompt for directory if not provided
        if directory is None:
            directory = get_valid_directory()
        
        # Get output file path if not provided
        if output_json is None:
            output_json = get_output_file()
        
        # Log the directory being scanned
        logger.info(f"Scanning directory: {directory}")
        
        # Get 100 unique keywords (this will be our vocabulary)
        vocabulary = get_user_keywords(100)
        logger.info(f"Using vocabulary: {', '.join(vocabulary[:5])}... (first 5 shown)")
        
        # Collect metadata
        metadata_list = []
        
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
                            keywords_text = ' '.join(data['keywords'])
                        elif isinstance(data['keywords'], str):
                            keywords_text = data['keywords']
                        else:
                            logger.warning(f"Skipping {file_path}: 'keywords' must be a string or list")
                            continue
                        
                        # Create binary vector
                        binary_vector, found_keywords = create_binary_vector(keywords_text, vocabulary)
                        
                        metadata = {
                            'name': data['name'],
                            'full_path': data['full_path'],
                            'file_type': data.get('file_type', 'image/png'),
                            'date_created': data.get('date_created', 'Unknown'),
                            'author': data.get('author', 'Unknown'),
                            'keywords': keywords_text,
                            'keyword_vector': binary_vector
                        }
                        
                        metadata_list.append(metadata)
                        
                        # Log which keywords were found
                        logger.info(f"Indexed: {file_path} (Image: {data['name']}) - Found keywords: {found_keywords}")
                        
                    except Exception as e:
                        logger.warning(f"Error processing {file_path}: {e}")
        
        if not metadata_list:
            logger.warning("No valid JSON files found in directory")
            return
        
        # Verify all vectors are 100-dimensional
        for metadata in metadata_list:
            if len(metadata['keyword_vector']) != 100:
                logger.warning(f"Vector for {metadata['name']} has {len(metadata['keyword_vector'])} dimensions, expected 100")
        
        # Save metadata to JSON in current directory
        try:
            with open(output_json, 'w') as f:
                json.dump({
                    'images': metadata_list,
                    'vocabulary': vocabulary,  # Store the ordered vocabulary
                    'vector_type': 'binary'    # Mark this as binary vectors
                }, f, indent=2)
            logger.info(f"Successfully saved binary index to {output_json}")
            logger.info(f"Indexed {len(metadata_list)} images with {len(vocabulary)} keyword positions")
        except Exception as e:
            logger.error(f"Error saving index to {output_json}: {e}")
            
    except Exception as e:
        logger.error(f"Error indexing directory {directory}: {e}")

if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Ask user about keyword source
    print("Keyword source options:")
    print("1. Extract keywords from JSON files (recommended)")
    print("2. Use keywords.txt file")
    choice = input("Choose keyword source (1-2, default: 1): ").strip()
    use_json_keywords = choice != "2"
    
    index_images(directory, use_json_keywords=use_json_keywords)

