"""
Test script to verify Cortensor Agent Auditor setup
Run this after completing setup to ensure everything works
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    """Test that all dependencies are installed"""
    print("Testing imports...")
    try:
        import fastapi
        import web3
        import sqlalchemy
        import sentence_transformers
        import numpy
        import sklearn
        print("✓ All Python dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_web3_connection():
    """Test Web3 connection to Arbitrum Sepolia"""
    print("\nTesting Web3 connection...")
    try:
        from backend.web3_client import web3_client
        is_connected = web3_client.w3.is_connected()
        if is_connected:
            print(f"✓ Connected to Arbitrum Sepolia")
            print(f"  Account: {web3_client.account.address}")
            return True
        else:
            print("✗ Failed to connect to RPC")
            return False
    except Exception as e:
        print(f"✗ Web3 connection error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    try:
        from backend.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_models():
    """Test that database models are properly defined"""
    print("\nTesting database models...")
    try:
        from backend.models import Agent, Audit, ReputationHistory, ValidatorStats
        print("✓ All models imported successfully")
        return True
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False

def test_engines():
    """Test that engines can be initialized"""
    print("\nTesting engines...")
    try:
        from backend.engines.poi_engine import PoIEngine
        from backend.engines.pouw_engine import PoUWEngine
        from backend.engines.evidence_generator import EvidenceBundleGenerator
        
        poi = PoIEngine()
        pouw = PoUWEngine()
        evidence = EvidenceBundleGenerator()
        
        print("✓ All engines initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Engine initialization failed: {e}")
        return False

def test_embedding_model():
    """Test sentence transformer model"""
    print("\nTesting embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(["test sentence"])
        print(f"✓ Embedding model loaded (dimension: {len(embeddings[0])})")
        return True
    except Exception as e:
        print(f"✗ Embedding model failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Cortensor Agent Auditor - System Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_web3_connection,
        test_database_connection,
        test_models,
        test_engines,
        test_embedding_model
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Run backend:  python -m backend.main")
        print("2. Run frontend: cd frontend && npm run dev")
        print("3. Submit test audit via http://localhost:3000/submit")
        return 0
    else:
        print("\n❌ Some tests failed. Please check configuration.")
        print("\nCommon issues:")
        print("- Missing .env configuration")
        print("- PostgreSQL not running")
        print("- Invalid RPC URL or private key")
        print("- Missing dependencies (run: pip install -r requirements.txt)")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
