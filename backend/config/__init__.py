"""
Configuration settings for the Manim OCR Integration backend.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
VIDEO_DIR = BASE_DIR / "videos"
CACHE_DIR = BASE_DIR / "cache"

# Ensure directories exist
VIDEO_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Flask configuration
class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    HOST = '0.0.0.0'
    PORT = 5000

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Select configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

def get_config():
    """Get configuration based on FLASK_ENV environment variable"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, DevelopmentConfig)()

# Video generation settings
VIDEO_CONFIG = {
    'output_dir': VIDEO_DIR,
    'quality_options': ['low_quality', 'medium_quality', 'high_quality'],
    'default_quality': 'medium_quality',
    'max_batch_size': 10,
    'task_timeout_hours': 24
}

# AI settings
AI_CONFIG = {
    'cache_file': CACHE_DIR / "ai_cache.json",
    'tasks_file': BASE_DIR / "tasks.json",
    'max_tokens': 1900,
    'temperature': 0.7
}

# OCR settings
OCR_CONFIG = {
    'model_path': None,  # Will be set dynamically
    'preprocessing_levels': ['minimal', 'moderate', 'aggressive'],
    'default_preprocessing': 'moderate'
}

# External service availability flags (set during import)
SERVICE_AVAILABILITY = {
    'mixtex': False,
    'manim': False,
    'openai': False,
    'sympy': False
}