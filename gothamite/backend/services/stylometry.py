import math
from collections import Counter
import re

def compute_stylometric_similarity(text1: str, text2: str) -> float:
    # Bag-of-words term-frequency cosine similarity. No IDF weighting and no trained
    # model: a deterministic lexical-overlap measure used as a corroborating signal.
    def get_tokens(text):
        return re.findall(r'\b\w+\b', text.lower())
    
    t1 = get_tokens(text1)
    t2 = get_tokens(text2)
    
    if not t1 or not t2:
        return 0.0
        
    c1 = Counter(t1)
    c2 = Counter(t2)
    
    terms = set(c1.keys()).union(set(c2.keys()))
    
    dot_product = sum(c1.get(t, 0) * c2.get(t, 0) for t in terms)
    mag1 = math.sqrt(sum(c1.get(t, 0)**2 for t in terms))
    mag2 = math.sqrt(sum(c2.get(t, 0)**2 for t in terms))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
        
    return dot_product / (mag1 * mag2)
