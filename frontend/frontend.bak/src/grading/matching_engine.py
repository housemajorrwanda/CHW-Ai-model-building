"""
Matching Engine - Compares student steps to gold steps
Uses multiple strategies to determine equivalence
"""
import re
from typing import Tuple, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    Engine for matching student steps to gold solution steps.
    Uses multiple strategies: exact, symbolic, derivation, similarity.
    """
    
    def __init__(self, 
                 use_symbolic: bool = True,
                 similarity_threshold: float = 0.8):
        """
        Initialize matching engine.
        
        Args:
            use_symbolic: Whether to use SymPy for symbolic matching
            similarity_threshold: Minimum similarity for text matching (0-1)
        """
        self.use_symbolic = use_symbolic
        self.similarity_threshold = similarity_threshold
        
        # Try to import SymPy for symbolic math
        if use_symbolic:
            try:
                from sympy import sympify, simplify, Eq
                from sympy.parsing.sympy_parser import parse_expr
                self.sympify = sympify
                self.simplify = simplify
                self.Eq = Eq
                self.parse_expr = parse_expr
                self.sympy_available = True
            except ImportError:
                logger.warning("SymPy not available. Symbolic matching disabled.")
                self.sympy_available = False
        else:
            self.sympy_available = False
    
    def match(self, student_text: str, gold_text: str) -> Tuple[float, str]:
        """
        Match student text against gold text using multiple strategies.
        
        Args:
            student_text: Student's answer
            gold_text: Correct answer
            
        Returns:
            (match_score, strategy_used) where score is 0.0 to 1.0
        """
        # Strategy 1: Exact match
        score, strategy = self._exact_match(student_text, gold_text)
        if score == 1.0:
            return score, strategy
        
        # Strategy 2: Normalized match
        score, strategy = self._normalized_match(student_text, gold_text)
        if score == 1.0:
            return score, strategy
        
        # Strategy 3: Symbolic equivalence
        if self.sympy_available:
            score, strategy = self._symbolic_match(student_text, gold_text)
            if score > 0.9:
                return score, strategy
        
        # Strategy 4: Valid derivation
        score, strategy = self._derivation_match(student_text, gold_text)
        if score > 0.7:
            return score, strategy
        
        # Strategy 5: Text similarity
        score, strategy = self._similarity_match(student_text, gold_text)
        
        return score, strategy
    
    def _exact_match(self, text1: str, text2: str) -> Tuple[float, str]:
        """Check for exact text match"""
        if text1.strip() == text2.strip():
            return 1.0, "exact_match"
        return 0.0, ""
    
    def _normalized_match(self, text1: str, text2: str) -> Tuple[float, str]:
        """Match after normalizing whitespace and case"""
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        if norm1 == norm2:
            return 1.0, "normalized_match"
        return 0.0, ""
    
    def _normalize_text(self, text: str) -> str:
        """Normalize mathematical text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove all whitespace
        text = re.sub(r'\s+', '', text)
        
        # Standardize operators
        text = text.replace('×', '*').replace('÷', '/')
        text = text.replace('**', '^')
        
        # Standardize equals
        text = text.replace('==', '=')
        
        return text
    
    def _symbolic_match(self, text1: str, text2: str) -> Tuple[float, str]:
        """Check for mathematical equivalence using SymPy"""
        if not self.sympy_available:
            return 0.0, ""
        
        try:
            # Parse both expressions
            expr1 = self._parse_math_expression(text1)
            expr2 = self._parse_math_expression(text2)
            
            if expr1 is None or expr2 is None:
                return 0.0, ""
            
            # Check if they're equations
            if '=' in text1 and '=' in text2:
                # Handle equations
                return self._compare_equations(text1, text2)
            else:
                # Compare as expressions
                diff = self.simplify(expr1 - expr2)
                if diff == 0:
                    return 1.0, "symbolic_equivalent"
                
                # Check if one is a multiple of the other
                try:
                    ratio = self.simplify(expr1 / expr2)
                    if ratio.is_number:
                        return 0.9, "symbolic_equivalent_scaled"
                except:
                    pass
            
            return 0.0, ""
            
        except Exception as e:
            logger.debug(f"Symbolic matching failed: {e}")
            return 0.0, ""
    
    def _parse_math_expression(self, text: str) -> Optional[any]:
        """Parse mathematical expression with SymPy"""
        try:
            # Clean the text
            text = text.replace('^', '**')
            text = text.replace('×', '*')
            text = text.replace('÷', '/')
            
            # Remove equation part if present
            if '=' in text:
                text = text.split('=')[0].strip()
            
            return self.sympify(text)
        except:
            return None
    
    def _compare_equations(self, eq1: str, eq2: str) -> Tuple[float, str]:
        """Compare two equations for equivalence"""
        try:
            # Split equations
            parts1 = eq1.split('=')
            parts2 = eq2.split('=')
            
            if len(parts1) != 2 or len(parts2) != 2:
                return 0.0, ""
            
            # Parse both sides
            left1 = self.sympify(parts1[0].replace('^', '**'))
            right1 = self.sympify(parts1[1].replace('^', '**'))
            left2 = self.sympify(parts2[0].replace('^', '**'))
            right2 = self.sympify(parts2[1].replace('^', '**'))
            
            # Check if equivalent: (left1 - right1) == (left2 - right2)
            diff1 = self.simplify(left1 - right1)
            diff2 = self.simplify(left2 - right2)
            
            if self.simplify(diff1 - diff2) == 0:
                return 1.0, "symbolic_equation_equivalent"
            
            # Check reversed equation
            if self.simplify(left1 - right2) == 0 and self.simplify(right1 - left2) == 0:
                return 1.0, "symbolic_equation_reversed"
            
            return 0.0, ""
            
        except Exception as e:
            logger.debug(f"Equation comparison failed: {e}")
            return 0.0, ""
    
    def _derivation_match(self, text1: str, text2: str) -> Tuple[float, str]:
        """Check if one expression is a valid derivation of the other"""
        # Normalize both
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        # Check if one is a substring/superstring (factoring/expanding)
        if norm1 in norm2 or norm2 in norm1:
            return 0.7, "valid_derivation_substring"
        
        # Check for shared significant terms
        terms1 = set(re.findall(r'[a-z]\^?\d?', norm1))
        terms2 = set(re.findall(r'[a-z]\^?\d?', norm2))
        
        if terms1 and terms2:
            overlap = len(terms1 & terms2) / max(len(terms1), len(terms2))
            if overlap > 0.7:
                return 0.6, "valid_derivation_shared_terms"
        
        return 0.0, ""
    
    def _similarity_match(self, text1: str, text2: str) -> Tuple[float, str]:
        """Calculate text similarity for explanations"""
        # Use SequenceMatcher for fuzzy string matching
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        if similarity >= self.similarity_threshold:
            return similarity, "text_similarity"
        
        return 0.0, ""
    
    def find_best_match(self, student_text: str, gold_steps: list) -> Tuple[Optional[int], float, str]:
        """
        Find the best matching gold step for student text.
        
        Args:
            student_text: Student's answer
            gold_steps: List of Step objects
            
        Returns:
            (best_index, best_score, strategy) or (None, 0.0, "") if no match
        """
        best_index = None
        best_score = 0.0
        best_strategy = ""
        
        for i, gold_step in enumerate(gold_steps):
            score, strategy = self.match(student_text, gold_step.text)
            
            if score > best_score:
                best_score = score
                best_index = i
                best_strategy = strategy
        
        # Only return matches above a minimum threshold
        if best_score >= 0.5:
            return best_index, best_score, best_strategy
        
        return None, 0.0, ""

