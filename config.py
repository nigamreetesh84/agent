"""
Configuration Management
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8080))
    
    # OpenAI - Required
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
    
    # Data
    DATA_FILE_PATH = os.getenv('DATA_FILE_PATH', 'data/domestic_accounts.xlsx')
    
    # Redis (Optional)
    REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # TTL
    CONVERSATION_TTL_SECONDS = int(os.getenv('CONVERSATION_TTL_SECONDS', 604800))  # 7 days
    VISUALIZATION_TTL_SECONDS = int(os.getenv('VISUALIZATION_TTL_SECONDS', 259200))  # 3 days
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    def validate(self):
        """Validate required configuration"""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required in .env file")
        
        # Create directories
        for directory in ['data', 'logs']:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)