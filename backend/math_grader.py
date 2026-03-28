"""
Mathematical Problem Step-by-Step Grading Model

This module provides a grading system that evaluates student solutions
step-by-step against a gold standard solution.
"""

from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from sympy import sympify, simplify, Symbol, symbols, Eq, parse_expr
from sympy.parsing.sympy_parser import parse_expr as parse_expr_safe

try:
    from grading.science_synonyms import synonym_match_score as _syn_score
    _SCIENCE_SYNONYMS_AVAILABLE = True
except ImportError:
    _SCIENCE_SYNONYMS_AVAILABLE = False


class StepStatus(Enum):
    """Status of a step evaluation"""
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially correct"
    INCORRECT = "Incorrect"


class Step:
    """Represents a single step in a solution"""
    
    def __init__(self, content: str, points: float = 1.0, required: bool = True):
        """
        Args:
            content: The mathematical expression or explanation
            points: Points awarded for this step
            required: Whether this step is required for later steps to be valid
        """
        self.content = content.strip()
        self.points = points
        self.required = required
    
    def __repr__(self):
        return f"Step('{self.content}', points={self.points}, required={self.required})"


class StepEvaluation:
    """Result of evaluating a student step"""
    
    def __init__(self, status: StepStatus, points_earned: float, 
                 feedback: str = "", matched_gold_step: Optional[int] = None):
        self.status = status
        self.points_earned = points_earned
        self.feedback = feedback
        self.matched_gold_step = matched_gold_step  # Index of matched gold step
    
    def __repr__(self):
        return f"StepEvaluation(status={self.status.value}, points={self.points_earned}, feedback='{self.feedback}')"


class MathGrader:
    """
    Grades mathematical problems step-by-step.
    
    Compares student solutions against gold standard solutions,
    evaluating each step for correctness, partial correctness, or incorrectness.
    """
    
    def __init__(self, gold_steps: List[Step], tolerance: float = 1e-6):
        """
        Args:
            gold_steps: List of gold standard steps with their point values
            tolerance: Numerical tolerance for floating point comparisons
        """
        self.gold_steps = self._expand_arrow_gold_steps(gold_steps)
        self.tolerance = tolerance
        self.total_points = sum(step.points for step in self.gold_steps)

    def _expand_arrow_gold_steps(self, steps: List[Step]) -> List[Step]:
        """
        One rubric row like 'a \\Rightarrow b' becomes two steps with split points so
        each clause is matched once and the total weight stays the same.
        """
        out: List[Step] = []
        for s in steps:
            content = s.content.strip()
            parts = re.split(r"\s*(?:\\Rightarrow|⇒|=>)\s*", content)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) <= 1:
                out.append(s)
                continue
            sub_pts = s.points / len(parts)
            for p in parts:
                frag = p.strip().strip("$").strip()
                if frag:
                    out.append(Step(frag, sub_pts, s.required))
        return out
    
    def grade(self, student_steps: List[str]) -> Dict:
        """
        Grade a student solution step-by-step.
        
        Args:
            student_steps: List of student step strings
        
        Returns:
            Dictionary with:
                - evaluations: List of StepEvaluation objects
                - total_score: Total points earned
                - max_score: Maximum possible points
                - percentage: Score as percentage
        """
        evaluations = []
        used_gold_indices = set()
        
        for i, student_step in enumerate(student_steps):
            evaluation = self._evaluate_step(
                student_step, 
                i, 
                used_gold_indices,
                evaluations
            )
            evaluations.append(evaluation)
        
        total_score = sum(eval_obj.points_earned for eval_obj in evaluations)
        
        return {
            "evaluations": evaluations,
            "total_score": total_score,
            "max_score": self.total_points,
            "percentage": (total_score / self.total_points * 100) if self.total_points > 0 else 0
        }
    
    def _evaluate_step(self, student_step: str, student_index: int,
                      used_gold_indices: set, previous_evaluations: List[StepEvaluation]) -> StepEvaluation:
        """
        Evaluate a single student step against gold steps.
        
        Args:
            student_step: The student's step content
            student_index: Index of this step in student solution
            used_gold_indices: Gold step indices already matched
            previous_evaluations: Previous step evaluations
        
        Returns:
            StepEvaluation object
        """
        best_match = None
        best_score = 0.0
        best_gold_index = None
        
        # Check if earlier required steps were missed
        missing_required = self._check_missing_required_steps(
            student_index, previous_evaluations
        )
        
        # Try to match against each gold step
        for gold_idx, gold_step in enumerate(self.gold_steps):
            if gold_idx in used_gold_indices:
                continue
            
            match_score, match_type = self._compare_steps(student_step, gold_step.content)
            
            if match_score > best_score:
                best_score = match_score
                best_match = match_type
                best_gold_index = gold_idx
        
        # Determine status and points
        if best_gold_index is None:
            # No match found at all
            status = StepStatus.INCORRECT
            points = 0.0
            feedback = "Incorrect or not matching any expected step"
        elif best_score >= 1.0:  # Exact or equivalent match
            status = StepStatus.CORRECT
            points = self.gold_steps[best_gold_index].points
            feedback = f"Correct: matches step {best_gold_index + 1}"
            used_gold_indices.add(best_gold_index)
        elif best_score >= 0.5:  # Partial match
            status = StepStatus.PARTIALLY_CORRECT
            points = self.gold_steps[best_gold_index].points * best_score
            feedback = f"Partially correct: {best_match}"
            used_gold_indices.add(best_gold_index)
        else:
            status = StepStatus.INCORRECT
            points = 0.0
            feedback = f"Incorrect: low similarity ({best_score:.2f})"
        
        # Penalize if required earlier steps were missed (softer than 0.5 — avoids
        # crushing correct algebra when ordering or naming differs slightly).
        if missing_required and status != StepStatus.INCORRECT:
            points *= 0.72
            feedback += " (reduced due to missing earlier required steps)"
        
        return StepEvaluation(status, points, feedback, best_gold_index)
    
    def _check_missing_required_steps(self, current_index: int, 
                                     previous_evaluations: List[StepEvaluation]) -> bool:
        """
        Check if required steps before current step were missed.
        
        Returns:
            True if required steps were missed
        """
        if current_index == 0:
            return False
        
        # Check if any required gold steps before current position were not matched
        for i in range(min(current_index, len(self.gold_steps))):
            if self.gold_steps[i].required:
                if self._implicit_var_definition_waived(i, previous_evaluations):
                    continue
                # Check if this step was matched in previous evaluations
                matched = any(
                    eval_obj.matched_gold_step == i 
                    for eval_obj in previous_evaluations
                )
                if not matched:
                    return True
        return False

    def _implicit_var_definition_waived(
        self, gold_idx: int, previous_evaluations: List[StepEvaluation]
    ) -> bool:
        """
        Rubric lines like 'n, n+1' are satisfied when a later gold step (equation)
        was already matched — students rarely spell out the tuple explicitly.
        """
        if not self._is_implicit_var_definition_step(self.gold_steps[gold_idx].content):
            return False
        return any(
            ev.matched_gold_step is not None and ev.matched_gold_step > gold_idx
            for ev in previous_evaluations
        )

    def _is_implicit_var_definition_step(self, content: str) -> bool:
        t = content.strip()
        t = re.sub(r"^\$\$?(.*?)\$\$?$", r"\1", t)
        t = re.sub(r"\\,", "", t)
        t = re.sub(r"\s+", "", t.lower())
        return bool(re.match(r"^([a-z]),\1\+1$", t))

    def _gold_step_variants(self, gold_inner: str) -> List[str]:
        """Split compound gold (arrow chains) so each clause can match independently."""
        t = gold_inner.strip()
        if not t:
            return [t]
        seen = set()
        out: List[str] = []

        def add(s: str) -> None:
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)

        add(t)
        parts = re.split(r"\s*(?:\\Rightarrow|⇒|=>)\s*", t)
        if len(parts) > 1:
            for p in parts:
                add(p)
        return out
    
    def _normalize_math_text(self, text: str) -> str:
        """Normalize mathematical text for comparison"""
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Normalize common math symbols
        # Replace different minus/hyphen variants with standard -
        text = text.replace('−', '-').replace('–', '-').replace('—', '-')
        # Replace multiplication symbols
        text = text.replace('·', '*').replace('×', '*').replace('×', '*')
        # Replace division symbols
        text = text.replace('÷', '/')
        # Normalize superscripts (basic handling)
        text = text.replace('²', '^2').replace('³', '^3')
        # Normalize spaces around operators
        text = re.sub(r'\s*([+\-*/=])\s*', r'\1', text)
        
        return text.strip()

    def _student_match_variants(self, student_step: str) -> List[str]:
        """
        Build alternate strings for matching OCR / show-your-work answers.
        Gold steps are often bare equations (2x = 18); students add labels like
        'Add 8 to both sides:' or 'Final answer: x = 9'.
        """
        raw = student_step.strip()
        if not raw:
            return [raw]
        seen = set()
        out: List[str] = []

        def add(s: str) -> None:
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)

        add(raw)
        # Drop common instructional prefixes (whole string)
        stripped = re.sub(
            r"(?i)^(?:final\s+answer\s*:\s*|therefore\s*,?\s*|thus\s*,?\s*|so\s*,?\s*|hence\s*,?\s*)",
            "",
            raw,
        ).strip()
        add(stripped)
        # Text after the last colon often holds the equation (label : equation)
        if ":" in raw and "=" in raw:
            tail = raw[raw.rfind(":") + 1 :].strip()
            add(tail)
        # Pull out equation-like spans (at least one =, alphanumeric math)
        for m in re.finditer(
            r"[0-9a-zA-Z^+\-*/().,\s]{1,64}\s*=\s*[0-9a-zA-Z^+\-*/().,\s]+",
            raw,
        ):
            frag = m.group(0).strip()
            if len(frag) >= 3:
                add(frag)
        # Single-line cleanup: keep longest '=' segment if multiple
        if raw.count("=") >= 1:
            parts = re.split(r"\s+(?=[0-9a-zA-Z(]+\s*=)", raw)
            for p in parts:
                if "=" in p:
                    add(p.strip())
        return out if out else [raw]

    def _compare_steps(self, student_step: str, gold_step: str) -> Tuple[float, str]:
        """
        Compare a student step with a gold step, trying several interpretations
        of the student text (OCR labels, final-answer lines, equation-only).
        """
        best: Tuple[float, str] = (0.0, "no match")
        for variant in self._student_match_variants(student_step):
            score, desc = self._compare_steps_single(variant, gold_step)
            if score > best[0]:
                best = (score, desc)
        return best

    def _compare_steps_single(self, student_step: str, gold_step: str) -> Tuple[float, str]:
        """
        Compare one candidate student string to a gold step.
        Tries each clause of compound gold (e.g. a \\Rightarrow b) separately.
        """
        student_step = student_step.strip()
        gold_step = gold_step.strip()

        student_clean = re.sub(r"^\$\$?(.*?)\$\$?$", r"\1", student_step)
        gold_clean = re.sub(r"^\$\$?(.*?)\$\$?$", r"\1", gold_step)

        student_normalized = self._normalize_math_text(student_clean)
        best: Tuple[float, str] = (0.0, "no match")

        for gv in self._gold_step_variants(gold_clean):
            gvn = self._normalize_math_text(gv)
            pair = self._compare_steps_single_against_gold_fragment(
                student_step, student_clean, student_normalized, gold_step, gv, gvn
            )
            if pair[0] > best[0]:
                best = pair
        return best

    def _compare_steps_single_against_gold_fragment(
        self,
        student_step: str,
        student_clean: str,
        student_normalized: str,
        gold_step_full: str,
        gold_frag: str,
        gold_normalized: str,
    ) -> Tuple[float, str]:
        """Compare student to one gold fragment (possibly one side of \\Rightarrow)."""
        if student_step == gold_step_full or student_clean == gold_frag:
            return (1.0, "exact match")

        if student_normalized == gold_normalized:
            return (1.0, "normalized exact match")

        if _SCIENCE_SYNONYMS_AVAILABLE:
            syn_score = _syn_score(student_clean, gold_frag)
            if syn_score >= 0.85:
                return (syn_score, "science synonym match")

        math_score = self._check_mathematical_equivalence(student_normalized, gold_normalized)
        if math_score > 0:
            return (math_score, "mathematically equivalent")

        if math_score == 0:
            math_score = self._check_mathematical_equivalence(student_step, gold_frag)
            if math_score > 0:
                return (math_score, "mathematically equivalent (original)")

        derivation_score = self._check_derivation(student_normalized, gold_normalized)
        if derivation_score > 0:
            return (derivation_score, "valid intermediate derivation")

        student_core = re.sub(r"[=+\-*/()\[\]{}]", "", student_normalized.lower())
        gold_core = re.sub(r"[=+\-*/()\[\]{}]", "", gold_normalized.lower())

        if student_core and gold_core:
            if gold_core in student_core or student_core in gold_core:
                overlap = min(len(student_core), len(gold_core)) / max(len(student_core), len(gold_core))
                if overlap > 0.6:
                    return (overlap * 0.7, "contains matching content")

        text_similarity = self._text_similarity(student_normalized, gold_normalized)
        if text_similarity > 0.5:
            return (text_similarity * 0.6, "similar explanation")

        return (0.0, "no match")

    def _equations_equal_modulo_symbol_rename(self, seq: Eq, geq: Eq) -> bool:
        """True if equations match after renaming a single student variable to gold's (e.g. x vs n)."""
        try:
            s_syms = seq.free_symbols
            g_syms = geq.free_symbols
            if not s_syms or not g_syms:
                return False
            if s_syms == g_syms:
                if simplify(seq.lhs - geq.lhs) == 0 and simplify(seq.rhs - geq.rhs) == 0:
                    return True
                if simplify(seq.lhs - geq.rhs) == 0 and simplify(seq.rhs - geq.lhs) == 0:
                    return True
                return False
            if len(s_syms) == 1 and len(g_syms) == 1:
                ss, gs = next(iter(s_syms)), next(iter(g_syms))
                seq2 = seq.subs(ss, gs)
                if simplify(seq2.lhs - geq.lhs) == 0 and simplify(seq2.rhs - geq.rhs) == 0:
                    return True
                if simplify(seq2.lhs - geq.rhs) == 0 and simplify(seq2.rhs - geq.lhs) == 0:
                    return True
            return False
        except Exception:
            return False
    
    def _check_mathematical_equivalence(self, student: str, gold: str) -> float:
        """
        Check if two mathematical expressions are equivalent.
        
        Returns:
            Score between 0 and 1
        """
        try:
            # Try to parse as mathematical expressions
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            
            # Handle equations separately
            if isinstance(student_expr, Eq) and isinstance(gold_expr, Eq):
                if self._equations_equal_modulo_symbol_rename(student_expr, gold_expr):
                    return 1.0
                # Compare both sides of equations
                lhs_diff = simplify(student_expr.lhs - gold_expr.lhs)
                rhs_diff = simplify(student_expr.rhs - gold_expr.rhs)
                
                if lhs_diff == 0 and rhs_diff == 0:
                    return 1.0
                
                # Check if differences are numerically close to zero
                try:
                    if abs(float(lhs_diff)) < self.tolerance and abs(float(rhs_diff)) < self.tolerance:
                        return 1.0
                except:
                    pass
                
                # Check if equations are equivalent (e.g., x = 2 vs 2 = x)
                if simplify(student_expr.lhs - gold_expr.rhs) == 0 and \
                   simplify(student_expr.rhs - gold_expr.lhs) == 0:
                    return 1.0
                
                return 0.0
            
            # Handle one equation and one expression
            if isinstance(student_expr, Eq) or isinstance(gold_expr, Eq):
                # If one is an equation and the other isn't, they can't be equivalent
                return 0.0
            
            # Both are expressions - check if they simplify to the same
            diff = simplify(student_expr - gold_expr)
            
            # If difference is zero (or very close), they're equivalent
            if diff == 0:
                return 1.0
            
            # Check if it's a constant close to zero (for numerical expressions)
            try:
                if abs(float(diff)) < self.tolerance:
                    return 1.0
            except:
                pass
            
            # Try comparing simplified forms
            student_simplified = simplify(student_expr)
            gold_simplified = simplify(gold_expr)
            if student_simplified == gold_simplified:
                return 1.0
            
        except Exception as e:
            # If parsing fails, they're not equivalent expressions
            return 0.0
        
        return 0.0
    
    def _check_derivation(self, student: str, gold: str) -> float:
        """
        Check if student step is a valid intermediate derivation leading to gold step.
        
        This is a heuristic check - it looks for common patterns like:
        - Student has part of the gold expression
        - Student shows work that would lead to gold step
        
        Returns:
            Score between 0 and 1
        """
        try:
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            
            # Check if student expression appears in gold expression's structure
            # This is a simplified heuristic
            student_str = str(student_expr)
            gold_str = str(gold_expr)
            
            # If student expression is a sub-expression of gold
            if student_str in gold_str or gold_str in student_str:
                return 0.6
            
            # Check if they share significant common terms
            student_terms = set(str(student_expr).replace(' ', '').split('+'))
            gold_terms = set(str(gold_expr).replace(' ', '').split('+'))
            common = student_terms.intersection(gold_terms)
            if len(common) > 0 and len(common) / max(len(student_terms), len(gold_terms)) > 0.5:
                return 0.5
            
        except:
            pass
        
        return 0.0
    
    def _parse_expression(self, text: str):
        """
        Try to parse a text string as a mathematical expression.
        Handles LaTeX, plain text, and equations.
        
        Returns:
            SymPy expression or None if parsing fails
        """
        if not text or not text.strip():
            return None
            
        # Remove LaTeX delimiters if present
        text = re.sub(r'^\$\$?(.*?)\$\$?$', r'\1', text.strip())
        text = re.sub(r'^\\\[(.*?)\\\]$', r'\1', text)
        text = re.sub(r'^\\\((.*?)\\\)$', r'\1', text)
        
        # Remove common prefixes like "=", "Step:", etc.
        text = re.sub(r'^(step\s*\d*:?\s*|solution:?\s*|answer:?\s*)', '', text, flags=re.IGNORECASE)
        text = text.strip()
        
        # Normalize common math functions (case-insensitive)
        # Convert LaTeX function commands to standard names
        function_map = {
            r'\\sin': 'sin',
            r'\\cos': 'cos',
            r'\\tan': 'tan',
            r'\\sec': 'sec',
            r'\\csc': 'csc',
            r'\\cot': 'cot',
            r'\\arcsin': 'asin',
            r'\\arccos': 'acos',
            r'\\arctan': 'atan',
            r'\\ln': 'log',  # Natural log
            r'\\log': 'log',
            r'\\exp': 'exp',
        }
        for latex_cmd, sympy_name in function_map.items():
            text = re.sub(latex_cmd + r'\(', sympy_name + '(', text, flags=re.IGNORECASE)
            text = re.sub(latex_cmd + r'\{', sympy_name + '(', text, flags=re.IGNORECASE)
        
        # Also handle plain text versions (case-insensitive)
        text = re.sub(r'\bsin\s*\(', 'sin(', text, flags=re.IGNORECASE)
        text = re.sub(r'\bcos\s*\(', 'cos(', text, flags=re.IGNORECASE)
        text = re.sub(r'\btan\s*\(', 'tan(', text, flags=re.IGNORECASE)
        text = re.sub(r'\bln\s*\(', 'log(', text, flags=re.IGNORECASE)
        
        # Convert common LaTeX commands to SymPy-friendly format
        # Handle fractions: \frac{a}{b} -> (a)/(b)
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
        # Handle sqrt: \sqrt{x} -> sqrt(x)
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', text)
        text = re.sub(r'\\sqrt\[(\d+)\]\{([^}]+)\}', r'root(\1, \2)', text)
        # Handle powers: x^{n} -> x**n or x^n -> x**n
        text = re.sub(r'\{([^}]+)\}\^\{([^}]+)\}', r'(\1)**(\2)', text)
        text = re.sub(r'([a-zA-Z0-9\)]+)\^\{([^}]+)\}', r'\1**(\2)', text)
        text = re.sub(r'([a-zA-Z0-9\)]+)\^([0-9]+)', r'\1**\2', text)
        # Handle subscripts: x_{n} -> x_n (SymPy handles this)
        text = re.sub(r'\{([^}]+)\}_\{([^}]+)\}', r'\1_\2', text)
        text = re.sub(r'([a-zA-Z0-9\)]+)_\{([^}]+)\}', r'\1_\2', text)
        # Remove remaining LaTeX braces
        text = re.sub(r'\{([^}]+)\}', r'\1', text)
        # Handle multiplication: \cdot, \times -> *
        text = re.sub(r'\\cdot|\\times', '*', text)
        # Handle division: \div -> /
        text = re.sub(r'\\div', '/', text)
        
        # Try to extract mathematical expressions
        # Look for equations (contains =)
        if '=' in text:
            parts = text.split('=', 1)
            try:
                lhs_str = parts[0].strip()
                rhs_str = parts[1].strip()
                lhs = parse_expr_safe(lhs_str, transformations='all')
                rhs = parse_expr_safe(rhs_str, transformations='all')
                return Eq(lhs, rhs)
            except Exception as e:
                # If parsing as equation fails, try to parse as single expression
                pass
        
        # Try as single expression
        try:
            return parse_expr_safe(text, transformations='all')
        except Exception as e:
            # If parsing fails, return None
            return None
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity metric (for non-mathematical explanations).
        
        Returns:
            Similarity score between 0 and 1
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if len(union) > 0 else 0.0


def create_grader_from_rubric(gold_steps: List[Tuple[str, float, bool]]) -> MathGrader:
    """
    Helper function to create a grader from a list of tuples.
    
    Args:
        gold_steps: List of (content, points, required) tuples
    
    Returns:
        MathGrader instance
    """
    steps = [Step(content, points, required) for content, points, required in gold_steps]
    return MathGrader(steps)

