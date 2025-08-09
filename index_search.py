import json
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_index_file():
    """Prompt user for the location of the index file."""
    while True:
        index_file = input("Enter the path to the index file (default: image_index.json): ").strip()
        if not index_file:
            index_file = "image_index.json"
        
        # Expand user home directory if needed
        index_file = os.path.expanduser(index_file)
        
        if os.path.isfile(index_file):
            logger.info(f"Using index file: {index_file}")
            return index_file
        else:
            print(f"File {index_file} does not exist. Please enter a valid file path.")

def create_query_vector(query, vocabulary):
    """Create a binary vector for the search query."""
    # Split query and convert to lowercase
    query_keywords = [kw.strip().lower() for kw in query.split()]
    
    # Create binary vector
    vector = []
    matched_keywords = []
    unmatched_keywords = []
    
    for vocab_word in vocabulary:
        if vocab_word in query_keywords:
            vector.append(1)
            matched_keywords.append(vocab_word)
        else:
            vector.append(0)
    
    # Find keywords that weren't in vocabulary
    for kw in query_keywords:
        if kw not in vocabulary:
            unmatched_keywords.append(kw)
    
    logger.info(f"Query matched keywords: {matched_keywords}")
    if unmatched_keywords:
        logger.warning(f"Query keywords not in vocabulary: {unmatched_keywords}")
    
    return vector, matched_keywords, unmatched_keywords

def jaccard_similarity(vec1, vec2):
    """Calculate Jaccard similarity between two binary vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    intersection = np.sum(vec1 & vec2)
    union = np.sum(vec1 | vec2)
    
    if union == 0:
        return 0.0
    return intersection / union

def hamming_similarity(vec1, vec2):
    """Calculate Hamming similarity (1 - normalized Hamming distance)."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    matches = np.sum(vec1 == vec2)
    return matches / len(vec1)

def requires_all_keywords(query_vector, image_vector, query_matched_keywords):
    """Check if image contains ALL query keywords."""
    for i, query_bit in enumerate(query_vector):
        if query_bit == 1 and image_vector[i] == 0:
            return False
    return True

def search_images(query, index_file=None, similarity_threshold=0.1, similarity_method="cosine", match_mode="any", show_fallback=True):
    """Search for images with binary vectors using different similarity measures."""
    try:
        # Get index file path if not provided
        if index_file is None:
            index_file = get_index_file()
        
        # Load index
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        images = index['images']
        vocabulary = index['vocabulary']
        vector_type = index.get('vector_type', 'tfidf')
        
        logger.info(f"Loaded index with {len(images)} images and vector type: {vector_type}")
        
        # Create query vector
        query_vector, query_matched_keywords, unmatched_keywords = create_query_vector(query, vocabulary)
        
        if not query_matched_keywords:
            logger.warning("No query keywords found in vocabulary!")
            return []
        
        # Verify query vector length
        if len(query_vector) != 100:
            logger.warning(f"Query vector has {len(query_vector)} dimensions, expected 100")
        
        # Compare query vector with image vectors
        all_results = []  # Store all results for fallback
        results = []
        
        for image in images:
            image_vector = image['keyword_vector']
            if len(image_vector) != 100:
                logger.warning(f"Image {image['name']} vector has {len(image_vector)} dimensions, expected 100")
                continue
            
            # Calculate similarity based on chosen method
            if similarity_method == "cosine":
                similarity = cosine_similarity([query_vector], [image_vector])[0][0]
            elif similarity_method == "jaccard":
                similarity = jaccard_similarity(query_vector, image_vector)
            elif similarity_method == "hamming":
                similarity = hamming_similarity(query_vector, image_vector)
            else:
                logger.error(f"Unknown similarity method: {similarity_method}")
                return []
            
            # Find matching keywords for this image
            matching_keywords = []
            for i, (q_bit, img_bit) in enumerate(zip(query_vector, image_vector)):
                if q_bit == 1 and img_bit == 1:
                    matching_keywords.append(vocabulary[i])
            
            # Calculate match percentage
            match_percentage = len(matching_keywords) / len(query_matched_keywords) if query_matched_keywords else 0
            
            result = {
                'name': image['name'],
                'full_path': image['full_path'],
                'similarity': round(similarity, 4),
                'keywords': image['keywords'],
                'matching_keywords': matching_keywords,
                'match_percentage': round(match_percentage, 4),
                'query_keywords_found': f"{len(matching_keywords)}/{len(query_matched_keywords)}",
                'file_type': image['file_type'],
                'date_created': image['date_created'],
                'author': image['author']
            }
            
            # Store all results for potential fallback
            all_results.append(result)
            
            # Apply match mode filter and similarity threshold
            passes_match_mode = True
            if match_mode == "all":
                passes_match_mode = requires_all_keywords(query_vector, image_vector, query_matched_keywords)
            
            if passes_match_mode and similarity >= similarity_threshold:
                results.append(result)
        
        # Sort results by similarity (descending)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        if not results:
            logger.info(f"No images found with {similarity_method} similarity >= {similarity_threshold:.2%} and match mode '{match_mode}'")
        else:
            logger.info(f"Found {len(results)} images with {similarity_method} similarity >= {similarity_threshold:.2%} and match mode '{match_mode}'")
            for result in results:
                logger.info(f"Image: {result['name']}, Similarity: {result['similarity']:.2%}, Matches: {result['query_keywords_found']} ({result['matching_keywords']})")
        
        return results
    
    except FileNotFoundError:
        logger.error(f"Index file {index_file} not found")
        return []
    except Exception as e:
        logger.error(f"Error searching images: {e}")
        return []

if __name__ == "__main__":
    # Get index file location
    index_file = get_index_file()
    
    # Get search query
    query = input("Enter search query (e.g., 'card online payment'): ").strip() or "card online payment"
    
    # Get match mode
    print("\nMatch modes:")
    print("1. any - Match images that contain ANY of the query keywords")
    print("2. all - Match images that contain ALL of the query keywords")
    
    match_choice = input("Choose match mode (1-2, default: 1): ").strip()
    match_mode = "all" if match_choice == "2" else "any"
    
    # Get similarity method
    print("\nSimilarity methods:")
    print("1. cosine - Cosine similarity (good for TF-IDF and binary)")
    print("2. jaccard - Jaccard similarity (ideal for binary vectors)")
    print("3. hamming - Hamming similarity (based on exact matches)")
    
    method_choice = input("Choose similarity method (1-3, default: 2): ").strip()
    method_map = {"1": "cosine", "2": "jaccard", "3": "hamming"}
    similarity_method = method_map.get(method_choice, "jaccard")
    
    # Get similarity threshold
    threshold_input = input("Enter similarity threshold (0.0-1.0, default: 0.1): ").strip()
    try:
        similarity_threshold = float(threshold_input) if threshold_input else 0.1
    except ValueError:
        similarity_threshold = 0.1
    
    # Perform search
    results = search_images(query, index_file, similarity_threshold, similarity_method, match_mode)
    if results:
        print(f"\nMatching images (using {similarity_method} similarity, {match_mode} match mode):")
        for i, result in enumerate(results, 1):
            match_type = "🎯 EXACT" if result['similarity'] >= similarity_threshold else "📍 CLOSEST"
            print(f"{i}. {match_type} - {result['name']} ({result['similarity']:.1%} similarity)")
            print(f"   Path: {result['full_path']}")
            print(f"   Query keywords found: {result['query_keywords_found']} - {', '.join(result['matching_keywords'])}")
            print(f"   Match percentage: {result['match_percentage']:.1%}")
            print(f"   All keywords: {result['keywords']}")
            print()
    else:
        print("No matching images found.")
