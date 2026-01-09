#!/usr/bin/env python3
"""
Unified OCR + Manim Backend Server
Flask server that provides both OCR and Manim video generation APIs.
Uses MixTeX for LaTeX OCR extraction and Manim for video generation.
"""

import os
import sys
import base64
import io
import uuid
import time
import threading
import glob
import shutil
import re
import tempfile
import json
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import numpy as np
import traceback
import logging

# Add the mixtex path to the system path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mixtexgui'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'mixtexgui', 'examples'))

# Import MixTeX core functionality
try:
    from mixtex_core import load_model, pad_image, stream_inference, convert_align_to_equations
    print("✅ Successfully imported MixTeX core modules")
    MIXTEX_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MixTeX modules not available: {e}")
    MIXTEX_AVAILABLE = False

# Import Manim functionality
try:
    from manim import Scene, Text, MathTex, Write, FadeOut, UP, DOWN, LEFT, RIGHT, BLUE, RED, GREEN, YELLOW, WHITE, BLACK
    print("✅ Successfully imported Manim")
    MANIM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Manim not available: {e}")
    MANIM_AVAILABLE = False

# Import OpenAI for AI-powered scene generation
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
    AI_AVAILABLE = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENAI_API_KEY"))
    print(f"✅ AI integration {'available' if AI_AVAILABLE else 'not configured'}")
except ImportError as e:
    print(f"⚠️ AI integration not available: {e}")
    AI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configure logging to reduce verbosity for repetitive status checks
class StatusCheckFilter(logging.Filter):
    def filter(self, record):
        # Suppress logs for status check endpoints that spam the console
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # Filter out repetitive GET requests to status endpoints
            if 'GET /api/status/' in message and '200' in message:
                return False
        return True

# Apply the filter to werkzeug logger (Flask's request logger)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(StatusCheckFilter())
werkzeug_logger.setLevel(logging.INFO)  # Keep other logs but filter status checks  # Enable CORS for React frontend

# Global model variable
model = None
model_loaded = False
model_error = None

# Global variables for video generation
video_output_dir = os.path.join(os.path.dirname(__file__), 'videos')
tasks_file = os.path.join(os.path.dirname(__file__), 'tasks.json')

# Persistent task storage functions
def load_tasks():
    """Load tasks from persistent storage"""
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load tasks file: {e}")
            return {}
    return {}

def save_tasks(tasks):
    """Save tasks to persistent storage"""
    try:
        # Atomic write using temporary file
        temp_file = tasks_file + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(tasks, f, indent=2)
        
        # Replace original file atomically
        if os.name == 'nt':  # Windows
            if os.path.exists(tasks_file):
                os.remove(tasks_file)
            os.rename(temp_file, tasks_file)
        else:  # Unix/Linux
            os.rename(temp_file, tasks_file)
    except IOError as e:
        logger.error(f"Failed to save tasks file: {e}")

def update_task(task_id, updates):
    """Update a task and save to persistent storage"""
    tasks = load_tasks()
    if task_id in tasks:
        tasks[task_id].update(updates)
    else:
        tasks[task_id] = updates
    save_tasks(tasks)
    return tasks[task_id]

def get_task(task_id):
    """Get a task from persistent storage"""
    tasks = load_tasks()
    return tasks.get(task_id)

def cleanup_old_tasks(max_age_hours=24):
    """Remove tasks older than max_age_hours"""
    tasks = load_tasks()
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    cleaned_tasks = {}
    removed_count = 0
    
    for task_id, task in tasks.items():
        task_age = current_time - task.get('created_at', current_time)
        if task_age < max_age_seconds:
            cleaned_tasks[task_id] = task
        else:
            removed_count += 1
            # Clean up video file if it exists
            video_path = task.get('video_path')
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"Removed old video file: {video_path}")
                except OSError:
                    pass
    
    if removed_count > 0:
        save_tasks(cleaned_tasks)
        logger.info(f"Cleaned up {removed_count} old tasks")
    
    return cleaned_tasks

# Load existing tasks on startup and clean old ones
video_tasks = cleanup_old_tasks()
logger.info(f"Loaded {len(video_tasks)} existing tasks from persistent storage")

def initialize_model():
    """Initialize the MixTeX model on server startup"""
    global model, model_loaded, model_error
    
    if not MIXTEX_AVAILABLE:
        print("⚠️ MixTeX not available, OCR functionality will be disabled")
        model_loaded = False
        model_error = "MixTeX modules not available"
        return False
    
    try:
        print("🔄 Initializing MixTeX model...")
        
        # Try to find the onnx model directory
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'mixtexgui', 'onnx'),
            os.path.join(os.path.dirname(__file__), '..', 'onnx'),
            os.path.join(os.path.dirname(__file__), 'onnx'),
        ]
        
        onnx_path = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                onnx_path = abs_path
                break
        
        if not onnx_path:
            raise FileNotFoundError(f"Could not find onnx model directory in any of: {possible_paths}")
        
        print(f"📁 Using model path: {onnx_path}")
        
        # Load the model
        model = load_model(onnx_path)
        model_loaded = True
        model_error = None
        
        print("✅ MixTeX model loaded successfully!")
        return True
        
    except Exception as e:
        error_msg = f"Failed to load MixTeX model: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"📄 Traceback: {traceback.format_exc()}")
        model_loaded = False
        model_error = error_msg
        return False

def preprocess_image(image, preprocessing_level='moderate'):
    """
    Preprocess the image based on the specified level
    """
    try:
        if preprocessing_level == 'minimal':
            return image
        
        elif preprocessing_level == 'moderate':
            # Basic cleanup - resize to standard size and ensure RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return image
            
        elif preprocessing_level == 'aggressive':
            # More preprocessing - convert to grayscale, enhance contrast
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to grayscale for better OCR
            image = image.convert('L').convert('RGB')
            
            return image
        
        else:
            return image
            
    except Exception as e:
        logger.error(f"Error in image preprocessing: {e}")
        return image

def extract_latex_from_image(image, preprocessing_level='moderate'):
    """
    Extract LaTeX content from image using MixTeX model
    """
    global model, model_loaded
    
    if not model_loaded or model is None:
        raise Exception("MixTeX model is not loaded")
    
    try:
        # Preprocess the image
        processed_image = preprocess_image(image, preprocessing_level)
        
        # Pad image to required dimensions (448x448 for MixTeX)
        padded_image = pad_image(processed_image, (448, 448))
        
        # Extract LaTeX using MixTeX streaming inference
        latex_parts = []
        for piece in stream_inference(padded_image, model):
            latex_parts.append(piece)
        
        # Join all parts to get complete LaTeX
        full_latex = ''.join(latex_parts)
        
        # Clean up the output
        full_latex = full_latex.strip()
        
        # Replace common formatting
        full_latex = full_latex.replace('\\[', '\\begin{align*}').replace('\\]', '\\end{align*}')
        full_latex = full_latex.replace('%', '\\%')
        
        return full_latex
        
    except Exception as e:
        logger.error(f"Error in LaTeX extraction: {e}")
        raise

# AI-powered Manim scene generation
def generate_manim_code_with_ai(latex_content, topic="Mathematical Expression"):
    """
    Generate educational Manim code using AI for the given LaTeX content.

    Updated Philosophy:
    - Visual-first narrative: show geometry/process before symbols.
    - Text is cumulative: previously shown short captions remain; new lines append beneath (no overlap).
    - No harsh constraints like forced removal of prior text unless transitioning to a new major phase.
    - Avoid dense paragraphs: each caption line is a concise conceptual cue.
    - Integral (or other structure) should emerge from previous visual approximations.

    This function now:
    - Removes the old strict "CRITICAL FINAL REQUIREMENT" block.
    - Instructs AI to build a caption panel that stacks lines (like a running conceptual transcript).
    - Encourages structured phases (axes → function → region → approximation → refinement → symbol → numeric).
    """
    if not AI_AVAILABLE:
        return None

    try:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENAI_API_KEY")
        if os.environ.get("GITHUB_TOKEN"):
            client = OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=token,
            )
            model = "gpt-4o"
        else:
            client = OpenAI(api_key=token)
            model = "gpt-4o"

        system_prompt = """You are an expert Manim scene designer focused on VISUAL-FIRST mathematical storytelling.

CORE PRINCIPLES:
- Visuals introduce concepts; symbols summarize them.
- Show processes (graph drawing, area filling, refining rectangles, morphing to integral).
- Captions accumulate as a vertical stack (concept log). Do NOT overlap text; each new line appears below previous lines in a caption panel.
- Keep each caption line short (≤ ~55 characters). No large paragraphs.
- Only clear the scene (self.clear()) for major phase transitions (if needed). Otherwise keep visuals and keep adding to the caption panel.
- Use consistent styling: captions at bottom or lower-left; math visuals centered or appropriately placed.
- Prefer constructive animations: Create, FadeIn, Transform, ReplacementTransform.
- If rendering an integral: sequence should feel like rectangles → limiting behavior → integral symbol appears → evaluation result.

TECHNICAL REQUIREMENTS:
1. Define class LaTeXScene(Scene) with construct(self).
2. Use try/except for MathTex fallback to Text when necessary.
3. Maintain a caption panel: a Python list or VGroup of Text/MathTex lines.
   - When adding a new line:
       new_line.next_to(previous_line, DOWN, aligned_edge=LEFT, buff=0.25)
   - First line: anchor with .to_edge(DOWN) or .to_corner(DL).
4. Do not remove previous caption lines; they remain as historical context unless performing a full phase reset.
5. Avoid clutter: keep total caption lines reasonable (e.g. ≤ 8–10).
6. Use color coding sparingly (e.g. important symbol or final result).
7. Use explicit positions for major math objects (axes at center, function above region, etc.).
8. Keep code self-contained (no external assets).
9. For function y = x^2 integrals: definitely show axes, curve, shaded region, coarse rectangles, refinement, then emergence of ∫ and final numeric value.

ERROR RESILIENCE:
- Wrap suspicious LaTeX in try/except; fallback gracefully.

DO NOT:
- Produce giant blocks of explanatory text.
- Overwrite previous captions by default.
- Leave overlapping text objects.
- Use TransformMatchingTex (stick to Transform / ReplacementTransform).

Return ONLY the Python code for LaTeXScene (no markdown fences)."""

        analysis = analyze_mathematical_content(latex_content)

        user_prompt = f"""Create a VISUAL-FIRST Manim animation.

RAW CONTENT: {latex_content}

ANALYSIS:
- Type: {analysis['type']}
- Complexity: {analysis['complexity']}
- Visual Concepts: {', '.join(analysis['visual_concepts'])}
- Educational Focus: {analysis['educational_focus']}

SCENE OBJECTIVE:
Let the viewer SEE the underlying mathematical process unfold before the symbolic form is finalized.

REQUIRED VISUAL FLOW (ADAPT if appropriate):
1. Axes / coordinate frame (only if relevant to the content).
2. Function curve (if an integral or function).
3. Domain / interval highlight (if bounds exist).
4. Shaded region (if area/accumulation).
5. Approximation objects (rectangles / slices for integrals; discrete bars for sums; tangent lines for derivatives; approach markers for limits).
6. Refinement or evolution (e.g., more rectangles).
7. Emergence of symbolic form (Σ → ∫, derivative notation, etc.).
8. Final evaluation or simplified symbolic expression.
9. Concluding highlight of final result.

CAPTION PANEL:
- Maintain a list of short lines; each new conceptual milestone adds one line.
- Example line sequence (for integral): ['Curve y = x^2', 'Target area 0→2', 'Coarse rectangles', 'Refinement', 'Integral emerges', 'Exact area 8/3']
- Each line appended below the previous using next_to.

CODING PATTERN FOR CAPTIONS (MANDATORY STYLE):
caption_lines = []
line1 = Text("Curve y = x^2", font_size=24)
line1.to_edge(DOWN).to_corner(DL)
self.play(Write(line1))
caption_lines.append(line1)

line2 = Text("Target area 0→2", font_size=24)
line2.next_to(caption_lines[-1], DOWN, aligned_edge=LEFT, buff=0.25)
self.play(FadeIn(line2))
caption_lines.append(line2)

If too many lines accumulate for your case, you may (optionally) fade out earlier ones as a batch before continuing, but only if necessary for readability.

INTEGRAL-SPECIFIC SUGGESTIONS (if integral detected):
- Use axes = Axes(x_range=[-0.5, 3], y_range=[-0.5, 5]) (adjust if needed)
- Plot function via axes.plot(lambda x: x**2)
- Region: axes.get_area(graph, x_range=[0,2], color=BLUE, opacity=0.4)
- Rectangles: manually build with for-loop or use Riemann rectangle logic
- Refine via Transform old group → new group (NOT ReplacementTransform)
- Introduce integral symbol near upper-right or above region
- Evaluate: final MathTex with result (e.g. r"\\int_0^2 x^2 \\, dx = \\frac{8}{3}")

CRITICAL API REQUIREMENTS (Manim v0.17+):
- Use 'color=' not 'colors=' in get_riemann_rectangles()
- Use 'Create()' not 'ShowCreation()'
- Use 'Transform()' not 'ReplacementTransform()'
- Use 'FadeIn()' and 'FadeOut()' for object transitions
- Parameter names: 'color', 'fill_color', 'stroke_color' (singular forms)

IF TYPE is not integral, adapt analogous conceptual decomposition.

Return ONLY the Python code for the LaTeXScene class with correct modern API."""

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            temperature=0.7,
            max_tokens=1900
        )

        if not response.choices or not response.choices[0].message.content:
            return None

        generated_code = response.choices[0].message.content.strip()

        # Strip accidental fenced code blocks if present
        import re
        generated_code = re.sub(r'```(?:python)?\s*', '', generated_code)
        generated_code = generated_code.replace('```', '').strip()

        print(f"🤖 AI generated Manim code ({len(generated_code)} chars)")
        return generated_code

    except Exception as e:
        print(f"❌ AI code generation failed: {e}")
        return None
def fix_text_overlap_issues(manim_code):
    """Post-process AI-generated Manim code to prevent text overlaps and fix indentation"""
    
    # First, fix any basic indentation issues
    lines = manim_code.split('\n')
    fixed_lines = []
    in_method = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append('')
            continue
            
        # Handle import statements (should have no indentation)
        if stripped.startswith('from ') or stripped.startswith('import '):
            fixed_lines.append(stripped)
            continue
            
        # Handle class definition (should have no indentation)
        if stripped.startswith('class '):
            fixed_lines.append(stripped)
            in_method = False
            continue
            
        # Handle method definition (should have 4 spaces)
        if stripped.startswith('def '):
            fixed_lines.append('    ' + stripped)
            in_method = True
            continue
            
        # Handle method content - should be indented with 8 spaces
        if in_method and stripped:
            # Ensure proper 8-space indentation for method body
            if line.startswith('        '):  # Already has 8 spaces
                fixed_lines.append(line)
            elif line.startswith('    '):  # Has 4 spaces, need 4 more
                fixed_lines.append('    ' + line)
            else:  # No proper indentation, add 8 spaces
                fixed_lines.append('        ' + stripped)
        else:
            fixed_lines.append(line)
    
    # Now apply text overlap fixes
    processed_lines = []
    text_objects = []
    
    for i, line in enumerate(fixed_lines):
        stripped = line.strip()
        
        # Detect text object creation and fix positioning
        if ('Text(' in stripped or 'MathTex(' in stripped) and '=' in stripped:
            var_name = stripped.split('=')[0].strip()
            text_objects.append(var_name)
            
            # Add the text creation line
            processed_lines.append(line)
            
            # Check if positioning follows in next few lines
            has_positioning = False
            for j in range(i+1, min(i+4, len(fixed_lines))):
                if j < len(fixed_lines) and any(pos in fixed_lines[j] for pos in ['.to_edge', '.next_to', '.shift', '.center']):
                    has_positioning = True
                    break
            
            # Add positioning if missing
            if not has_positioning:
                indent = '        '  # Method body indentation
                if 'title' in var_name.lower():
                    processed_lines.append(f"{indent}{var_name}.to_edge(UP)")
                elif len(text_objects) == 1:
                    processed_lines.append(f"{indent}{var_name}.center()")
                else:
                    processed_lines.append(f"{indent}{var_name}.to_edge(DOWN)")
            continue
        
        # Fix multiple center() calls
        if '.center()' in stripped and len(text_objects) > 1:
            if 'title' not in stripped.lower():
                line = line.replace('.center()', '.to_edge(DOWN)')
        
        processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def validate_manim_code_structure(code):
    """Validate Manim code for common text overlap issues and syntax problems"""
    errors = []
    
    # Check for multiple .center() calls
    center_count = code.count('.center()')
    if center_count > 1:
        errors.append(f"Multiple .center() calls found ({center_count})")
    
    # Check for Text objects without positioning
    text_lines = [line for line in code.split('\n') if 'Text(' in line and '=' in line]
    positioning_lines = [line for line in code.split('\n') if any(pos in line for pos in ['.to_edge', '.next_to', '.center'])]
    
    if len(text_lines) > len(positioning_lines):
        errors.append("Text objects without explicit positioning found")
    
    # Check for missing self.remove() or self.clear() calls
    if 'self.remove(' not in code and 'self.clear()' not in code and len(text_lines) > 2:
        errors.append("No cleanup calls found for multiple text objects")
    
    # Check for basic syntax issues
    syntax_errors = validate_python_syntax(code)
    errors.extend(syntax_errors)
    
    return errors

def validate_python_syntax(code):
    """Check for common Python syntax errors"""
    errors = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
            
        # Check for unclosed parentheses
        open_parens = line.count('(')
        close_parens = line.count(')')
        if open_parens != close_parens:
            errors.append(f"Unmatched parentheses on line {i}")
            
        # Check for missing commas in function calls
        import re
        if '(' in line and ')' in line:
            # Find content inside parentheses
            matches = re.findall(r'\(([^)]+)\)', line)
            for match in matches:
                # Check if it looks like multiple arguments without commas
                if ' ' in match and ',' not in match and '=' not in match:
                    # Skip if it's a single string argument
                    if not (match.strip().startswith('"') or match.strip().startswith("'")):
                        errors.append(f"Possible missing comma in function call on line {i}")
        
        # Check for incomplete method chains
        if '.to_edge(' in line and '.to_corner' in line and not ').to_corner' in line:
            errors.append(f"Incomplete method chain on line {i}")
            
    return errors

def fix_severe_syntax_errors(code):
    """Apply more aggressive fixes for severe syntax errors"""
    lines = code.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
            
        # Fix method chaining issues
        if '.to_edge(' in line and '.to_corner' in line:
            # Ensure proper method chaining: .to_edge(param).to_corner(param)
            import re
            line = re.sub(r'\.to_edge\(([^)]+)\)\.to_corner', r'.to_edge(\1).to_corner', line)
            line = re.sub(r'\.to_edge\(([^)]+)\.to_corner', r'.to_edge(\1).to_corner', line)
        
        # Fix incomplete function calls
        stripped_line = line.strip()
        if (('self.play(' in stripped_line or 'Text(' in stripped_line or 'MathTex(' in stripped_line) 
            and stripped_line.count('(') > stripped_line.count(')')):
            # Add missing closing parentheses
            missing_parens = stripped_line.count('(') - stripped_line.count(')')
            line += ')' * missing_parens
            
        # Fix missing commas in Text/MathTex calls
        import re
        if 'Text(' in line or 'MathTex(' in line:
            # Pattern: Text("string" font_size=24) -> Text("string", font_size=24)
            line = re.sub(r'(Text\([^)]*?["\'])(\s+)(\w+\s*=)', r'\1,\2\3', line)
            line = re.sub(r'(MathTex\([^)]*?["\'])(\s+)(\w+\s*=)', r'\1,\2\3', line)
        
        # Fix incomplete lines that end with dots
        if stripped_line.endswith('.'):
            line = line[:-1]  # Remove trailing dot
            
        # Ensure proper string quoting
        # Fix unquoted text in Text() calls
        line = re.sub(r'Text\(([^"\'()][^"\'()]*[^"\'(),])\s*\)', r'Text("\1")', line)
        
        fixed_lines.append(line)
    
    # Final pass to ensure proper structure
    result = '\n'.join(fixed_lines)
    
    # Replace any remaining problematic patterns
    result = re.sub(r'([^,\s])\s+(\w+\s*=)', r'\1, \2', result)  # Add commas before keyword args
    
    return result

def fix_manim_api_compatibility(code):
    """Fix common Manim API compatibility issues"""
    import re
    
    # Fix parameter name changes
    fixes = {
        # Riemann rectangles parameter fix - most common issue
        'colors=': 'color=',
        'colours=': 'color=',
        
        # Animation method changes
        'ShowCreation(': 'Create(',
        'DrawBorderThenFill(': 'Create(',
        'ShowIncreasingSubsets(': 'Create(',
        'ShowSubmobjectsOneByOne(': 'Create(',
        
        # Transform method changes
        'ReplacementTransform(': 'Transform(',
        'TransformMatchingTex(': 'Transform(',
        
        # Method name changes
        '.fade(': '.set_opacity(',
        '.scale_about_point(': '.scale(',
        '.rotate_about_origin(': '.rotate(',
        
        # Color parameter variations
        'fill_colours=': 'fill_color=',
        'stroke_colours=': 'stroke_color=',
        'edge_colours=': 'edge_color=',
        
        # Configuration parameter changes
        'background_colour=': 'background_color=',
        'tex_colour=': 'tex_color=',
    }
    
    result = code
    for old, new in fixes.items():
        result = result.replace(old, new)
    
    # Fix specific method calls with regex patterns
    # Fix get_riemann_rectangles with colors parameter specifically
    result = re.sub(r'\.get_riemann_rectangles\([^)]*\bcolors\s*=', 
                   lambda m: m.group(0).replace('colors=', 'color='), result)
    
    # Fix other regex patterns
    result = re.sub(r'(\w+\([^)]*?)colours(\s*=\s*[^,)]+)', r'\1color\2', result)
    result = re.sub(r'\.set_colour\(', '.set_color(', result)
    result = re.sub(r'\.get_colour\(', '.get_color(', result)
    
    return result

def apply_emergency_fixes(code):
    """Apply emergency fixes to problematic Manim code with proper indentation and syntax fixes"""
    lines = code.split('\n')
    fixed_lines = []
    in_method = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            fixed_lines.append('')
            continue
            
        # Handle imports (no indentation)
        if stripped.startswith('from ') or stripped.startswith('import '):
            fixed_lines.append(stripped)
            in_method = False
        # Handle class definitions (no indentation)
        elif stripped.startswith('class '):
            fixed_lines.append(stripped)
            in_method = False
        # Handle method definitions (4 spaces)
        elif stripped.startswith('def '):
            fixed_lines.append('    ' + stripped)
            in_method = True
        else:
            # Method body content - ensure 8-space indentation
            if in_method:
                if not line.startswith('        '):
                    line = '        ' + stripped
                
                # Fix common syntax issues
                line = fix_common_syntax_errors(line)
                
                # Replace multiple center() calls with proper positioning
                if '.center()' in line and 'title' not in line.lower():
                    line = line.replace('.center()', '.to_edge(DOWN)')
                
                fixed_lines.append(line)
            else:
                # Outside method, keep as is
                fixed_lines.append(line)
        
        # Add cleanup between text sections
        if i < len(lines) - 1 and 'self.play(Write(' in line:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if 'Text(' in next_line or 'MathTex(' in next_line:
                recent_lines = lines[max(0, i-5):i]
                if not any('self.clear()' in recent for recent in recent_lines):
                    if any('Text(' in recent for recent in recent_lines):
                        fixed_lines.append("        self.wait(1)")
                        fixed_lines.append("        self.clear()")
    
    return '\n'.join(fixed_lines)

def fix_common_syntax_errors(line):
    """Fix common Python syntax errors in a line of code"""
    stripped = line.strip()
    
    # Fix missing commas in method calls
    # Look for patterns like: method(arg1 arg2) -> method(arg1, arg2)
    import re
    
    # Fix missing commas between function arguments
    # Pattern: word( stuff word stuff ) -> word( stuff, word stuff )
    line = re.sub(r'(\w+\([^)]*?)(\s+)(\w+[^),]*)', r'\1,\2\3', line)
    
    # Fix missing parentheses in method calls
    # Pattern: .method -> .method()
    if '.' in stripped and not stripped.endswith(')') and not '=' in stripped and not stripped.startswith('#'):
        if re.match(r'.*\.\w+$', stripped.strip()):
            line = line.rstrip() + '()'
    
    # Fix incomplete method calls like .to_edge(DOWN.to_corner -> .to_edge(DOWN).to_corner
    line = re.sub(r'\.to_edge\((\w+)\.to_corner', r'.to_edge(\1).to_corner', line)
    
    # Fix missing quotes around strings
    # Pattern: Text(Some text) -> Text("Some text")
    line = re.sub(r'Text\(([^"\'()][^"\'()]*[^"\'()])\)', r'Text("\1")', line)
    
    # Ensure proper parentheses matching
    open_parens = line.count('(')
    close_parens = line.count(')')
    if open_parens > close_parens:
        line += ')' * (open_parens - close_parens)
    
    return line

def analyze_mathematical_content(latex_content):
    """Analyze mathematical content to identify structure and create visual-first prompts"""
    
    content_analysis = {
        'type': 'unknown',
        'complexity': 'basic',
        'visual_concepts': [],
        'key_operations': [],
        'educational_focus': 'explanation'
    }
    
    # Detect mathematical content types
    if re.search(r'\\int|∫', latex_content):
        content_analysis['type'] = 'integral'
        content_analysis['visual_concepts'] = ['function_graph', 'area_under_curve', 'riemann_sums']
        content_analysis['educational_focus'] = 'Show the curve, highlight the region, animate rectangles becoming integral'
        
    elif re.search(r'\\frac|\\dfrac|/', latex_content):
        content_analysis['type'] = 'fraction'
        content_analysis['visual_concepts'] = ['division_visualization', 'part_whole_relationship']
        content_analysis['educational_focus'] = 'Visual division, pie charts, or bar representations'
        
    elif re.search(r'\\sum|Σ', latex_content):
        content_analysis['type'] = 'summation'
        content_analysis['visual_concepts'] = ['sequence_visualization', 'accumulation']
        content_analysis['educational_focus'] = 'Show terms adding up step by step'
        
    elif re.search(r'\\sqrt|√', latex_content):
        content_analysis['type'] = 'square_root'
        content_analysis['visual_concepts'] = ['geometric_squares', 'number_line']
        content_analysis['educational_focus'] = 'Geometric interpretation of square roots'
        
    elif re.search(r'\^.*2|x\s*\*\s*x|squared', latex_content):
        content_analysis['type'] = 'quadratic'
        content_analysis['visual_concepts'] = ['parabola', 'vertex_form', 'transformations']
        content_analysis['educational_focus'] = 'Show parabola formation and key features'
        
    elif re.search(r'=.*solve|find|calculate|evaluate', latex_content.lower()):
        content_analysis['type'] = 'equation_solving'
        content_analysis['visual_concepts'] = ['algebraic_steps', 'balance_visualization']
        content_analysis['educational_focus'] = 'Show equation balancing and step-by-step solving'
        
    elif re.search(r'derivative|\\frac\{d\}|d/dx|f\'', latex_content):
        content_analysis['type'] = 'derivative'
        content_analysis['visual_concepts'] = ['slope_visualization', 'tangent_lines', 'rate_of_change']
        content_analysis['educational_focus'] = 'Show slope changes and tangent line meaning'
        
    elif re.search(r'limit|\\lim|approaches', latex_content):
        content_analysis['type'] = 'limit'
        content_analysis['visual_concepts'] = ['approaching_behavior', 'graph_analysis']
        content_analysis['educational_focus'] = 'Animate the approach to a limiting value'
        
    # Detect complexity
    complexity_indicators = len(re.findall(r'\\[a-zA-Z]+', latex_content))
    if complexity_indicators > 5:
        content_analysis['complexity'] = 'advanced'
    elif complexity_indicators > 2:
        content_analysis['complexity'] = 'intermediate'
        
    # Extract key mathematical operations
    operations = re.findall(r'[+\-*/=<>≤≥∫∑∏]|\\[a-zA-Z]+', latex_content)
    content_analysis['key_operations'] = operations[:5]  # Limit to top 5
    
    return content_analysis

def generate_video_async(task_id, latex_content, topic, quality="medium_quality"):
    """Generate video in background thread using Manim when available."""
    try:
        # Update task status using persistent storage
        update_task(task_id, {
            'status': 'generating',
            'message': 'Creating Manim scene...'
        })

        # Ensure output directory exists
        os.makedirs(video_output_dir, exist_ok=True)

        if not MANIM_AVAILABLE:
            raise Exception("Manim is not available on the server")

        # Try to generate AI-powered educational scene first
        ai_code = None
        if AI_AVAILABLE:
            try:
                update_task(task_id, {'message': 'Generating educational content with AI...'})
                ai_code_raw = generate_manim_code_with_ai(latex_content, topic)
                
                # Post-process the AI code to fix text overlap issues
                update_task(task_id, {'message': 'Optimizing animation structure...'})
                ai_code = fix_text_overlap_issues(ai_code_raw)
                
                # Fix Manim API compatibility issues
                ai_code = fix_manim_api_compatibility(ai_code)
                
                # Validate the final code
                validation_errors = validate_manim_code_structure(ai_code)
                if validation_errors:
                    print(f"⚠️ Code validation found issues: {validation_errors}")
                    # Apply additional fixes
                    ai_code = apply_emergency_fixes(ai_code)
                
                # Final syntax check using Python's AST
                try:
                    import ast
                    ast.parse(ai_code)
                    print(f"✅ Code passed syntax validation")
                except SyntaxError as e:
                    print(f"⚠️ Syntax error detected: {e}")
                    print(f"Applying emergency syntax fixes...")
                    ai_code = fix_severe_syntax_errors(ai_code)
                    try:
                        ast.parse(ai_code)
                        print(f"✅ Syntax errors resolved")
                    except SyntaxError as e2:
                        print(f"❌ Could not resolve syntax error: {e2}")
                        raise Exception(f"Unable to fix syntax error: {e2}")
                
                print(f"🔧 Applied text overlap fixes and validation to AI-generated code")
                
            except Exception as e:
                print(f"⚠️ AI generation failed, falling back to basic scene: {e}")

        # Create or compile the scene class  
        if ai_code:
            try:
                # Execute the AI-generated code to create the LaTeXScene class
                # Import all commonly used Manim classes and functions
                from manim import (
                    Scene, Text, MathTex, Write, Transform, ReplacementTransform, 
                    FadeIn, FadeOut, Create, DrawBorderThenFill,
                    UP, DOWN, LEFT, RIGHT, ORIGIN, PI, TAU,
                    BLUE, RED, GREEN, YELLOW, WHITE, BLACK, ORANGE, PURPLE, PINK,
                    NumberPlane, Axes, VGroup, Line, Rectangle, Circle, Dot,
                    Arrow, DoubleArrow, Vector, always_redraw
                )
                
                # Handle deprecated names for compatibility
                ShowCreation = Create  # ShowCreation was renamed to Create
                
                exec_globals = {
                    'Scene': Scene, 'Text': Text, 'MathTex': MathTex, 'Write': Write,
                    'Transform': Transform, 'ReplacementTransform': ReplacementTransform,
                    'FadeIn': FadeIn, 'FadeOut': FadeOut, 'Create': Create,
                    'ShowCreation': ShowCreation, 'DrawBorderThenFill': DrawBorderThenFill,
                    'UP': UP, 'DOWN': DOWN, 'LEFT': LEFT, 'RIGHT': RIGHT, 'ORIGIN': ORIGIN,
                    'PI': PI, 'TAU': TAU,
                    'BLUE': BLUE, 'RED': RED, 'GREEN': GREEN, 'YELLOW': YELLOW, 
                    'WHITE': WHITE, 'BLACK': BLACK, 'ORANGE': ORANGE, 'PURPLE': PURPLE, 'PINK': PINK,
                    'NumberPlane': NumberPlane, 'Axes': Axes, 'VGroup': VGroup,
                    'Line': Line, 'Rectangle': Rectangle, 'Circle': Circle, 'Dot': Dot,
                    'Arrow': Arrow, 'DoubleArrow': DoubleArrow, 'Vector': Vector,
                    'always_redraw': always_redraw
                }
                exec(ai_code, exec_globals)
                LaTeXScene = exec_globals['LaTeXScene']
                print("✅ Using AI-generated scene")
            except Exception as e:
                error_msg = f"AI scene compilation failed: {e}"
                print(f"❌ {error_msg}")
                print(f"Generated code preview: {ai_code[:300]}...")
                raise Exception(error_msg)
        else:
            error_msg = "AI code generation failed - no code generated"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

        # Map requested quality to manim setting
        quality_map = {
            'low_quality': 'low_quality',
            'medium_quality': 'medium_quality',
            'high_quality': 'high_quality',
        }
        manim_quality = quality_map.get(quality, 'medium_quality')

        # Render the scene with a temporary configuration
        try:
            from manim import tempconfig

            with tempconfig({
                "media_dir": video_output_dir,
                "video_dir": video_output_dir,
                "images_dir": video_output_dir,
                "quality": manim_quality,
                "format": "mp4",
            }):
                scene = LaTeXScene()
                scene.render()

                # Try to get the produced movie path from manim
                movie_path = None
                writer = getattr(scene, 'renderer', None)
                if writer and getattr(writer, 'file_writer', None):
                    movie_path = getattr(writer.file_writer, 'movie_file_path', None) or getattr(writer.file_writer, 'output_file_path', None)

                # Fallback: pick the most recent mp4 in the output dir
                if not movie_path or not os.path.exists(movie_path):
                    candidates = sorted(glob.glob(os.path.join(video_output_dir, "*.mp4")), key=os.path.getmtime, reverse=True)
                    movie_path = candidates[0] if candidates else None

                if not movie_path or not os.path.exists(movie_path):
                    raise Exception("Manim did not produce a video file")

                # Copy to our task-specific filename
                output_file = os.path.join(video_output_dir, f"{task_id}.mp4")
                shutil.copyfile(movie_path, output_file)

        except Exception as manim_error:
            raise Exception(f"Manim rendering error: {manim_error}")

        # Success
        update_task(task_id, {
            'status': 'completed',
            'message': 'Video generated successfully',
            'video_path': os.path.join(video_output_dir, f"{task_id}.mp4"),
            'video_url': f"/api/videos/{task_id}.mp4"
        })
        print(f"✅ Video generation completed for task {task_id}")

    except Exception as e:
        update_task(task_id, {
            'status': 'error',
            'message': f'Video generation failed: {str(e)}'
        })
        print(f"❌ Video generation failed for task {task_id}: {e}")

# Manim API endpoints
@app.route('/api/health', methods=['GET'])
def manim_health_check():
    """Overall health check endpoint"""
    # OCR is ready if either MixTeX model is loaded OR we're in demo mode
    ocr_ready = model_loaded or not MIXTEX_AVAILABLE
    
    return jsonify({
        'status': 'ready' if (ocr_ready and MANIM_AVAILABLE) else 'partial',
        'ocr_status': 'ready' if ocr_ready else 'error',
        'manim_status': 'ready' if MANIM_AVAILABLE else 'unavailable',
        'message': 'Backend services status',
        'demo_mode': not MIXTEX_AVAILABLE
    })

@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Generate Manim video from LaTeX content"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        topic = data.get('topic', 'Mathematical Expression')
        latex_content = topic  # The topic IS the LaTeX content from OCR
        quality = data.get('quality', 'medium_quality')
        
        if not latex_content:
            return jsonify({'success': False, 'message': 'No content provided'}), 400
        
        # Create unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task using persistent storage
        update_task(task_id, {
            'status': 'starting',
            'message': 'Initializing video generation...',
            'created_at': time.time()
        })

        # Start video generation in background
        thread = threading.Thread(
            target=generate_video_async,
            args=(task_id, latex_content, topic, quality)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Video generation started'
        })
        
    except Exception as e:
        logger.error(f"Error in generate_video: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def check_video_status(task_id):
    """Check video generation status"""
    task = get_task(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    response = {
        'success': True,
        'status': task['status'],
        'message': task['message']
    }
    
    if task['status'] == 'completed':
        response['video_url'] = task.get('video_url')
    
    return jsonify(response)

@app.route('/api/videos/<filename>', methods=['GET'])
def serve_video(filename):
    """Serve generated video files"""
    try:
        video_path = os.path.join(video_output_dir, filename)
        if os.path.exists(video_path):
            # Serve with correct mimetype for HTML5 video
            return send_file(video_path, as_attachment=False, mimetype='video/mp4')
        else:
            return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# OCR endpoints
@app.route('/api/ocr/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    if MIXTEX_AVAILABLE and model_loaded:
        return jsonify({
            'status': 'ready',
            'message': 'MixTeX OCR backend is running',
            'model_loaded': True
        })
    elif MIXTEX_AVAILABLE:
        return jsonify({
            'status': 'error',
            'message': model_error,
            'model_loaded': False
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'MixTeX modules not available',
            'model_loaded': False,
            'backend': 'MixTeX'
        })

@app.route('/api/ocr/status', methods=['GET'])
def status_check():
    """Status check endpoint"""
    if MIXTEX_AVAILABLE and model_loaded:
        return jsonify({
            'status': 'ready',
            'message': 'MixTeX model is ready',
            'model_loaded': True,
            'backend': 'MixTeX'
        })
    elif MIXTEX_AVAILABLE:
        return jsonify({
            'status': 'error',
            'message': model_error,
            'model_loaded': False,
            'backend': 'MixTeX'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'MixTeX modules not available',
            'model_loaded': False,
            'backend': 'MixTeX'
        })

@app.route('/api/ocr/extract', methods=['POST'])
def extract_content():
    """
    Extract mathematical content from image data
    Expected JSON payload:
    {
        "image_data": "data:image/png;base64,iVBOR...",
        "preprocessing_level": "moderate"  // optional: minimal, moderate, aggressive
    }
    """
    try:
        # Check if model is loaded
        if not model_loaded:
            return jsonify({
                'success': False,
                'message': f'Model not loaded: {model_error}',
                'formulas': [],
                'text_content': [],
                'raw_result': ''
            }), 500
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No JSON data provided',
                'formulas': [],
                'text_content': [],
                'raw_result': ''
            }), 400
        
        # Extract image data
        image_data = data.get('image_data')
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image_data provided',
                'formulas': [],
                'text_content': [],
                'raw_result': ''
            }), 400
        
        preprocessing_level = data.get('preprocessing_level', 'moderate')
        
        logger.info(f"Processing OCR request with preprocessing level: {preprocessing_level}")
        
        # Decode base64 image
        try:
            if image_data.startswith('data:image/'):
                # Remove data URL prefix
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            logger.info(f"Image decoded successfully: {image.size} {image.mode}")
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Failed to decode image: {str(e)}',
                'formulas': [],
                'text_content': [],
                'raw_result': ''
            }), 400
        
        # Extract LaTeX using MixTeX
        try:
            latex_result = extract_latex_from_image(image, preprocessing_level)
            
            logger.info(f"LaTeX extraction successful: {len(latex_result)} characters")
            
            # Format the response - MixTeX typically returns mathematical formulas
            if latex_result:
                # Check if it contains mathematical content
                is_formula = any(char in latex_result for char in ['\\', '{', '}', '^', '_', '$'])
                
                if is_formula:
                    formulas = [latex_result]
                    text_content = []
                else:
                    formulas = []
                    text_content = [latex_result]
                
                return jsonify({
                    'success': True,
                    'message': 'Content extracted successfully',
                    'formulas': formulas,
                    'text_content': text_content,
                    'raw_result': latex_result,
                    'preprocessing_level': preprocessing_level
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No content detected in the image',
                    'formulas': [],
                    'text_content': [],
                    'raw_result': '',
                    'preprocessing_level': preprocessing_level
                })
                
        except Exception as e:
            logger.error(f"LaTeX extraction failed: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'OCR processing failed: {str(e)}',
                'formulas': [],
                'text_content': [],
                'raw_result': '',
                'preprocessing_level': preprocessing_level
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in extract_content: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'formulas': [],
            'text_content': [],
            'raw_result': ''
        }), 500

@app.route('/api/ocr/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify the API is working"""
    return jsonify({
        'message': 'MixTeX OCR backend is working!',
        'model_loaded': model_loaded,
        'endpoints': {
            'health': '/api/ocr/health',
            'status': '/api/ocr/status', 
            'extract': '/api/ocr/extract (POST)',
            'test': '/api/ocr/test'
        }
    })

if __name__ == '__main__':
    print("🚀 Starting MixTeX OCR Backend Server...")
    
    # Initialize the model
    if initialize_model():
        print("✅ Model initialization successful!")
    else:
        print("❌ Model initialization failed - server will run but OCR will not work")
    
    # Start the Flask server
    print("🌐 Starting Unified Backend Server on http://localhost:5000")
    print("📋 Available OCR endpoints:")
    print("   GET  /api/ocr/health   - OCR Health check")
    print("   GET  /api/ocr/status   - OCR Status check")
    print("   POST /api/ocr/extract  - Extract LaTeX from image")
    print("   GET  /api/ocr/test     - Test endpoint")
    print("📋 Available Manim endpoints:")
    print("   GET  /api/health       - Overall health check")
    print("   POST /api/generate     - Generate Manim video")
    print("   GET  /api/status/<id>  - Check video generation status")
    print("   GET  /api/videos/<id>  - Serve video files")
    
    # Disable debug mode to prevent auto-reloading during video generation
    # Debug mode causes restarts when Manim modifies temporary files
    app.run(host='0.0.0.0', port=5000, debug=False)