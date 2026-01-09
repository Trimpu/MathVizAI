#!/usr/bin/env python3
"""
Unified OCR + Manim Backend Server
Flask server that provides both OCR and Manim video generation APIs.
Uses MixTeX for LaTeX OCR extraction and Manim for video generation.
"""

import os
import logging
from flask import Flask
from flask_cors import CORS

# Import modular components
from config import Config
from api.routes import api_bp
from services.ocr_service import ocr_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app with configuration
app = Flask(__name__)
CORS(app)

# Register API blueprint with /api prefix
app.register_blueprint(api_bp, url_prefix='/api')

# Initialize configuration
config = Config()

# Initialize Manim service output directory
from services.manim_service import manim_service
from pathlib import Path
videos_dir = Path(__file__).parent / 'videos'
videos_dir.mkdir(exist_ok=True)
manim_service.set_output_dir(videos_dir)
logger.info(f"📁 Manim output directory: {videos_dir}")

# Initialize OCR service (load model)
print("🔄 Initializing OCR service...")
ocr_service.initialize_model()

if __name__ == "__main__":
    print("🚀 Starting Modular Manim Integration Backend Server...")

    print("📋 Available endpoints:")
    print("   GET  /api/health              - Overall health check")
    print("   POST /api/generate-video      - Generate video from text")
    print("   POST /api/generate-from-latex - Generate video from LaTeX")
    print("   POST /api/extract-latex       - Extract LaTeX from image")
    print("   POST /api/analyze-math        - Analyze mathematical content")
    print("   GET  /api/video-status/<id>   - Check video generation status")
    print("   GET  /api/video/<id>          - Serve generated video")
    print("   POST /api/cleanup             - Clean up old videos")
    print("   POST /api/ai-suggest          - Get AI suggestions")

    # Start the Flask server
    print("🌐 Starting server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
