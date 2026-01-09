"""
OCR service using MixTeX for mathematical content extraction.
"""
import os
import logging
from pathlib import Path
from PIL import Image
import traceback

logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR functionality using MixTeX"""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_error = None
        self.mixtex_available = False

        # Try to import MixTeX
        try:
            # Add mixtex path to system path
            import sys
            backend_dir = Path(__file__).parent.parent
            mixtex_path = backend_dir.parent.parent / "mixtexgui"
            if mixtex_path.exists():
                sys.path.append(str(mixtex_path))
                sys.path.append(str(mixtex_path / "examples"))

            from mixtex_core import load_model, pad_image, stream_inference, convert_align_to_equations
            self.load_model = load_model
            self.pad_image = pad_image
            self.stream_inference = stream_inference
            self.convert_align_to_equations = convert_align_to_equations
            self.mixtex_available = True
            print("✅ Successfully imported MixTeX core modules")
        except ImportError as e:
            print(f"⚠️ MixTeX modules not available: {e}")
            self.mixtex_available = False

    def initialize_model(self):
        """Initialize the MixTeX model"""
        if not self.mixtex_available:
            self.model_loaded = False
            self.model_error = "MixTeX modules not available"
            return False

        try:
            print("🔄 Initializing MixTeX model...")

            # Try to find the onnx model directory
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "mixtexgui" / "onnx",
                Path(__file__).parent.parent / "onnx",
                Path(__file__).parent / "onnx",
            ]

            onnx_path = None
            for path in possible_paths:
                if path.exists():
                    onnx_path = path
                    break

            if not onnx_path:
                raise FileNotFoundError(f"Could not find onnx model directory in any of: {possible_paths}")

            print(f"📁 Using model path: {onnx_path}")

            # Load the model
            self.model = self.load_model(str(onnx_path))
            self.model_loaded = True
            self.model_error = None

            print("✅ MixTeX model loaded successfully!")
            return True

        except Exception as e:
            error_msg = f"Failed to load MixTeX model: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"📄 Traceback: {traceback.format_exc()}")
            self.model_loaded = False
            self.model_error = error_msg
            return False

    def preprocess_image(self, image, preprocessing_level='moderate'):
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

    def extract_latex_from_image(self, image, preprocessing_level='moderate'):
        """
        Extract LaTeX content from image using MixTeX model
        """
        if not self.model_loaded or self.model is None:
            raise Exception("MixTeX model is not loaded")

        try:
            logger.info(f"🔍 Starting LaTeX extraction from image: {image.size} {image.mode}")
            
            # Preprocess the image
            processed_image = self.preprocess_image(image, preprocessing_level)
            logger.info(f"✅ Preprocessed image: {processed_image.size} {processed_image.mode}")

            # Pad image to required dimensions (448x448 for MixTeX)
            padded_image = self.pad_image(processed_image, (448, 448))
            logger.info(f"✅ Padded image to: {padded_image.size if hasattr(padded_image, 'size') else 'tensor'}")

            # Extract LaTeX using MixTeX streaming inference
            logger.info("🔄 Starting MixTeX streaming inference...")
            latex_parts = []
            for piece in self.stream_inference(padded_image, self.model):
                latex_parts.append(piece)
                logger.debug(f"📝 Received piece: {piece}")

            # Join all parts to get complete LaTeX
            full_latex = ''.join(latex_parts)
            logger.info(f"✅ Raw LaTeX extraction complete: {len(full_latex)} characters")
            logger.info(f"📄 Raw LaTeX: {full_latex[:200] if full_latex else '(empty)'}...")

            # Clean up the output
            full_latex = full_latex.strip()

            # Replace common formatting
            full_latex = full_latex.replace('\\[', '\\begin{align*}').replace('\\]', '\\end{align*}')
            full_latex = full_latex.replace('%', '\\%')
            
            logger.info(f"✅ Final LaTeX after cleanup: {full_latex[:200] if full_latex else '(empty)'}...")

            return full_latex

        except Exception as e:
            logger.error(f"Error in LaTeX extraction: {e}", exc_info=True)
            raise

    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return self.mixtex_available and self.model_loaded

# Global OCR service instance
ocr_service = OCRService()