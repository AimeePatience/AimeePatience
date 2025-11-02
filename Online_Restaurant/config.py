import os
from os.path import join, dirname

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    BASE_DIR = dirname(dirname(__file__)) if __file__ else os.path.dirname(os.path.abspath(__file__))
    
    # Database configuration
    # SQLite for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'restaurant.db')
    
    # MySQL for production (PythonAnywhere)
    # Uncomment and configure for production:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'mysql+pymysql://username:password@hostname/database_name'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Hugging Face API configuration
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY') or ''
    HUGGINGFACE_API_URL = os.environ.get('HUGGINGFACE_API_URL') or \
        'https://api-inference.huggingface.co/models/google/flan-t5-base'
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Knowledge base path
    KNOWLEDGE_BASE_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'restaurant_info.txt')


