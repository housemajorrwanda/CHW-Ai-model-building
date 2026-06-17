"""
ML-Enhanced Matching Engine
Uses machine learning models trained on Rwanda exam dataset to improve answer matching
"""
import re
import pickle
import os
from typing import Tuple, Optional, Dict, List
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")


class MLMatcher:
    """
    Machine learning-based answer matcher trained on Rwanda exam dataset.
    Uses semantic embeddings and TF-IDF for improved answer matching.
    """
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 use_embeddings: bool = True,
                 similarity_threshold: float = 0.6):
        """
        Initialize ML matcher.
        
        Args:
            model_path: Path to saved model (if exists)
            use_embeddings: Whether to use sentence transformers
            similarity_threshold: Minimum similarity score (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE
        self.embedding_model = None
        self.tfidf_vectorizer = None
        self.question_metadata = {}
        
        # Load or initialize models
        if self.use_embeddings:
            try:
                # Use a lightweight model that works well for similarity
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence transformer model")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
                self.use_embeddings = False
        
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english',
                lowercase=True
            )
    
    def train_on_dataset(self, dataset_path: str):
        """
        Train the matcher on the Rwanda exam dataset.
        
        Args:
            dataset_path: Path to grading_dataset_enhanced.csv
        """
        import pandas as pd
        
        try:
            df = pd.read_csv(dataset_path)
            logger.info(f"Loaded dataset with {len(df)} rows")
            
            # Extract question-answer pairs
            question_answer_pairs = []
            for _, row in df.iterrows():
                question = str(row.get('question', '')).strip()
                answer = str(row.get('answer', '')).strip()
                
                if question and answer and len(question) > 10 and len(answer) > 5:
                    question_answer_pairs.append({
                        'question': question,
                        'answer': answer,
                        'marks': row.get('marks', 0),
                        'difficulty': row.get('estimated_difficulty', 'Medium'),
                        'question_type': row.get('question_type', ''),
                        'keywords': str(row.get('keywords', '')),
                        'topic': str(row.get('topic', '')),
                        'subject': str(row.get('subject', ''))
                    })
            
            logger.info(f"Extracted {len(question_answer_pairs)} valid question-answer pairs")
            
            # Train TF-IDF on all questions and answers
            if self.tfidf_vectorizer:
                all_texts = [pair['question'] + ' ' + pair['answer'] for pair in question_answer_pairs]
                self.tfidf_vectorizer.fit(all_texts)
                logger.info("Trained TF-IDF vectorizer")
            
            # Store metadata for context-aware matching
            for pair in question_answer_pairs:
                key = self._normalize_text(pair['question'])
                self.question_metadata[key] = {
                    'difficulty': pair['difficulty'],
                    'question_type': pair['question_type'],
                    'keywords': pair['keywords'],
                    'topic': pair['topic'],
                    'subject': pair['subject']
                }
            
            logger.info(f"Stored metadata for {len(self.question_metadata)} questions")
            
        except Exception as e:
            logger.error(f"Error training on dataset: {e}")
            raise
    
    def match(self, 
              student_text: str, 
              gold_text: str,
              question_context: Optional[Dict] = None) -> Tuple[float, str]:
        """
        Match student answer against gold answer using ML models.
        
        Args:
            student_text: Student's answer
            gold_text: Correct answer
            question_context: Optional context about the question (difficulty, type, etc.)
            
        Returns:
            (match_score, strategy) where score is 0.0 to 1.0
        """
        if not student_text or not gold_text:
            return 0.0, "empty_input"
        
        # Strategy 1: Semantic similarity using embeddings
        if self.use_embeddings and self.embedding_model:
            embedding_score = self._embedding_similarity(student_text, gold_text)
            if embedding_score > 0.85:
                return embedding_score, "ml_embedding_high"
            if embedding_score > self.similarity_threshold:
                return embedding_score, "ml_embedding"
        
        # Strategy 2: TF-IDF cosine similarity
        if self.tfidf_vectorizer:
            tfidf_score = self._tfidf_similarity(student_text, gold_text)
            if tfidf_score > 0.8:
                return tfidf_score, "ml_tfidf_high"
            if tfidf_score > self.similarity_threshold:
                return tfidf_score, "ml_tfidf"
        
        # Strategy 3: Keyword-based matching (if context available)
        if question_context:
            keyword_score = self._keyword_match(student_text, gold_text, question_context)
            if keyword_score > self.similarity_threshold:
                return keyword_score, "ml_keyword_context"
        
        # Strategy 4: Normalized text similarity (fallback)
        normalized_score = self._normalized_similarity(student_text, gold_text)
        if normalized_score > self.similarity_threshold:
            return normalized_score, "ml_normalized"
        
        return 0.0, "no_match"
    
    def _embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using sentence embeddings"""
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.debug(f"Embedding similarity failed: {e}")
            return 0.0
    
    def _tfidf_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using TF-IDF vectors"""
        try:
            vectors = self.tfidf_vectorizer.transform([text1, text2])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            logger.debug(f"TF-IDF similarity failed: {e}")
            return 0.0
    
    def _keyword_list_from_context(self, context: Dict) -> List[str]:
        """Normalize keywords from question context (comma string or list)."""
        raw = context.get("keywords", "")
        if not raw:
            return []
        if isinstance(raw, (list, tuple, set)):
            return [str(k).strip().lower() for k in raw if str(k).strip()]
        if isinstance(raw, str):
            return [k.strip().lower() for k in raw.split(",") if k.strip()]
        return [str(raw).strip().lower()] if str(raw).strip() else []

    def _keyword_match(self, student_text: str, gold_text: str, context: Dict) -> float:
        """Match based on keywords from question context"""
        keyword_list = self._keyword_list_from_context(context)
        if not keyword_list:
            return 0.0
        
        student_lower = student_text.lower()
        gold_lower = gold_text.lower()
        
        # Count keyword matches
        student_keywords = sum(1 for kw in keyword_list if kw in student_lower)
        gold_keywords = sum(1 for kw in keyword_list if kw in gold_lower)
        
        if gold_keywords == 0:
            return 0.0
        
        # Score based on keyword overlap
        keyword_score = student_keywords / max(gold_keywords, 1)
        
        # Combine with text similarity
        text_sim = self._normalized_similarity(student_text, gold_text)
        
        return (keyword_score * 0.6 + text_sim * 0.4)
    
    def _normalized_similarity(self, text1: str, text2: str) -> float:
        """Calculate normalized text similarity"""
        from difflib import SequenceMatcher
        
        # Normalize texts
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove punctuation (keep alphanumeric and spaces)
        text = re.sub(r'[^\w\s]', '', text)
        
        return text.strip()
    
    def find_best_match(self, 
                       student_text: str, 
                       gold_steps: List,
                       question_context: Optional[Dict] = None) -> Tuple[Optional[int], float, str]:
        """
        Find the best matching gold step for student text.
        
        Args:
            student_text: Student's answer
            gold_steps: List of Step objects or strings
            question_context: Optional context about the question
            
        Returns:
            (best_index, best_score, strategy) or (None, 0.0, "") if no match
        """
        best_index = None
        best_score = 0.0
        best_strategy = ""
        
        for i, gold_step in enumerate(gold_steps):
            # Extract text from Step object or use string directly
            if hasattr(gold_step, 'text'):
                gold_text = gold_step.text
            else:
                gold_text = str(gold_step)
            
            score, strategy = self.match(student_text, gold_text, question_context)
            
            if score > best_score:
                best_score = score
                best_index = i
                best_strategy = strategy
        
        # Only return matches above threshold
        if best_score >= self.similarity_threshold:
            return best_index, best_score, best_strategy
        
        return None, 0.0, ""
    
    def save_model(self, model_path: str):
        """Save the trained model to disk"""
        try:
            os.makedirs(os.path.dirname(model_path) if os.path.dirname(model_path) else '.', exist_ok=True)
            
            model_data = {
                'tfidf_vectorizer': self.tfidf_vectorizer,
                'question_metadata': self.question_metadata,
                'similarity_threshold': self.similarity_threshold
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Saved model to {model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self, model_path: str):
        """Load a trained model from disk"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.tfidf_vectorizer = model_data.get('tfidf_vectorizer')
            self.question_metadata = model_data.get('question_metadata', {})
            self.similarity_threshold = model_data.get('similarity_threshold', 0.6)
            
            logger.info(f"Loaded model from {model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")

