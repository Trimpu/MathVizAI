"""
Core video generation logic for the Manim integration project.
"""
import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import Config, VIDEO_CONFIG
from services.manim_service import manim_service
from services.ai_service import ai_service
from services.sympy_service import sympy_service
from utils.math_utils import extract_math_expressions, analyze_math_content

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Core class for generating mathematical videos using Manim"""

    def __init__(self):
        self.config = Config()
        self.manim_service = manim_service
        self.ai_service = ai_service
        self.sympy_service = sympy_service

    def generate_video_from_text(self, text: str, quality: str = "medium") -> Dict[str, Any]:
        """
        Generate a video from text containing mathematical content.

        Args:
            text: Input text with mathematical expressions
            quality: Video quality ('low', 'medium', 'high')

        Returns:
            Dictionary containing generation results
        """
        try:
            # Analyze the mathematical content
            math_analysis = analyze_math_content(text)
            logger.info(f"Math analysis: {math_analysis}")

            if not math_analysis['has_math']:
                return {
                    'success': False,
                    'error': 'No mathematical expressions found in the text',
                    'analysis': math_analysis
                }

            # Extract mathematical expressions
            expressions = math_analysis['expressions']

            # Generate Manim code using AI
            manim_code = self.ai_service.generate_manim_code(text, expressions)

            if not manim_code:
                return {
                    'success': False,
                    'error': 'Failed to generate Manim code',
                    'analysis': math_analysis
                }

            # Execute the AI-generated code to create the scene class
            try:
                # Import all commonly used Manim classes and functions
                from manim import (
                    Scene, Text, MathTex, Write, Transform, ReplacementTransform, 
                    FadeIn, FadeOut, Create, DrawBorderThenFill,
                    UP, DOWN, LEFT, RIGHT, ORIGIN, PI, TAU,
                    BLUE, RED, GREEN, YELLOW, WHITE, BLACK, ORANGE, PURPLE, PINK,
                    NumberPlane, Axes, VGroup, Line, Rectangle, Circle, Dot,
                    Arrow, DoubleArrow, Vector, always_redraw,
                    ThreeDScene, Surface, ThreeDAxes, Sphere, Cube, Camera
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
                    'always_redraw': always_redraw,
                    'ThreeDScene': ThreeDScene, 'Surface': Surface, 'ThreeDAxes': ThreeDAxes,
                    'Sphere': Sphere, 'Cube': Cube, 'Camera': Camera
                }
                exec(manim_code, exec_globals)
                LaTeXScene = exec_globals['LaTeXScene']
                print("✅ Using AI-generated scene")
            except Exception as e:
                error_msg = f"AI scene compilation failed: {e}"
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'analysis': math_analysis,
                    'manim_code': manim_code
                }

            # Create unique scene name
            scene_name = f"MathScene_{uuid.uuid4().hex[:8]}"

            # Render the video
            video_path = self.manim_service.render_scene(
                scene_class=LaTeXScene,
                quality=quality
            )

            if not video_path:
                return {
                    'success': False,
                    'error': 'Video rendering failed',
                    'analysis': math_analysis,
                    'manim_code': manim_code
                }

            return {
                'success': True,
                'video_path': video_path,
                'scene_name': scene_name,
                'analysis': math_analysis,
                'manim_code': manim_code,
                'quality': quality
            }

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {
                'success': False,
                'error': f"Unexpected error during video generation: {str(e)}"
            }

    def generate_video_from_latex(self, latex_content: str, quality: str = "medium") -> Dict[str, Any]:
        """
        Generate a video directly from LaTeX content.

        Args:
            latex_content: LaTeX mathematical expression
            quality: Video quality ('low', 'medium', 'high')

        Returns:
            Dictionary containing generation results
        """
        try:
            # Preprocess LaTeX with SymPy if available
            processed_latex = self.sympy_service.preprocess_latex(latex_content)

            # Create a simple text description for AI generation
            text_description = f"Create an animation for the mathematical expression: {processed_latex}"

            # Generate Manim code
            manim_code = self.ai_service.generate_manim_code(text_description, processed_latex)

            if not manim_code:
                return {
                    'success': False,
                    'error': 'Failed to generate Manim code from LaTeX'
                }

            # Save the generated code for debugging
            debug_file = Path(__file__).parent.parent / 'videos' / 'last_generated_scene.py'
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(manim_code)
                logger.info(f"💾 Saved generated code to: {debug_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not save debug file: {e}")
            
            # Check if the generated code contains self.play() calls BEFORE compilation
            has_animations = 'self.play(' in manim_code
            logger.info(f"🔍 Code contains self.play() calls: {has_animations}")
            logger.info(f"📊 Code length: {len(manim_code)} chars, Lines: {manim_code.count(chr(10))}")
            
            if not has_animations:
                logger.warning("⚠️ Generated code has no self.play() calls - adding default animation")
                # Inject a simple animation into the construct method
                import re
                # Find the construct method and add a basic animation at the beginning
                pattern = r'(def construct\(self\):)(.*?)(\n    def|\n\nclass|\Z)'
                
                def add_animation(match):
                    method_def = match.group(1)
                    method_body = match.group(2)
                    next_part = match.group(3)
                    
                    # Add a simple title animation at the very start
                    animation_code = '''
        # AUTO-INJECTED: Ensure video output
        title = Text("Mathematical Visualization", font_size=48)
        self.play(Write(title), run_time=1)
        self.wait(0.5)
        self.play(FadeOut(title), run_time=0.5)
        self.wait(0.3)
'''
                    return method_def + animation_code + method_body + next_part
                
                manim_code = re.sub(pattern, add_animation, manim_code, flags=re.DOTALL)
                logger.info("✅ Injected animation successfully")

            # Execute the AI-generated code to create the scene class
            try:
                # Import all commonly used Manim classes and functions
                from manim import (
                    Scene, Text, MathTex, Write, Transform, ReplacementTransform, 
                    FadeIn, FadeOut, Create, DrawBorderThenFill,
                    UP, DOWN, LEFT, RIGHT, ORIGIN, PI, TAU,
                    BLUE, RED, GREEN, YELLOW, WHITE, BLACK, ORANGE, PURPLE, PINK,
                    NumberPlane, Axes, VGroup, Line, Rectangle, Circle, Dot,
                    Arrow, DoubleArrow, Vector, always_redraw,
                    ThreeDScene, Surface, ThreeDAxes, Sphere, Cube, Camera
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
                    'always_redraw': always_redraw,
                    'ThreeDScene': ThreeDScene, 'Surface': Surface, 'ThreeDAxes': ThreeDAxes,
                    'Sphere': Sphere, 'Cube': Cube, 'Camera': Camera
                }
                # Add 3D objects that might be missing
                try:
                    from manim import Cylinder, Cone
                    exec_globals['Cylinder'] = Cylinder
                    exec_globals['Cone'] = Cone
                except ImportError:
                    pass
                
                exec(manim_code, exec_globals)
                
                # Find Scene classes that were DEFINED in the executed code (not imported from manim)
                # Classes from manim package have __module__ starting with 'manim'
                LaTeXScene = None
                for name, obj in exec_globals.items():
                    if isinstance(obj, type) and issubclass(obj, Scene):
                        module_name = getattr(obj, '__module__', '')
                        # Exclude classes from the manim package
                        if not module_name.startswith('manim'):
                            LaTeXScene = obj
                            logger.info(f"✅ Found scene class: {name}")
                            break
                
                if not LaTeXScene:
                    # Fallback: try common names
                    for class_name in ['LaTeXScene', 'MathScene', 'MyScene', 'MainScene']:
                        if class_name in exec_globals:
                            LaTeXScene = exec_globals[class_name]
                            logger.info(f"✅ Using scene class: {class_name}")
                            break
                
                if not LaTeXScene:
                    raise ValueError("No Scene class found in AI-generated code")
                
                # Wrap the construct method to catch errors
                original_construct = LaTeXScene.construct
                def wrapped_construct(self):
                    try:
                        logger.info(f"🎭 Executing construct() method...")
                        original_construct(self)
                        logger.info(f"✅ construct() completed successfully")
                    except Exception as construct_error:
                        logger.error(f"❌ Error in construct(): {construct_error}", exc_info=True)
                        raise
                
                LaTeXScene.construct = wrapped_construct
                    
                print("✅ Using AI-generated scene")
            except Exception as e:
                error_msg = f"AI scene compilation failed: {e}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"📝 Generated code:\n{manim_code}")
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'manim_code': manim_code
                }

            # Create unique scene name
            scene_name = f"LaTeXScene_{uuid.uuid4().hex[:8]}"

            # Render the video
            logger.info(f"🎬 Starting video render with quality={quality}")
            video_path = self.manim_service.render_scene(
                scene_class=LaTeXScene,
                quality=quality
            )
            logger.info(f"📹 Render complete. Video path: {video_path}")

            if not video_path:
                return {
                    'success': False,
                    'error': 'Video rendering failed',
                    'manim_code': manim_code
                }

            return {
                'success': True,
                'video_path': video_path,
                'scene_name': scene_name,
                'latex_content': processed_latex,
                'manim_code': manim_code,
                'quality': quality
            }

        except Exception as e:
            logger.error(f"LaTeX video generation failed: {e}")
            return {
                'success': False,
                'error': f"Unexpected error during LaTeX video generation: {str(e)}"
            }

    def get_video_status(self, scene_name: str) -> Dict[str, Any]:
        """
        Get the status of a video generation task.

        Args:
            scene_name: Name of the scene

        Returns:
            Dictionary containing status information
        """
        try:
            videos_dir = Path(VIDEO_CONFIG['output_dir'])
            video_path = videos_dir / f"{scene_name}.mp4"

            if video_path.exists():
                file_size = video_path.stat().st_size
                return {
                    'status': 'completed',
                    'video_path': str(video_path),
                    'file_size': file_size,
                    'exists': True
                }
            else:
                # Check for partial files
                partial_dir = videos_dir / "partial_movie_files" / scene_name
                if partial_dir.exists():
                    partial_files = list(partial_dir.glob("*.mp4"))
                    return {
                        'status': 'processing',
                        'partial_files': len(partial_files),
                        'exists': False
                    }

                return {
                    'status': 'not_found',
                    'exists': False
                }

        except Exception as e:
            logger.error(f"Error checking video status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'exists': False
            }

    def cleanup_old_videos(self, max_age_days: int = 7) -> Dict[str, Any]:
        """
        Clean up old video files.

        Args:
            max_age_days: Maximum age of videos to keep

        Returns:
            Dictionary containing cleanup results
        """
        try:
            import time
            from datetime import datetime, timedelta

            videos_dir = Path(VIDEO_CONFIG['output_dir'])
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

            cleaned_files = []
            total_size_cleaned = 0

            for video_file in videos_dir.glob("*.mp4"):
                if video_file.stat().st_mtime < cutoff_time:
                    file_size = video_file.stat().st_size
                    video_file.unlink()
                    cleaned_files.append(str(video_file))
                    total_size_cleaned += file_size

            # Also clean up partial movie files
            partial_dir = videos_dir / "partial_movie_files"
            if partial_dir.exists():
                for scene_dir in partial_dir.iterdir():
                    if scene_dir.is_dir() and scene_dir.stat().st_mtime < cutoff_time:
                        # Remove the entire scene directory
                        import shutil
                        shutil.rmtree(scene_dir)
                        cleaned_files.append(str(scene_dir))

            return {
                'success': True,
                'cleaned_files': len(cleaned_files),
                'total_size_cleaned': total_size_cleaned,
                'files': cleaned_files[:10]  # Limit to first 10 for brevity
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global video generator instance
video_generator = VideoGenerator()