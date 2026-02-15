"""
Step Parser - Automatically separates OCR text into individual steps
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class StepParser:
    """
    Parses continuous OCR text into separate steps.
    Detects step boundaries using various heuristics.
    """
    
    def __init__(self):
        """Initialize the parser with detection patterns."""
        # Patterns that indicate step boundaries
        self.step_patterns = [
            r'^\s*\d+[\.\)]\s*',  # Numbered steps: "1.", "2)", "3. "
            r'^\s*[a-z][\.\)]\s*',  # Lettered steps: "a.", "b)"
            r'^\s*Step\s+\d+',  # "Step 1", "Step 2"
            r'^\s*[A-Z][a-z]+\s+\d+',  # "Problem 1", "Question 2"
            r'^\s*[Qq]\d+',  # "Q1", "q2"
            r'^\s*[Pp]\d+',  # "P1", "p2"
        ]
        
        # Patterns that indicate new equations/expressions
        self.expression_patterns = [
            r'=',  # Equations
            r'→',  # Arrows
            r'⇒',  # Implies
            r'∴',  # Therefore
            r'∵',  # Because
        ]
    
    def parse(self, text: str, min_step_length: int = 3) -> List[str]:
        """
        Parse text into separate steps.
        
        Args:
            text: Continuous text from OCR
            min_step_length: Minimum characters for a valid step
            
        Returns:
            List of step strings
        """
        if not text or not text.strip():
            return []
        
        # Split by newlines first
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return []
        
        steps = []
        current_step = []
        
        for line in lines:
            # Check if this line starts a new step
            is_new_step = self._is_step_start(line)
            
            if is_new_step and current_step:
                # Save previous step
                step_text = ' '.join(current_step).strip()
                if len(step_text) >= min_step_length:
                    steps.append(step_text)
                current_step = [line]
            else:
                # Continue current step
                current_step.append(line)
        
        # Add last step
        if current_step:
            step_text = ' '.join(current_step).strip()
            if len(step_text) >= min_step_length:
                steps.append(step_text)
        
        # If no steps detected, try splitting by common separators
        if len(steps) <= 1:
            steps = self._split_by_separators(text)
        
        # If still only one step, try splitting by equations
        if len(steps) <= 1:
            steps = self._split_by_equations(text)
        
        # Clean up steps
        steps = [self._clean_step(step) for step in steps if step.strip()]
        
        logger.info(f"Parsed {len(steps)} steps from text")
        
        return steps
    
    def _is_step_start(self, line: str) -> bool:
        """Check if a line starts a new step."""
        for pattern in self.step_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _split_by_separators(self, text: str) -> List[str]:
        """Split text by common separators."""
        # Common separators
        separators = [
            r'\s*;\s*',  # Semicolon
            r'\s*,\s*(?=[A-Za-z0-9])',  # Comma (but not in numbers)
            r'\s+and\s+',  # "and"
            r'\s+or\s+',  # "or"
            r'\s+then\s+',  # "then"
        ]
        
        steps = [text]
        
        for sep in separators:
            new_steps = []
            for step in steps:
                parts = re.split(sep, step)
                new_steps.extend([p.strip() for p in parts if p.strip()])
            steps = new_steps
        
        return steps
    
    def _split_by_equations(self, text: str) -> List[str]:
        """Split text by equations (lines with =)."""
        # Split by newlines that contain =
        lines = text.split('\n')
        
        steps = []
        current = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # If line contains =, it might be a new step
            if '=' in line and current:
                steps.append(' '.join(current))
                current = [line]
            else:
                current.append(line)
        
        if current:
            steps.append(' '.join(current))
        
        return steps if len(steps) > 1 else [text]
    
    def _clean_step(self, step: str) -> str:
        """Clean up a step string."""
        # Remove step numbers if present
        step = re.sub(r'^\s*\d+[\.\)]\s*', '', step)
        step = re.sub(r'^\s*[a-z][\.\)]\s*', '', step, flags=re.IGNORECASE)
        step = re.sub(r'^\s*Step\s+\d+\s*', '', step, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        step = re.sub(r'\s+', ' ', step).strip()
        
        # Remove leading/trailing punctuation
        step = step.strip('.,;:')
        
        return step
    
    def parse_with_context(self, text: str, context: dict = None) -> List[str]:
        """
        Parse with additional context (e.g., expected number of steps).
        
        Args:
            text: Text to parse
            context: Optional context dict with hints
            
        Returns:
            List of steps
        """
        steps = self.parse(text)
        
        # If context provides expected step count, try to match it
        if context and 'expected_steps' in context:
            expected = context['expected_steps']
            if len(steps) != expected and len(steps) == 1:
                # Try to split the single step
                steps = self._smart_split(steps[0], expected)
        
        return steps
    
    def _smart_split(self, text: str, num_parts: int) -> List[str]:
        """Intelligently split text into approximately num_parts."""
        if num_parts <= 1:
            return [text]
        
        # Try to find natural break points
        # Split by common math operators
        parts = re.split(r'([+\-*/=])', text)
        
        # Recombine with operators
        result = []
        current = []
        
        for i, part in enumerate(parts):
            current.append(part)
            # Try to balance the splits
            if len(result) < num_parts - 1 and len(''.join(current)) > len(text) // num_parts:
                result.append(''.join(current).strip())
                current = []
        
        if current:
            result.append(''.join(current).strip())
        
        return result if len(result) > 1 else [text]


def parse_steps(text: str) -> List[str]:
    """
    Convenience function to parse text into steps.
    
    Args:
        text: Continuous text
        
    Returns:
        List of step strings
    """
    parser = StepParser()
    return parser.parse(text)

