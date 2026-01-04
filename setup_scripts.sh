#!/bin/bash
# ========== setup.sh ==========
# Quick setup script for Sherlock App

echo "🔍 Setting up Sherlock Account Analysis System..."

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p agents
mkdir -p services
mkdir -p tools
mkdir -p utils
mkdir -p data
mkdir -p logs
mkdir -p tests

# Create __init__.py files
touch agents/__init__.py
touch services/__init__.py
touch tools/__init__.py
touch utils/__init__.py
touch tests/__init__.py

# Create .env from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Environment
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8080

# OpenAI Configuration (REQUIRED - Add your key here)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3

# Data Configuration
DATA_FILE_PATH=data/domestic_accounts.xlsx

# Redis Configuration (Optional)
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# TTL Settings
CONVERSATION_TTL_SECONDS=604800
VISUALIZATION_TTL_SECONDS=259200

# CORS
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Rate Limiting
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=60
EOF
    echo "✅ .env file created. IMPORTANT: Add your OpenAI API key!"
else
    echo "⚠️  .env file already exists, skipping..."
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists, skipping..."
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

# Install requirements
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create middleware __init__.py (empty for now)
mkdir -p middleware
touch middleware/__init__.py

# Create a simple auth middleware file
cat > middleware/auth.py << 'EOF'
"""
Authentication Middleware
"""
from functools import wraps
from bottle import request, abort
import os

def require_auth(func):
    """Decorator for requiring API key authentication"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true':
            api_key = request.headers.get('X-API-Key')
            valid_keys = os.getenv('API_KEYS', '').split(',')
            
            if not api_key or api_key not in valid_keys:
                abort(401, 'Unauthorized')
        
        return func(*args, **kwargs)
    return wrapper
EOF

echo "✅ Middleware created"

# Print success message
echo ""
echo "✨ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Add your OpenAI API key to .env file"
echo "2. Copy your data file to data/domestic_accounts.xlsx"
echo "3. Activate virtual environment: source venv/bin/activate"
echo "4. Run the application: python app.py"
echo ""
echo "🚀 Your Sherlock system will be available at http://localhost:8080"
echo ""

# ========== PYTHON __INIT__ FILES CONTENT ==========

# agents/__init__.py
cat > agents/__init__.py << 'EOF'
"""
Agents Package
Multi-agent system for specialized analysis tasks
"""
from .agent_orchestrator import AgentOrchestrator
from .data_agent import DataAnalysisAgent
from .visualization_agent import VisualizationAgent
from .insight_agent import InsightAgent
from .report_agent import ReportGenerationAgent

__all__ = [
    'AgentOrchestrator',
    'DataAnalysisAgent',
    'VisualizationAgent',
    'InsightAgent',
    'ReportGenerationAgent'
]
EOF

# services/__init__.py
cat > services/__init__.py << 'EOF'
"""
Services Package
Business logic and data services
"""
from .conversation_service import ConversationService

__all__ = ['ConversationService']
EOF

# tools/__init__.py
cat > tools/__init__.py << 'EOF'
"""
Tools Package
Data processing and analysis tools
"""
from .data_tools import DataTools

__all__ = ['DataTools']
EOF

# utils/__init__.py
cat > utils/__init__.py << 'EOF'
"""
Utilities Package
Common utilities and helpers
"""
from .logger import setup_logger

__all__ = ['setup_logger']
EOF

echo "📝 __init__.py files created"

# Create a simple test file
cat > tests/test_basic.py << 'EOF'
"""
Basic tests for Sherlock App
"""
import pytest
from config import Config

def test_config_loading():
    """Test configuration loading"""
    config = Config()
    assert config.ENVIRONMENT in ['development', 'production', 'testing']
    assert config.PORT > 0

def test_config_validation():
    """Test configuration validation"""
    # This will raise if OPENAI_API_KEY is not set
    # In real setup, it should be set in .env
    config = Config()
    assert hasattr(config, 'OPENAI_API_KEY')

if __name__ == '__main__':
    pytest.main([__file__])
EOF

echo "🧪 Test file created"

# Create a run script
cat > run.sh << 'EOF'
#!/bin/bash
# Quick run script

echo "🚀 Starting Sherlock Application..."

# Activate virtual environment
source venv/bin/activate || . venv/Scripts/activate

# Run application
python app.py
EOF

chmod +x run.sh

echo "✅ Run script created (./run.sh)"

# Create a sample data generator (for testing without real data)
cat > generate_sample_data.py << 'EOF'
"""
Generate sample data for testing
Run this if you don't have real data yet
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(n_records=100):
    """Generate sample domestic account data"""
    
    np.random.seed(42)
    
    data = {
        'CASID': [f'CASID{i:06d}' for i in range(n_records)],
        'LEGAL_NAME': [f'Company {i}' for i in range(n_records)],
        'ECI': [f'ECI{i:04d}' for i in range(n_records)],
        'UCN': [f'UCN{i:05d}' for i in range(n_records)],
        'COUNTRY_CD': np.random.choice(['US', 'UK', 'FR', 'DE', 'JP'], n_records),
        'EFF_BALANCE_LCY': np.random.uniform(-1000000, 5000000, n_records),
        'EFF_BALANCE_DBT': np.random.uniform(0, 100000, n_records),
        'EFF_BALANCE_CRDT': np.random.uniform(0, 100000, n_records),
        'MTD_BALANCE_LCY': np.random.uniform(-500000, 3000000, n_records),
        'OVERDRAFT_INT_AMT': np.random.choice([0] * 60 + list(np.random.uniform(10000, 2000000, 40))),
        'OD_Tenure': np.random.choice([0] * 60 + list(np.random.randint(1, 365, 40))),
        'OD_RATE': np.random.uniform(0, 8, n_records),
        'OVERDRAFT_LIMIT_AMT': np.random.uniform(0, 3000000, n_records),
        'BUSINESS_DT': [datetime.now() - timedelta(days=np.random.randint(0, 30)) for _ in range(n_records)],
        'ERISA_IND': np.random.choice(['Y', 'N'], n_records, p=[0.1, 0.9]),
        'CHAD_LAD_FLAG': np.random.choice(['Y', 'N'], n_records, p=[0.05, 0.95])
    }
    
    df = pd.DataFrame(data)
    
    # Save to Excel
    output_path = 'data/domestic_accounts.xlsx'
    df.to_excel(output_path, index=False)
    print(f"✅ Sample data generated: {output_path}")
    print(f"📊 Generated {n_records} records")
    print(f"💰 Accounts with overdraft: {(df['OVERDRAFT_INT_AMT'] > 0).sum()}")
    print(f"📈 Total overdraft amount: ${df['OVERDRAFT_INT_AMT'].sum():,.2f}")

if __name__ == '__main__':
    generate_sample_data(100)
EOF

echo "🎲 Sample data generator created (generate_sample_data.py)"

echo ""
echo "💡 Tip: If you don't have real data, run: python generate_sample_data.py"
echo ""
