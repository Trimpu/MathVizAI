"""
AI service for generating Manim code using OpenAI/Github models.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI-powered content generation"""

    def __init__(self):
        self.client = None
        self.available = False
        self.cache = {}
        self.cache_file = None

        # Try to initialize AI client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the AI client"""
        try:
            from openai import OpenAI
            from dotenv import load_dotenv
            load_dotenv()

            token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENAI_API_KEY")
            if token:
                if os.environ.get("GITHUB_TOKEN"):
                    self.client = OpenAI(
                        base_url="https://models.github.ai/inference",
                        api_key=token,
                    )
                    self.model = "gpt-5"
                else:
                    self.client = OpenAI(api_key=token)
                    self.model = "gpt-5"

                self.available = True
                print(f"✅ AI integration available")
            else:
                self.available = False
                print(f"⚠️ AI integration not configured")
        except ImportError as e:
            print(f"⚠️ AI integration not available: {e}")
            self.available = False

    def load_cache(self, cache_file: Path):
        """Load AI code cache from file"""
        self.cache_file = cache_file
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}

    def save_cache(self):
        """Save AI code cache to file"""
        if self.cache_file:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
            except:
                pass

    def generate_manim_code(self, latex_content: str, topic: str = "Mathematical Expression",
                          style: str = "default", animation_speed: str = "normal",
                          color_scheme: str = "blue_red") -> Optional[str]:
        """
        Generate educational Manim code using AI for the given LaTeX content.
        """
        if not self.available or not self.client:
            return None

        # Create cache key
        cache_key = f"{latex_content}_{style}_{animation_speed}_{color_scheme}"

        # Check cache first
        if cache_key in self.cache:
            print(f"📋 Using cached AI code for: {cache_key[:50]}...")
            return self.cache[cache_key]

        try:
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

3D VISUALIZATION SUPPORT:
- CRITICAL: If using 3D objects (Cylinder, Sphere, Cone, Cube, Surface), you MUST use ThreeDScene as the base class, NOT Scene
- For 3D concepts: Use "class LaTeXScene(ThreeDScene):" instead of "class LaTeXScene(Scene):"
- Include camera rotations, zooms, and perspective changes to show depth
- Use Surface, ParametricSurface, or VectorField3D for appropriate visualizations
- Add ThreeDAxes in 3D scenes when relevant
- AVOID 3D objects unless the problem explicitly requires 3D visualization - use 2D shapes instead when possible

MULTI-SCENE NARRATIVES:
- For complex topics, create multiple connected scenes (Scene1, Scene2, etc.) that build sequentially.
- Use scene transitions to maintain narrative flow.
- Each scene should focus on one key concept, with clear progression.

INTERACTIVE ELEMENTS:
- Where possible, use InteractiveScene for clickable elements or parameter exploration.
- Add sliders or controls for dynamic visualization (e.g., changing function parameters).
- Export as HTML for web interactivity when requested.

TECHNICAL REQUIREMENTS:
1. Define class LaTeXScene(Scene) with construct(self). For 3D: LaTeXScene(ThreeDScene). For multi-scene: multiple classes.
2. Use try/except for MathTex fallback to Text when necessary.
3. Maintain a caption panel: a Python list or VGroup of Text/MathTex lines.
   - When adding a new line:
       new_line.next_to(previous_line, DOWN, aligned_edge=LEFT, buff=0.25)
   - First line: anchor with .to_edge(DOWN) or .to_corner(DL).
4. Do not remove previous caption lines; they remain as historical context unless performing a full phase reset.
5. Avoid clutter: keep total caption lines reasonable (e.g. ≤ 8–10).
6. Use color coding sparingly (e.g. important symbol or final result).
7. Use explicit positions for major math objects (axes at center, function above region, etc.). Keep 3D objects positioned for optimal viewing.
8. Keep code self-contained (no external assets).
9. For function y = x^2 integrals: definitely show axes, curve, shaded region, coarse rectangles, refinement, then emergence of ∫ and final numeric value.

ERROR RESILIENCE:
- Wrap suspicious LaTeX in try/except; fallback gracefully.

DO NOT:
- Produce giant blocks of explanatory text.
- Overwrite previous captions by default.
- Leave overlapping text objects.
- Use TransformMatchingTex (stick to Transform / ReplacementTransform).

Return ONLY the Python code for the LaTeXScene class with correct modern API."""

            # Import analysis function
            from utils.math_utils import analyze_math_content

            analysis = analyze_math_content(latex_content)

            user_prompt = f"""Create a VISUAL-FIRST Manim animation.

RAW CONTENT: {latex_content}

ANALYSIS:
- Type: {analysis['type']}
- Complexity: {analysis['complexity']}
- Visual Concepts: {', '.join(analysis['visual_concepts'])}
- Educational Focus: {analysis['educational_focus']}

CUSTOMIZATION SETTINGS:
- Style: {style} (default=dark background, colorful=bright colors, minimal=clean/simple)
- Animation Speed: {animation_speed} (slow=longer pauses, normal=standard, fast=quick transitions)
- Color Scheme: {color_scheme} (blue_red=BLUE/RED, green_purple=GREEN/PURPLE, etc.)

SCENE OBJECTIVE:
Let the viewer SEE the underlying mathematical process unfold before the symbolic form is finalized.

REQUIRED VISUAL FLOW (ADAPT if appropriate):
1. Axes / coordinate frame (only if relevant to the content). For 3D: use ThreeDAxes.
2. Function curve (if an integral or function). For 3D: use parametric curves or surfaces.
3. Domain / interval highlight (if bounds exist).
4. Shaded region (if area/accumulation). For 3D: use surface patches.
5. Approximation objects (rectangles / slices for integrals; discrete bars for sums; tangent lines for derivatives; approach markers for limits). For 3D: use 3D primitives.
6. Refinement or evolution (e.g., more rectangles). For 3D: animate parameter changes.
7. Emergence of symbolic form (Σ → ∫, derivative notation, etc.).
8. Final evaluation or simplified symbolic expression.
9. Concluding highlight of final result.

3D VISUALIZATION REQUIREMENTS (if applicable):
- Use ThreeDScene for camera control and 3D objects.
- Include camera.begin_ambient_camera_rotation() for dynamic viewing.
- Position 3D objects for optimal perspective (e.g., surfaces slightly tilted).
- Use Surface or ParametricSurface for functions of two variables.

MULTI-SCENE REQUIREMENTS (for complex topics):
- Create multiple scene classes (LaTeXScene1, LaTeXScene2, etc.) if the concept needs sequential development.
- Each scene should build on the previous, maintaining visual continuity.
- Use self.wait() between major transitions within a scene.

CAPTION PANEL:
- Maintain a list of short lines; each new conceptual milestone adds one line.
- Example line sequence (for integral): ['Curve y = x^2', 'Target area 0→2', 'Coarse rectangles', 'Refinement', 'Integral emerges', 'Exact area 8/3']
- Each line appended below the previous using next_to.

CODING PATTERN FOR CAPTIONS (MANDATORY STYLE):
caption_lines = []
line1 = Text("Curve y = x^2", font_size=24)
line1.to_edge(DOWN).to_corner(DL)
self.play(Write(line1))
self.wait(0.5)
caption_lines.append(line1)

line2 = Text("Target area 0→2", font_size=24)
line2.next_to(caption_lines[-1], DOWN, aligned_edge=LEFT, buff=0.25)
self.play(FadeIn(line2))
self.wait(0.5)
caption_lines.append(line2)

If too many lines accumulate for your case, you may (optionally) fade out earlier ones as a batch before continuing, but only if necessary for readability.

MINIMUM REQUIRED STRUCTURE (every scene MUST include):
def construct(self):
    # Step 1: Title/introduction - REQUIRED
    title = Text("Your Title Here", font_size=42)
    self.play(Write(title))
    self.wait(1)
    
    # Step 2: Main content - REQUIRED
    content = MathTex(r"Your LaTeX Here")
    self.play(FadeIn(content))
    self.wait(2)
    
    # Step 3: Additional visuals/explanation - OPTIONAL
    # ... more animations ...
    
    # Step 4: Conclusion - RECOMMENDED
    self.play(FadeOut(title), FadeOut(content))
    self.wait(1)

INTEGRAL-SPECIFIC SUGGESTIONS (if integral detected):
- Use axes = Axes(x_range=[-0.5, 3], y_range=[-0.5, 5]) (adjust if needed)
- Plot function via axes.plot(lambda x: x**2)
- Region: axes.get_area(graph, x_range=[0,2], color=BLUE, opacity=0.4)
- Rectangles: manually build with for-loop or use Riemann rectangle logic
- Refine via Transform old group → new group (NOT ReplacementTransform)
- Introduce integral symbol near upper-right or above region
- Evaluate: final MathTex with result (e.g. r"\\int_0^2 x^2 \\, dx = \\frac{8}{3}")

3D INTEGRAL SUGGESTIONS (if 3D integral detected):
- Use ThreeDAxes() for coordinate system
- Create surface via Surface(lambda u,v: [u,v,u**2+v**2], u_range=[-1,1], v_range=[-1,1])
- Show volume via opacity or wireframe
- Animate camera around the volume

CRITICAL API REQUIREMENTS (Manim v0.17+):
- Use 'color=' not 'colors=' in get_riemann_rectangles()
- Use 'Create()' not 'ShowCreation()'
- Use 'Transform()' for changing objects - NEVER use 'ReplacementTransform()'
- Use 'FadeIn()' and 'FadeOut()' for object transitions
- Parameter names: 'color', 'fill_color', 'stroke_color' (singular forms)
- For 3D objects (Cylinder, Sphere, Cone): MUST use ThreeDScene as base class
- PREFER 2D visualizations (Rectangle, Circle, Polygon) over 3D objects when possible

MANDATORY ANIMATION REQUIREMENT:
- MUST call self.play() at least 3-5 times with animations (Write, Create, FadeIn, Transform, etc.)
- MUST include self.wait(1) between major animation steps for proper timing
- DO NOT create objects without animating them - every visual element must have an animation
- Example minimal scene:
  title = Text("Example", font_size=48)
  self.play(Write(title))
  self.wait(1)
  equation = MathTex(r"f(x) = x^2")
  self.play(FadeIn(equation))
  self.wait(2)

CRITICAL FORMATTING RULES:
- Each statement must be on ONE complete line - do NOT split assignments or function calls across multiple lines
- Comments must be on their own line BEFORE the code, never mixed with code
- Example CORRECT:
  # Step 1: Create function
  func_text = MathTex("f(x) = x^2", font_size=36)
- Example WRONG:
  # Step 1: Create function, func_text = MathTex(...)
- Keep function calls complete: obj = Constructor(arg1, arg2, kwarg=value)
- Balance all parentheses on the same line where they open
- ALWAYS animate object creation with self.play() - never just create objects without showing them

IF TYPE is not integral, adapt analogous conceptual decomposition.

Return ONLY the Python code for the LaTeXScene class with correct modern API."""

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                temperature=0.6,
                max_tokens=2500
            )

            if not response.choices or not response.choices[0].message.content:
                return None

            generated_code = response.choices[0].message.content.strip()

            # Strip accidental fenced code blocks if present
            import re
            generated_code = re.sub(r'```(?:python)?\s*', '', generated_code)
            generated_code = generated_code.replace('```', '').strip()

            print(f"🤖 AI generated Manim code ({len(generated_code)} chars)")

            # Cache the result
            self.cache[cache_key] = generated_code
            self.save_cache()

            return generated_code

        except Exception as e:
            print(f"❌ AI code generation failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if AI service is available"""
        return self.client is not None

# Global AI service instance
ai_service = AIService()