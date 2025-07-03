#!/usr/bin/env python3
"""
Startup script for Burnaby Home Loans Chatbot API
"""

import os
import sys

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before starting the application.")
        print("You can create a .env file in the project root with:")
        print("OPENAI_API_KEY=your_api_key_here")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🏠 Burnaby Home Loans Chatbot API")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("✅ Environment variables configured")
    print("🚀 Starting Flask application...")
    # print("📡 API will be available at: http://localhost:5000")
    # print("🩺 Health check: http://localhost:5000/health")
    # print("💬 Chatbot endpoint: http://localhost:5000/chatbot-api")
    # In production, use your Render URL (e.g., https://burnabyhomeloans.onrender.com)
    print("\nPress Ctrl+C to stop the server")
    print("=" * 40)
    
    # Import and run the Flask app
    from app import app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main() 