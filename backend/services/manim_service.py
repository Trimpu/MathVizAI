"""
Manim service for video generation and rendering.
"""
import os
import shutil
import glob
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ManimService:
    """Service for Manim video generation"""

    def __init__(self):
        self.manim_available = False
        self.output_dir = None

        # Try to import Manim
        try:
            import manim
            self.manim_available = True
            print("✅ Successfully imported Manim")
        except ImportError as e:
            print(f"⚠️ Manim not available: {e}")
            self.manim_available = False

    def set_output_dir(self, output_dir: Path):
        """Set the output directory for videos"""
        self.output_dir = output_dir
        output_dir.mkdir(exist_ok=True)

    def render_scene(self, scene_class, quality: str = "medium_quality") -> Optional[str]:
        """
        Render a Manim scene to video file

        Args:
            scene_class: The Manim scene class to render
            quality: Quality setting for rendering

        Returns:
            Path to the rendered video file, or None if failed
        """
        if not self.manim_available or not self.output_dir:
            return None

        try:
            from manim import tempconfig
            
            # Map quality values to Manim format
            quality_map = {
                'low': 'low_quality',
                'medium': 'medium_quality',
                'high': 'high_quality',
                'low_quality': 'low_quality',
                'medium_quality': 'medium_quality',
                'high_quality': 'high_quality'
            }
            manim_quality = quality_map.get(quality, 'medium_quality')
            
            logger.info(f"🎥 Rendering scene with quality={quality} (manim: {manim_quality})")
            logger.info(f"📁 Output directory: {self.output_dir}")

            with tempconfig({
                "media_dir": str(self.output_dir),
                "video_dir": str(self.output_dir),
                "images_dir": str(self.output_dir),
                "quality": manim_quality,
                "format": "mp4",
            }):
                logger.info(f"🎬 Creating scene instance...")
                scene = scene_class()
                scene_name = scene_class.__name__
                logger.info(f"▶️ Starting render for {scene_name}...")
                
                # Record time before rendering
                import time
                render_start_time = time.time()
                
                try:
                    scene.render()
                    logger.info(f"✅ Render complete")
                except Exception as render_error:
                    logger.error(f"❌ Error during scene.render(): {render_error}", exc_info=True)
                    return None

                # Look for the video file with the scene's name
                expected_video = self.output_dir / f"{scene_name}.mp4"
                logger.info(f"🔍 Looking for expected video: {expected_video}")
                
                if expected_video.exists():
                    logger.info(f"✅ Found expected video file")
                    return str(expected_video)
                
                # Fallback: Find the most recently created mp4 (created after render started)
                logger.info(f"⚠️ Expected video not found, searching for recent files...")
                candidates = [
                    p for p in self.output_dir.glob("*.mp4") 
                    if p.stat().st_mtime > render_start_time
                ]
                
                if candidates:
                    most_recent = max(candidates, key=lambda x: x.stat().st_mtime)
                    logger.info(f"✅ Using most recently created video: {most_recent}")
                    return str(most_recent)
                
                # Last resort: Check if a PNG was created (static scene with no animations)
                logger.info(f"⚠️ No video found, checking for PNG (static scene)...")
                png_candidates = [
                    p for p in self.output_dir.glob(f"{scene_name}*.png")
                    if p.stat().st_mtime > render_start_time
                ]
                
                if png_candidates:
                    png_file = png_candidates[0]
                    logger.warning(f"⚠️ Scene rendered as static image (no animations): {png_file}")
                    logger.error(f"❌ Scene must include self.play() calls to generate video")
                    return None
                else:
                    logger.error(f"❌ No video or image files created during render")
                    return None

        except Exception as e:
            logger.error(f"❌ Manim rendering error: {e}", exc_info=True)
            return None

    def get_quality_options(self) -> list:
        """Get available quality options"""
        return ["low_quality", "medium_quality", "high_quality"]

    def is_available(self) -> bool:
        """Check if Manim service is available"""
        return self.manim_available

# Global Manim service instance
manim_service = ManimService()