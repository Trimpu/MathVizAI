"""
Mathematical utility functions for the Manim integration project.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def extract_math_expressions(text: str) -> List[str]:
    """
    Extract mathematical expressions from text using regex patterns.

    Args:
        text: Input text containing mathematical expressions

    Returns:
        List of extracted mathematical expressions
    """
    # Common LaTeX math delimiters
    patterns = [
        r'\$\$([^$]+)\$\$',  # Display math: $$
        r'\$([^$]+)\$',      # Inline math: $
        r'\\\[([^\\]+)\\\]', # Display math: \[
        r'\\\(([^\\]+)\\\)', # Inline math: \(
        r'\\begin\{equation\}(.*?)\\end\{equation\}',  # Equation environment
        r'\\begin\{align\}(.*?)\\end\{align\}',        # Align environment
        r'\\begin\{gather\}(.*?)\\end\{gather\}',      # Gather environment
    ]

    expressions = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        expressions.extend(matches)

    # Remove duplicates while preserving order
    seen = set()
    unique_expressions = []
    for expr in expressions:
        expr_clean = expr.strip()
        if expr_clean and expr_clean not in seen:
            seen.add(expr_clean)
            unique_expressions.append(expr_clean)

    return unique_expressions

def analyze_math_content(text: str) -> Dict[str, Any]:
    """
    Analyze mathematical content in text.

    Args:
        text: Input text to analyze

    Returns:
        Dictionary containing analysis results
    """
    expressions = extract_math_expressions(text)
    complexity_score = _calculate_complexity_score(expressions)
    
    # Determine content type
    content_type = 'general'
    if any(op in text for op in ['\\int', '\\iint', '\\iiint']):
        content_type = 'integral'
    elif any(op in text for op in ['\\sum', '\\prod']):
        content_type = 'series'
    elif any(op in text for op in ['\\frac{d}{dx}', '\\partial', '\\nabla']):
        content_type = 'derivative'
    elif any(op in text for op in ['\\lim']):
        content_type = 'limit'
    elif any(mat in text for mat in ['\\begin{matrix}', '\\begin{pmatrix}', '\\begin{bmatrix}']):
        content_type = 'matrix'
    
    # Determine complexity level
    if complexity_score < 0.3:
        complexity = 'simple'
    elif complexity_score < 0.6:
        complexity = 'moderate'
    else:
        complexity = 'advanced'
    
    # Identify visual concepts
    visual_concepts = []
    if 'integral' in content_type or 'derivative' in content_type:
        visual_concepts.append('function graph')
        visual_concepts.append('coordinate system')
    if 'integral' in content_type:
        visual_concepts.append('area under curve')
        visual_concepts.append('approximation')
    if 'matrix' in content_type:
        visual_concepts.append('grid layout')
        visual_concepts.append('transformation')
    if '\\theta' in text or 'sin' in text or 'cos' in text:
        visual_concepts.append('trigonometry')
    if 'series' in content_type:
        visual_concepts.append('sequence')
        visual_concepts.append('sum notation')
    
    # Default visual concepts if none identified
    if not visual_concepts:
        visual_concepts = ['mathematical notation', 'step-by-step derivation']
    
    # Determine educational focus
    educational_focus = f"Understanding {content_type} concepts through visualization"

    analysis = {
        'total_expressions': len(expressions),
        'expressions': expressions,
        'has_math': len(expressions) > 0,
        'math_density': len(''.join(expressions)) / len(text) if text else 0,
        'complexity_score': complexity_score,
        'type': content_type,
        'complexity': complexity,
        'visual_concepts': visual_concepts,
        'educational_focus': educational_focus
    }

    return analysis

def _calculate_complexity_score(expressions: List[str]) -> float:
    """
    Calculate a complexity score for mathematical expressions.

    Args:
        expressions: List of mathematical expressions

    Returns:
        Complexity score (0-1, higher is more complex)
    """
    if not expressions:
        return 0.0

    total_score = 0.0
    for expr in expressions:
        score = 0.0

        # Check for advanced operations
        if any(op in expr for op in ['\\int', '\\sum', '\\prod', '\\lim']):
            score += 0.3

        # Check for fractions
        if '\\frac' in expr:
            score += 0.2

        # Check for matrices/vectors
        if any(mat in expr for mat in ['\\begin{matrix}', '\\begin{pmatrix}', '\\begin{bmatrix}']):
            score += 0.4

        # Check for derivatives
        if any(deriv in expr for deriv in ['\\frac{d}{dx}', '\\partial', '\\nabla']):
            score += 0.3

        # Check for complex functions
        if any(func in expr for func in ['\\sin', '\\cos', '\\tan', '\\log', '\\ln', '\\exp']):
            score += 0.1

        # Length factor (longer expressions tend to be more complex)
        length_factor = min(len(expr) / 200, 1.0)  # Cap at 200 chars
        score += length_factor * 0.2

        total_score += min(score, 1.0)  # Cap individual expression score

    return min(total_score / len(expressions), 1.0) if expressions else 0.0

def validate_latex_syntax(latex_str: str) -> Tuple[bool, Optional[str]]:
    """
    Basic validation of LaTeX syntax.

    Args:
        latex_str: LaTeX string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Basic checks for common LaTeX syntax errors
        errors = []

        # Check for unmatched braces
        brace_count = latex_str.count('{') - latex_str.count('}')
        if brace_count != 0:
            errors.append(f"Unmatched braces: {brace_count} extra {'{' if brace_count > 0 else '}'}")

        # Check for unmatched parentheses in math mode
        if '\\(' in latex_str or '\\)' in latex_str:
            paren_count = latex_str.count('\\(') - latex_str.count('\\)')
            if paren_count != 0:
                errors.append(f"Unmatched math parentheses: {paren_count} extra \\(")

        # Check for common command errors
        if '\\\\' in latex_str and not any(env in latex_str for env in ['\\begin{tabular}', '\\begin{array}']):
            # Allow double backslashes in tabular/array environments
            pass

        # Check for empty commands
        empty_commands = re.findall(r'\\[a-zA-Z]+\{\}', latex_str)
        if empty_commands:
            errors.append(f"Empty commands found: {', '.join(empty_commands[:3])}")

        if errors:
            return False, '; '.join(errors)

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"

def sanitize_math_input(math_input: str) -> str:
    """
    Sanitize mathematical input to prevent injection or malformed content.

    Args:
        math_input: Raw mathematical input

    Returns:
        Sanitized mathematical input
    """
    if not math_input:
        return ""

    # Remove potentially dangerous LaTeX commands
    dangerous_commands = [
        '\\input', '\\include', '\\usepackage', '\\documentclass',
        '\\write', '\\read', '\\openin', '\\openout'
    ]

    sanitized = math_input
    for cmd in dangerous_commands:
        sanitized = sanitized.replace(cmd, '')

    # Limit length to prevent resource exhaustion
    max_length = 10000
    if len(sanitized) > max_length:
        logger.warning(f"Math input too long ({len(sanitized)}), truncating to {max_length}")
        sanitized = sanitized[:max_length]

    return sanitized.strip()

def format_math_for_display(math_expr: str, display_mode: bool = True) -> str:
    """
    Format mathematical expression for display.

    Args:
        math_expr: Mathematical expression
        display_mode: Whether to use display math mode

    Returns:
        Formatted LaTeX string
    """
    if not math_expr.strip():
        return ""

    # Clean up the expression
    expr = math_expr.strip()

    # Wrap in appropriate delimiters
    if display_mode:
        return f"$${expr}$$"
    else:
        return f"${expr}$"