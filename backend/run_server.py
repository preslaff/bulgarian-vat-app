#!/usr/bin/env python3
"""
Enhanced VAT API Server Startup Script
Fixes multiprocessing issues on Windows
"""

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Add current directory to Python path to ensure imports work
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # Import and run the FastAPI app
    try:
        from main_simple import app
        print("Starting Bulgarian VAT API Server...")
        print("Backend directory:", current_dir)
        print("Python version:", sys.version.split()[0])
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            reload=False,  # Disable reload to avoid multiprocessing issues
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("   pip install fastapi uvicorn sqlalchemy")
        sys.exit(1)
    except Exception as e:
        print(f"Server startup error: {e}")
        sys.exit(1)