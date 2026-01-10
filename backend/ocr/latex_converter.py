"""
LaTeX to Math Converter
Converts LaTeX notation to readable mathematical expressions for grading
"""
import re
import logging

logger = logging.getLogger(__name__)


class LaTeXConverter:
    """
    Converts LaTeX mathematical notation to readable format.
    Handles fractions, exponents, roots, operators, and formatting.
    """
    
    def __init__(self):
        """Initialize the converter with common LaTeX patterns."""
        # Define conversion patterns (order matters!)
        self.patterns = [
            # Remove formatting commands
            (r'\\overline\{([^}]+)\}', r'\1'),  # \overline{...} -> ...
            (r'\\underline\{([^}]+)\}', r'\1'),  # \underline{...} -> ...
            (r'\\text\{([^}]+)\}', r'\1'),  # \text{...} -> ...
            (r'\\mathrm\{([^}]+)\}', r'\1'),  # \mathrm{...} -> ...
            (r'\\mathit\{([^}]+)\}', r'\1'),  # \mathit{...} -> ...
            
            # Fractions: \frac{a}{b} -> (a)/(b) or a/b
            # Handle nested fractions by processing from innermost to outermost
            (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)'),
            
            # Square root: \sqrt{...} -> √(...)
            (r'\\sqrt\{([^}]+)\}', r'√(\1)'),
            
            # Nth root: \sqrt[n]{...} -> nth root of ...
            (r'\\sqrt\[([^\]]+)\]\{([^}]+)\}', r'(\2)^(1/\1)'),
            
            # Exponents: x^{2} -> x^2 or x²
            (r'([a-zA-Z0-9\)\]\}]+)\^\{([^}]+)\}', r'\1^\2'),
            (r'([a-zA-Z0-9\)\]\}]+)\^([0-9]+)', r'\1^\2'),  # x^2 without braces
            
            # Subscripts: x_{1} -> x_1
            (r'([a-zA-Z0-9\)\]\}]+)_\{([^}]+)\}', r'\1_\2'),
            (r'([a-zA-Z0-9\)\]\}]+)_([0-9]+)', r'\1_\2'),  # x_1 without braces
            
            # Greek letters (common ones)
            (r'\\alpha', 'α'),
            (r'\\beta', 'β'),
            (r'\\gamma', 'γ'),
            (r'\\delta', 'δ'),
            (r'\\epsilon', 'ε'),
            (r'\\theta', 'θ'),
            (r'\\lambda', 'λ'),
            (r'\\mu', 'μ'),
            (r'\\pi', 'π'),
            (r'\\sigma', 'σ'),
            (r'\\phi', 'φ'),
            (r'\\omega', 'ω'),
            
            # Operators
            (r'\\pm', '±'),
            (r'\\mp', '∓'),
            (r'\\times', '×'),
            (r'\\cdot', '·'),
            (r'\\div', '÷'),
            (r'\\leq', '≤'),
            (r'\\geq', '≥'),
            (r'\\neq', '≠'),
            (r'\\approx', '≈'),
            (r'\\equiv', '≡'),
            
            # Sets and logic
            (r'\\in', '∈'),
            (r'\\notin', '∉'),
            (r'\\subset', '⊂'),
            (r'\\cup', '∪'),
            (r'\\cap', '∩'),
            
            # Arrows
            (r'\\rightarrow', '→'),
            (r'\\leftarrow', '←'),
            (r'\\Rightarrow', '⇒'),
            (r'\\Leftarrow', '⇐'),
            (r'\\leftrightarrow', '↔'),
            
            # Infinity
            (r'\\infty', '∞'),
            
            # Sum, product, integral
            (r'\\sum', '∑'),
            (r'\\prod', '∏'),
            (r'\\int', '∫'),
            
            # Remove extra braces (after processing)
            (r'\{([a-zA-Z0-9+\-*/=±×÷≤≥≠≈≡∈∉⊂∪∩→←⇒⇐↔∞∑∏∫√()\[\],.\s]+)\}', r'\1'),
            
            # Clean up spacing
            (r'\s+', ' '),  # Multiple spaces to one
            (r'\s*([+\-*/=±×÷≤≥≠≈≡])\s*', r' \1 '),  # Space around operators
        ]
    
    def _convert_nested_braces(self, text: str, start: int = 0) -> tuple:
        """Recursively convert nested LaTeX structures."""
        result = []
        i = start
        
        while i < len(text):
            if text[i:i+5] == '\\frac':
                # Found a fraction
                i += 5  # Skip '\frac'
                
                # Find numerator
                if i < len(text) and text[i] == '{':
                    num_start = i + 1
                    num_end, num_content = self._extract_braced_content(text, num_start)
                    numerator = self._convert_nested_braces(num_content, 0)[0]
                    i = num_end + 1
                else:
                    numerator = ''
                
                # Find denominator
                if i < len(text) and text[i] == '{':
                    den_start = i + 1
                    den_end, den_content = self._extract_braced_content(text, den_start)
                    denominator = self._convert_nested_braces(den_content, 0)[0]
                    i = den_end + 1
                else:
                    denominator = ''
                
                result.append(f'({numerator})/({denominator})')
            else:
                result.append(text[i])
                i += 1
        
        return (''.join(result), i)
    
    def _extract_braced_content(self, text: str, start: int) -> tuple:
        """Extract content within matching braces."""
        if start >= len(text) or text[start-1] != '{':
            return (start, '')
        
        depth = 1
        i = start
        content_start = start
        
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        
        content = text[content_start:i-1] if depth == 0 else text[content_start:]
        return (i-1, content)
    
    def convert(self, latex_text: str) -> str:
        """
        Convert LaTeX notation to readable math.
        
        Args:
            latex_text: LaTeX formatted string
            
        Returns:
            Converted readable mathematical expression
        """
        if not latex_text or not latex_text.strip():
            return latex_text
        
        result = latex_text.strip()
        
        # First, handle nested fractions recursively
        if '\\frac' in result:
            result, _ = self._convert_nested_braces(result, 0)
        
        # Apply all other conversion patterns
        for pattern, replacement in self.patterns:
            try:
                # Skip fraction pattern as we handled it above
                if '\\frac' in pattern:
                    continue
                result = re.sub(pattern, replacement, result)
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                continue
        
        # Final cleanup
        result = result.strip()
        
        # Remove leading/trailing operators
        result = re.sub(r'^[+\-*/=±×÷≤≥≠≈≡]+', '', result)
        result = re.sub(r'[+\-*/=±×÷≤≥≠≈≡]+$', '', result)
        
        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        logger.debug(f"Converted: {latex_text} -> {result}")
        
        return result
    
    def convert_multiple(self, latex_list: list) -> list:
        """
        Convert multiple LaTeX strings.
        
        Args:
            latex_list: List of LaTeX strings
            
        Returns:
            List of converted strings
        """
        return [self.convert(latex) for latex in latex_list]
    
    def is_latex(self, text: str) -> bool:
        """
        Check if text contains LaTeX notation.
        
        Args:
            text: Text to check
            
        Returns:
            True if LaTeX detected
        """
        latex_indicators = [
            r'\\frac', r'\\sqrt', r'\\overline', r'\\underline',
            r'\\^\{', r'\\_\{', r'\\alpha', r'\\beta', r'\\pm',
            r'\\times', r'\\leq', r'\\geq', r'\\infty'
        ]
        
        for pattern in latex_indicators:
            if re.search(pattern, text):
                return True
        
        return False


def convert_latex_to_math(latex_text: str) -> str:
    """
    Convenience function to convert LaTeX to math.
    
    Args:
        latex_text: LaTeX formatted string
        
    Returns:
        Converted readable math
    """
    converter = LaTeXConverter()
    return converter.convert(latex_text)

