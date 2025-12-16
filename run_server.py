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
    
    args = parser.parse_args()
    
    reload = not args.production
    
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
