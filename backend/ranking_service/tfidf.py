"""
TF-IDF (Term Frequency - Inverse Document Frequency) Algorithm

A statistical measure used to evaluate the importance of a word in a document
relative to a collection of documents (corpus).

Formula:
    TF-IDF(t, d, D) = TF(t, d) × IDF(t, D)

Where:
    - t = term (word)
    - d = document
    - D = corpus (collection of documents)

This module provides:
1. Term Frequency (TF) with logarithmic scaling
2. Inverse Document Frequency (IDF) with smoothing
3. TF-IDF scoring for query-document relevance
4. Query tokenization and preprocessing

Why TF-IDF?
- Simple yet effective for text relevance
- Language-independent
- Computationally efficient
- Forms the basis of many search engines
"""

import math
import re
from typing import List, Dict, Optional, Tuple
from collections import Counter
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings

# Try to use NLTK for better text processing
try:
    import nltk
    from nltk.stem import PorterStemmer
    from nltk.corpus import stopwords
    
    # Download required data
    for resource in ['punkt', 'punkt_tab', 'stopwords']:
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass
    
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass
class TFIDFScore:
    """Represents TF-IDF score for a document"""
    doc_id: str
    score: float
    term_scores: Dict[str, float]  # Individual term contributions
    
    def __repr__(self):
        return f"TFIDFScore(doc_id={self.doc_id}, score={self.score:.4f})"


class TextPreprocessor:
    """
    Text preprocessing for TF-IDF calculations
    
    Pipeline:
    1. Lowercase conversion
    2. Punctuation removal
    3. Tokenization
    4. Stopword removal
    5. Stemming (optional)
    """
    
    def __init__(self, use_stemming: bool = True, remove_stopwords: bool = True):
        self.use_stemming = use_stemming
        self.remove_stopwords_flag = remove_stopwords
        
        if NLTK_AVAILABLE and use_stemming:
            self.stemmer = PorterStemmer()
        else:
            self.stemmer = None
        
        if NLTK_AVAILABLE and remove_stopwords:
            try:
                self.stop_words = set(stopwords.words('english'))
            except Exception:
                self.stop_words = self._get_default_stopwords()
        else:
            self.stop_words = self._get_default_stopwords() if remove_stopwords else set()
    
    def _get_default_stopwords(self) -> set:
        """Default English stopwords"""
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
            'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'can', 'just', 'should', 'now', 'i', 'you',
            'your', 'we', 'our', 'my', 'me', 'her', 'him', 'them', 'their'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words
        
        Args:
            text: Input text string
        
        Returns:
            List of tokens (words)
        """
        if not text:
            return []
        
        # Lowercase
        text = text.lower()
        
        # Remove punctuation and special characters, keep alphanumeric
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Remove stopwords
        if self.remove_stopwords_flag:
            tokens = [t for t in tokens if t not in self.stop_words]
        
        # Remove short tokens (less than 2 chars)
        tokens = [t for t in tokens if len(t) >= 2]
        
        # Apply stemming
        if self.stemmer:
            tokens = [self.stemmer.stem(t) for t in tokens]
        
        return tokens
    
    def preprocess_query(self, query: str) -> List[str]:
        """
        Preprocess a search query
        
        Same as tokenize but optimized for queries
        """
        return self.tokenize(query)
    
    def preprocess_document(self, content: str) -> List[str]:
        """
        Preprocess document content
        
        Args:
            content: Document text content
        
        Returns:
            List of preprocessed tokens
        """
        return self.tokenize(content)


class TermFrequency:
    """
    Term Frequency (TF) Calculator
    
    Measures how frequently a term appears in a document.
    Uses logarithmic scaling to reduce the impact of term frequency.
    
    Variants:
    - Raw TF: count of term in document
    - Log TF: 1 + log(count) if count > 0, else 0
    - Augmented TF: 0.5 + 0.5 * (count / max_count)
    - Boolean TF: 1 if term present, else 0
    """
    
    @staticmethod
    def raw_tf(term: str, document_tokens: List[str]) -> int:
        """
        Raw term frequency (simple count)
        
        TF(t, d) = count of t in d
        """
        return document_tokens.count(term)
    
    @staticmethod
    def log_tf(term: str, document_tokens: List[str]) -> float:
        """
        Logarithmically scaled term frequency
        
        TF(t, d) = 1 + log₁₀(count) if count > 0, else 0
        
        Why logarithm?
        - A term appearing 100 times isn't 100x more important than appearing once
        - Logarithm dampens the effect of high frequencies
        - Prevents common terms from dominating
        """
        count = document_tokens.count(term)
        if count == 0:
            return 0.0
        return 1.0 + math.log10(count)
    
    @staticmethod
    def augmented_tf(term: str, document_tokens: List[str]) -> float:
        """
        Augmented term frequency (normalized by max frequency)
        
        TF(t, d) = 0.5 + 0.5 * (count / max_count)
        
        Why augmented?
        - Normalizes for document length
        - Values always between 0.5 and 1.0
        - Useful when comparing documents of different lengths
        """
        if not document_tokens:
            return 0.0
        
        count = document_tokens.count(term)
        max_count = max(Counter(document_tokens).values())
        
        return 0.5 + 0.5 * (count / max_count)
    
    @staticmethod
    def boolean_tf(term: str, document_tokens: List[str]) -> float:
        """
        Boolean term frequency
        
        TF(t, d) = 1 if t in d, else 0
        """
        return 1.0 if term in document_tokens else 0.0
    
    @staticmethod
    def compute_tf_vector(document_tokens: List[str], method: str = 'log') -> Dict[str, float]:
        """
        Compute TF for all terms in a document
        
        Args:
            document_tokens: List of tokens in document
            method: 'raw', 'log', 'augmented', or 'boolean'
        
        Returns:
            Dictionary mapping term -> TF value
        """
        tf_methods = {
            'raw': TermFrequency.raw_tf,
            'log': TermFrequency.log_tf,
            'augmented': TermFrequency.augmented_tf,
            'boolean': TermFrequency.boolean_tf
        }
        
        tf_func = tf_methods.get(method, TermFrequency.log_tf)
        
        unique_terms = set(document_tokens)
        return {term: tf_func(term, document_tokens) for term in unique_terms}


class InverseDocumentFrequency:
    """
    Inverse Document Frequency (IDF) Calculator
    
    Measures how important a term is across the entire corpus.
    Terms that appear in many documents get lower IDF scores.
    
    Formula:
        IDF(t, D) = log(N / df(t))
    
    Where:
        N = total number of documents
        df(t) = number of documents containing term t
    
    Smoothing variants prevent division by zero and log(0).
    """
    
    def __init__(self, corpus_stats: Optional[Dict[str, int]] = None, total_docs: int = 0):
        """
        Initialize IDF calculator
        
        Args:
            corpus_stats: Dict mapping term -> document frequency
            total_docs: Total number of documents in corpus
        """
        self.doc_frequencies: Dict[str, int] = corpus_stats or {}
        self.total_docs = total_docs
    
    def add_document(self, document_tokens: List[str]):
        """
        Add a document to the corpus statistics
        
        Args:
            document_tokens: Tokens from the document
        """
        unique_terms = set(document_tokens)
        for term in unique_terms:
            self.doc_frequencies[term] = self.doc_frequencies.get(term, 0) + 1
        self.total_docs += 1
    
    def idf(self, term: str) -> float:
        """
        Standard IDF calculation
        
        IDF(t) = log₁₀(N / df(t))
        
        Note: Returns 0 if term not in corpus
        """
        if term not in self.doc_frequencies or self.total_docs == 0:
            return 0.0
        
        df = self.doc_frequencies[term]
        return math.log10(self.total_docs / df)
    
    def idf_smooth(self, term: str) -> float:
        """
        Smoothed IDF (adds 1 to prevent log(0))
        
        IDF(t) = log₁₀((N + 1) / (df(t) + 1))
        
        Why smoothing?
        - Prevents division by zero for unseen terms
        - Ensures IDF is never negative
        - More stable for small corpora
        """
        df = self.doc_frequencies.get(term, 0)
        return math.log10((self.total_docs + 1) / (df + 1))
    
    def idf_probabilistic(self, term: str) -> float:
        """
        Probabilistic IDF
        
        IDF(t) = log₁₀((N - df(t)) / df(t))
        
        Why probabilistic?
        - Based on Robertson-Sparck Jones weighting
        - Can be negative for very common terms
        - Used in BM25 ranking
        """
        df = self.doc_frequencies.get(term, 0)
        if df == 0 or df >= self.total_docs:
            return 0.0
        
        return math.log10((self.total_docs - df) / df)
    
    def idf_max(self, term: str) -> float:
        """
        IDF with max normalization
        
        IDF(t) = log₁₀(max_df / (1 + df(t)))
        
        Where max_df is the maximum document frequency in corpus
        """
        if not self.doc_frequencies:
            return 0.0
        
        max_df = max(self.doc_frequencies.values())
        df = self.doc_frequencies.get(term, 0)
        
        return math.log10(max_df / (1 + df))
    
    def get_idf_vector(self, terms: List[str], method: str = 'smooth') -> Dict[str, float]:
        """
        Compute IDF for a list of terms
        
        Args:
            terms: List of terms to compute IDF for
            method: 'standard', 'smooth', 'probabilistic', or 'max'
        
        Returns:
            Dictionary mapping term -> IDF value
        """
        idf_methods = {
            'standard': self.idf,
            'smooth': self.idf_smooth,
            'probabilistic': self.idf_probabilistic,
            'max': self.idf_max
        }
        
        idf_func = idf_methods.get(method, self.idf_smooth)
        
        return {term: idf_func(term) for term in terms}


class TFIDFCalculator:
    """
    TF-IDF Calculator
    
    Combines Term Frequency and Inverse Document Frequency
    to score document relevance for a query.
    
    Usage:
        calculator = TFIDFCalculator()
        
        # Build corpus statistics
        for doc in documents:
            calculator.add_document(doc_id, doc_content)
        
        # Score a query
        results = calculator.score_query("search terms", top_k=10)
    """
    
    def __init__(
        self,
        tf_method: str = 'log',
        idf_method: str = 'smooth',
        use_stemming: bool = True,
        remove_stopwords: bool = True
    ):
        """
        Initialize TF-IDF calculator
        
        Args:
            tf_method: TF calculation method ('raw', 'log', 'augmented', 'boolean')
            idf_method: IDF calculation method ('standard', 'smooth', 'probabilistic')
            use_stemming: Whether to apply stemming
            remove_stopwords: Whether to remove stopwords
        """
        self.tf_method = tf_method
        self.idf_method = idf_method
        
        self.preprocessor = TextPreprocessor(
            use_stemming=use_stemming,
            remove_stopwords=remove_stopwords
        )
        
        self.idf_calculator = InverseDocumentFrequency()
        
        # Store document tokens for TF calculation
        self.documents: Dict[str, List[str]] = {}
    
    def add_document(self, doc_id: str, content: str):
        """
        Add a document to the corpus
        
        Args:
            doc_id: Unique document identifier
            content: Document text content
        """
        tokens = self.preprocessor.preprocess_document(content)
        self.documents[doc_id] = tokens
        self.idf_calculator.add_document(tokens)
    
    def compute_tfidf(self, doc_id: str, term: str) -> float:
        """
        Compute TF-IDF score for a term in a document
        
        TF-IDF(t, d) = TF(t, d) × IDF(t)
        
        Args:
            doc_id: Document identifier
            term: Term to score
        
        Returns:
            TF-IDF score
        """
        if doc_id not in self.documents:
            return 0.0
        
        doc_tokens = self.documents[doc_id]
        
        # Compute TF
        tf_methods = {
            'raw': TermFrequency.raw_tf,
            'log': TermFrequency.log_tf,
            'augmented': TermFrequency.augmented_tf,
            'boolean': TermFrequency.boolean_tf
        }
        tf_func = tf_methods.get(self.tf_method, TermFrequency.log_tf)
        tf = tf_func(term, doc_tokens)
        
        # Compute IDF
        idf_methods = {
            'standard': self.idf_calculator.idf,
            'smooth': self.idf_calculator.idf_smooth,
            'probabilistic': self.idf_calculator.idf_probabilistic,
            'max': self.idf_calculator.idf_max
        }
        idf_func = idf_methods.get(self.idf_method, self.idf_calculator.idf_smooth)
        idf = idf_func(term)
        
        return tf * idf
    
    def score_document(self, doc_id: str, query_terms: List[str]) -> TFIDFScore:
        """
        Score a document against query terms
        
        Args:
            doc_id: Document identifier
            query_terms: Preprocessed query terms
        
        Returns:
            TFIDFScore with document score and term contributions
        """
        term_scores = {}
        total_score = 0.0
        
        for term in query_terms:
            tfidf = self.compute_tfidf(doc_id, term)
            term_scores[term] = tfidf
            total_score += tfidf
        
        return TFIDFScore(
            doc_id=doc_id,
            score=total_score,
            term_scores=term_scores
        )
    
    def score_query(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[TFIDFScore]:
        """
        Score all documents against a query
        
        Args:
            query: Search query string
            top_k: Return only top K results (None for all)
        
        Returns:
            List of TFIDFScore sorted by score descending
        """
        # Preprocess query
        query_terms = self.preprocessor.preprocess_query(query)
        
        if not query_terms:
            return []
        
        # Score all documents
        scores = []
        for doc_id in self.documents:
            score = self.score_document(doc_id, query_terms)
            if score.score > 0:
                scores.append(score)
        
        # Sort by score descending
        scores.sort(key=lambda x: x.score, reverse=True)
        
        # Return top K if specified
        if top_k:
            return scores[:top_k]
        
        return scores
    
    def get_document_vector(self, doc_id: str) -> Dict[str, float]:
        """
        Get the TF-IDF vector for a document
        
        Args:
            doc_id: Document identifier
        
        Returns:
            Dictionary mapping term -> TF-IDF value
        """
        if doc_id not in self.documents:
            return {}
        
        doc_tokens = self.documents[doc_id]
        unique_terms = set(doc_tokens)
        
        return {term: self.compute_tfidf(doc_id, term) for term in unique_terms}
    
    @property
    def corpus_size(self) -> int:
        """Number of documents in corpus"""
        return len(self.documents)
    
    @property
    def vocabulary_size(self) -> int:
        """Number of unique terms in corpus"""
        return len(self.idf_calculator.doc_frequencies)


class QueryProcessor:
    """
    Query processor for search operations
    
    Features:
    - Query tokenization and normalization
    - Query expansion (synonyms, stemming)
    - Boolean query parsing (AND, OR, NOT)
    - Phrase query handling
    """
    
    def __init__(self, preprocessor: Optional[TextPreprocessor] = None):
        self.preprocessor = preprocessor or TextPreprocessor()
    
    def parse_query(self, query: str) -> Dict[str, any]:
        """
        Parse a query string into structured format
        
        Supports:
        - Simple queries: "hello world"
        - Quoted phrases: "hello world"
        - Boolean operators: hello AND world, hello OR world
        
        Returns:
            Dictionary with query structure
        """
        query = query.strip()
        
        # Check for phrase queries (quoted)
        phrases = re.findall(r'"([^"]+)"', query)
        
        # Remove phrases from query
        remaining = re.sub(r'"[^"]+"', '', query)
        
        # Check for boolean operators
        has_and = ' AND ' in remaining.upper()
        has_or = ' OR ' in remaining.upper()
        has_not = ' NOT ' in remaining.upper()
        
        # Tokenize remaining terms
        terms = self.preprocessor.tokenize(remaining)
        
        return {
            'raw': query,
            'terms': terms,
            'phrases': phrases,
            'operators': {
                'and': has_and,
                'or': has_or,
                'not': has_not
            }
        }
    
    def expand_query(self, terms: List[str]) -> List[str]:
        """
        Expand query terms with variants
        
        Currently just returns the terms,
        but can be extended with synonyms, etc.
        """
        # Could add synonym expansion, spelling correction, etc.
        return terms
    
    def preprocess(self, query: str) -> List[str]:
        """
        Full query preprocessing pipeline
        
        Args:
            query: Raw query string
        
        Returns:
            List of preprocessed query terms
        """
        parsed = self.parse_query(query)
        terms = parsed['terms']
        
        # Expand query
        expanded = self.expand_query(terms)
        
        return expanded


# Utility functions for integration with search service
def compute_tfidf_scores(
    query: str,
    documents: Dict[str, str],
    tf_method: str = 'log',
    idf_method: str = 'smooth'
) -> List[Tuple[str, float]]:
    """
    Convenience function to compute TF-IDF scores for a query
    
    Args:
        query: Search query
        documents: Dict mapping doc_id -> content
        tf_method: TF calculation method
        idf_method: IDF calculation method
    
    Returns:
        List of (doc_id, score) tuples sorted by score
    """
    calculator = TFIDFCalculator(
        tf_method=tf_method,
        idf_method=idf_method
    )
    
    for doc_id, content in documents.items():
        calculator.add_document(doc_id, content)
    
    results = calculator.score_query(query)
    
    return [(r.doc_id, r.score) for r in results]


if __name__ == "__main__":
    # Demo/test the TF-IDF implementation
    print("=" * 60)
    print("TF-IDF Algorithm Demo")
    print("=" * 60)
    
    # Sample documents
    documents = {
        "doc1": "The quick brown fox jumps over the lazy dog",
        "doc2": "A quick brown dog outpaces a fox",
        "doc3": "The dog is lazy but the fox is quick",
        "doc4": "Python is a programming language",
        "doc5": "Machine learning uses Python for data science"
    }
    
    # Create calculator
    calculator = TFIDFCalculator(tf_method='log', idf_method='smooth')
    
    # Add documents
    print("\n📄 Adding documents to corpus...")
    for doc_id, content in documents.items():
        calculator.add_document(doc_id, content)
        print(f"   {doc_id}: {content[:50]}...")
    
    print(f"\n📊 Corpus Statistics:")
    print(f"   Documents: {calculator.corpus_size}")
    print(f"   Vocabulary: {calculator.vocabulary_size}")
    
    # Test queries
    queries = [
        "quick fox",
        "lazy dog",
        "python programming",
        "data science machine learning"
    ]
    
    print("\n🔍 Query Results:")
    print("-" * 60)
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = calculator.score_query(query, top_k=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.doc_id} (score: {result.score:.4f})")
                for term, score in result.term_scores.items():
                    if score > 0:
                        print(f"      - {term}: {score:.4f}")
        else:
            print("   No matching documents")
    
    print("\n" + "=" * 60)
    print("✅ TF-IDF Demo Complete")
