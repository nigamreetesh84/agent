#!/usr/bin/env python
"""
Setup Verification Script
Run this to check if everything is configured correctly
"""

import sys
import os

def check_step(description, test_func):
    """Check a setup step"""
    try:
        result = test_func()
        print(f"✅ {description}")
        return True, result
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Error: {str(e)}")
        return False, None

def main():
    """Run all checks"""
    print("🔍 Sherlock Setup Verification\n")
    
    all_passed = True
    
    # Check 1: Python version
    def check_python():
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            return f"Python {version.major}.{version.minor}.{version.micro}"
        raise Exception(f"Python 3.9+ required, got {version.major}.{version.minor}")
    
    passed, result = check_step("Python version", check_python)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 2: Required files
    def check_files():
        required = [
            'app.py',
            'config.py',
            '.env',
            'agents/__init__.py',
            'agents/agent_orchestrator.py',
            'agents/data_agent.py',
            'agents/visualization_agent.py',
            'services/__init__.py',
            'services/conversation_service.py',
            'tools/__init__.py',
            'tools/data_tools.py',
            'utils/__init__.py',
            'utils/logger.py'
        ]
        missing = [f for f in required if not os.path.exists(f)]
        if missing:
            raise Exception(f"Missing files: {', '.join(missing)}")
        return f"{len(required)} files found"
    
    passed, result = check_step("Required files", check_files)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 3: Dependencies
    def check_dependencies():
        required_packages = [
            'bottle',
            'gevent',
            'geventwebsocket',
            'openai',
            'pandas',
            'numpy',
            'openpyxl',
            'dotenv'
        ]
        missing = []
        for pkg in required_packages:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        
        if missing:
            raise Exception(f"Missing packages: {', '.join(missing)}\nRun: pip install -r requirements.txt")
        return f"{len(required_packages)} packages installed"
    
    passed, result = check_step("Python packages", check_dependencies)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 4: Configuration
    def check_config():
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OPENAI_API_KEY not set in .env")
        if api_key == 'your-actual-openai-key-here' or api_key == 'your_openai_api_key_here':
            raise Exception("OPENAI_API_KEY is still placeholder. Add your real key to .env")
        if not api_key.startswith('sk-'):
            raise Exception("OPENAI_API_KEY format invalid (should start with sk-)")
        
        from config import Config
        config = Config()
        config.validate()
        
        return f"API key configured, model: {config.OPENAI_MODEL}"
    
    passed, result = check_step("Configuration", check_config)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 5: Data file
    def check_data():
        from dotenv import load_dotenv
        load_dotenv()
        
        data_path = os.getenv('DATA_FILE_PATH', 'data/domestic_accounts.xlsx')
        
        if not os.path.exists(data_path):
            raise Exception(f"Data file not found: {data_path}\nRun: python generate_sample_data.py")
        
        import pandas as pd
        df = pd.read_excel(data_path)
        
        return f"{len(df)} records, {len(df.columns)} columns"
    
    passed, result = check_step("Data file", check_data)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 6: Data tools
    def check_data_tools():
        from config import Config
        from tools.data_tools import DataTools
        
        config = Config()
        tools = DataTools(config)
        
        # Try to load data
        result = tools.get_domestic_metadata("summary")
        
        if 'error' in result:
            raise Exception(f"Data tools error: {result['error']}")
        
        return f"Data tools working, {result.get('total_records', 0)} records loaded"
    
    passed, result = check_step("Data tools", check_data_tools)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Check 7: OpenAI connection
    def check_openai():
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()
        
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Test API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for test
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        
        return f"API working, model: {response.model}"
    
    passed, result = check_step("OpenAI API", check_openai)
    all_passed = all_passed and passed
    if result:
        print(f"   {result}\n")
    
    # Summary
    print("\n" + "="*50)
    if all_passed:
        print("✅ All checks passed! You're ready to run:")
        print("   python app.py")
    else:
        print("❌ Some checks failed. Fix the errors above and try again.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
