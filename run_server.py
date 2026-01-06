#!/usr/bin/env python
"""
Run the CBC News Style Checker API server.

Usage:
    python run_server.py                    # Development mode with auto-reload
    python run_server.py --production       # Production mode
    python run_server.py --port 3000        # Custom port
"""

import argparse
import uvicorn
import os  # <--- 1. Import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CBC News Style Checker API")
    
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")

    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port to bind to")
    
    parser.add_argument("--production", action="store_true", help="Run in production mode (no auto-reload)")
    parser.add_argument("--reload", action="store_true", help="Explicitly enable auto-reload (default in non-production mode)")
    
    args = parser.parse_args()
    
    # Reload is enabled if --reload is set OR if --production is NOT set
    # Note: If both are set, production takes precedence? Or reload? 
    # Let's say explicit --reload wins or just stick to "production disables it".
    # Existing logic was: reload = not args.production.
    # New logic: If --reload is passed, we want reload. If --production is passed, we want no reload.
    # If neither, we assume development (reload).
    
    if args.reload:
        reload = True
    elif args.production:
        reload = False
    else:
        reload = True
    
    print(f"🚀 Starting CBC News Style Checker API on {args.host}:{args.port}")
    print(f"   Mode: {'Production' if args.production else 'Development (auto-reload)'}")
    print(f"   API Docs: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs")
    print()
    
    uvicorn.run(
        "src.api.server:app",
        host=args.host,
        port=args.port,
        reload=reload,
        log_level="info",
        loop="asyncio"
    )
