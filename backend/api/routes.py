"""
API routes for the Manim integration application.
"""
import os
import logging
from flask import Blueprint, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

from config import Config
from core.video_generator import video_generator
from services.ocr_service import ocr_service
from services.ai_service import ai_service
from utils.math_utils import extract_math_expressions, analyze_math_content

logger = logging.getLogger(__name__)

# Create blueprint for API routes
api_bp = Blueprint('api', __name__)

# Initialize config
config = Config()

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'manim': video_generator.manim_service.is_available(),
            'ocr': ocr_service.is_available(),
            'ai': ai_service.is_available(),
            'sympy': video_generator.sympy_service.is_available()
        }
    })

@api_bp.route('/generate-video', methods=['POST'])
def generate_video():
    """Generate video from text input"""
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400

        text = data['text']
        quality = data.get('quality', 'medium')

        if quality not in ['low', 'medium', 'high']:
            return jsonify({'error': 'Invalid quality parameter'}), 400

        result = video_generator.generate_video_from_text(text, quality)

        if result['success']:
            return jsonify({
                'success': True,
                'video_path': result['video_path'],
                'scene_name': result['scene_name'],
                'analysis': result['analysis']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'analysis': result.get('analysis')
            }), 500

    except Exception as e:
        logger.error(f"Error in generate_video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/generate-from-latex', methods=['POST'])
def generate_from_latex():
    """Generate video from LaTeX input"""
    try:
        data = request.get_json()

        if not data or 'latex' not in data:
            return jsonify({'error': 'Missing latex parameter'}), 400

        latex_content = data['latex']
        quality = data.get('quality', 'medium')

        if quality not in ['low', 'medium', 'high']:
            return jsonify({'error': 'Invalid quality parameter'}), 400

        logger.info(f"🎬 Generating video from LaTeX: {latex_content[:100]}...")
        result = video_generator.generate_video_from_latex(latex_content, quality)
        logger.info(f"📊 Generation result: success={result.get('success')}")

        if result['success']:
            return jsonify({
                'success': True,
                'video_path': result['video_path'],
                'scene_name': result['scene_name']
            })
        else:
            logger.error(f"❌ Video generation failed: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

    except Exception as e:
        logger.error(f"❌ Error in generate_from_latex: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@api_bp.route('/extract-latex', methods=['POST'])
def extract_latex():
    """Extract LaTeX from uploaded image (file upload or base64)"""
    try:
        logger.info("🚀 /extract-latex endpoint hit!")
        logger.info(f"📋 Request headers: {dict(request.headers)}")
        logger.info(f"📦 Content-Type: {request.content_type}")
        
        data = request.get_json()
        logger.info(f"📊 JSON data received: {bool(data)}")
        if data:
            logger.info(f"📝 Keys in data: {list(data.keys())}")
        
        # Check if it's base64 image data
        if data and 'image_data' in data:
            import base64
            import io
            
            try:
                logger.info("🖼️ Processing base64 image data...")
                # Remove data URL prefix if present
                image_data = data['image_data']
                logger.info(f"📏 Image data length: {len(image_data)}")
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                    logger.info("✂️ Removed data URL prefix")
                
                # Decode base64 to image
                image_bytes = base64.b64decode(image_data)
                logger.info(f"📦 Decoded to {len(image_bytes)} bytes")
                image = Image.open(io.BytesIO(image_bytes))
                logger.info(f"✅ Image opened successfully: {image.size} {image.mode}")
                
            except Exception as e:
                logger.error(f"❌ Base64 decode error: {str(e)}")
                return jsonify({'error': f'Invalid image data: {str(e)}'}), 400
        
        # Otherwise check for file upload
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No image selected'}), 400

            try:
                image = Image.open(file.stream)
            except Exception as e:
                return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        else:
            return jsonify({'error': 'No image data provided'}), 400

        if not ocr_service.is_available():
            return jsonify({'error': 'OCR service not available'}), 503

        try:
            # Extract LaTeX from image
            logger.info(f"🔍 Extracting LaTeX from image (size: {image.size})")
            latex_result = ocr_service.extract_latex_from_image(image)
            logger.info(f"✅ OCR extraction complete. Result: {latex_result[:100] if latex_result else 'Empty'}...")

            # Return in the format the frontend expects
            return jsonify({
                'success': True,
                'latex': latex_result,
                'formulas': [latex_result] if latex_result else [],  # Frontend expects array
                'text_content': [],  # Placeholder
                'confidence': 0.8,
                'raw_result': latex_result
            })

        except Exception as e:
            logger.error(f"❌ Error during OCR extraction: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'formulas': [],
                'text_content': []
            }), 500

    except Exception as e:
        logger.error(f"Error in extract_latex: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/analyze-math', methods=['POST'])
def analyze_math():
    """Analyze mathematical content in text"""
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400

        text = data['text']
        analysis = analyze_math_content(text)

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"Error in analyze_math: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/video-status/<scene_name>', methods=['GET'])
def video_status(scene_name):
    """Check video generation status"""
    try:
        status = video_generator.get_video_status(scene_name)
        return jsonify(status)

    except Exception as e:
        logger.error(f"Error in video_status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/video/<scene_name>', methods=['GET'])
def get_video(scene_name):
    """Serve generated video file"""
    try:
        status = video_generator.get_video_status(scene_name)

        if status['status'] != 'completed':
            return jsonify({'error': 'Video not ready or not found'}), 404

        video_path = status['video_path']
        return send_file(video_path, as_attachment=True, download_name=f"{scene_name}.mp4")

    except Exception as e:
        logger.error(f"Error in get_video: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/cleanup', methods=['POST'])
def cleanup_videos():
    """Clean up old video files"""
    try:
        data = request.get_json() or {}
        max_age_days = data.get('max_age_days', 7)

        result = video_generator.cleanup_old_videos(max_age_days)

        if result['success']:
            return jsonify({
                'success': True,
                'cleaned_files': result['cleaned_files'],
                'total_size_cleaned': result['total_size_cleaned']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

    except Exception as e:
        logger.error(f"Error in cleanup_videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/ai-suggest', methods=['POST'])
def ai_suggest():
    """Get AI suggestions for Manim code generation"""
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400

        text = data['text']

        if not ai_service.is_available():
            return jsonify({'error': 'AI service not available'}), 503

        # Generate suggestions
        math_expressions = extract_math_expressions(text)
        topic = math_expressions[0] if math_expressions else text
        suggestions = ai_service.generate_manim_code(text, topic)

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        logger.error(f"Error in ai_suggest: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/list-videos', methods=['GET'])
def list_videos():
    """List all generated video files"""
    try:
        import os
        from pathlib import Path
        
        videos_dir = Path(__file__).parent.parent / 'videos'
        videos = []
        
        if videos_dir.exists():
            for file in videos_dir.glob('*.mp4'):
                stat = file.stat()
                videos.append({
                    'filename': file.name,
                    'path': f'/api/videos/{file.name}',
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })
        
        # Sort by modification time (newest first)
        videos.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'videos': videos,
            'count': len(videos)
        })
    
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/videos/<filename>', methods=['GET'])
def serve_video(filename):
    """Serve video files"""
    try:
        from pathlib import Path
        from flask import send_from_directory
        
        videos_dir = Path(__file__).parent.parent / 'videos'
        
        logger.info(f"📹 Serving video: {filename}")
        logger.info(f"📁 Videos directory: {videos_dir}")
        
        if not (videos_dir / filename).exists():
            logger.error(f"❌ Video file not found: {filename}")
            return jsonify({'error': 'Video not found'}), 404
        
        return send_from_directory(videos_dir, filename, mimetype='video/mp4')
    
    except Exception as e:
        logger.error(f"Error serving video: {e}")
        return jsonify({'error': 'Internal server error'}), 500