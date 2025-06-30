#!/usr/bin/env python3
"""
Secure Chatbot API - Server-side OpenAI Integration
This file handles all OpenAI API calls securely using Python Flask
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
from dotenv import load_dotenv
import requests
import re

print("=== THIS IS THE CORRECT APP.PY ===")

# Load environment variables
load_dotenv()

print("API Key loaded:", os.getenv('OPENAI_API_KEY'))

# Initialize Flask app
app = Flask(__name__)

# Configure CORS (adjust for production)
CORS(app, origins=["*"], methods=["POST", "GET", "OPTIONS"], allow_headers=["Content-Type"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

# Mortgage-specific system prompt (identical to PHP version)
SYSTEM_PROMPT = """You are a professional mortgage broker assistant for Burnaby Home Loans in Burnaby, BC, Canada. 

Key Information:
- We specialize in mortgages for Burnaby and Greater Vancouver area
- Current rates: 5-year fixed ~5.5%, Variable ~5.8% (these are examples)
- We offer first-time buyer programs, refinancing, and commercial mortgages
- Popular Burnaby neighborhoods: Metrotown, Brentwood, Deer Lake, Burnaby Heights
- We work with all major Canadian banks and credit unions

Guidelines:
- Be helpful, professional, and knowledgeable about mortgages
- Provide accurate Canadian mortgage information
- Encourage users to apply for pre-approval or contact us
- If asked about specific rates, mention they change daily and recommend getting a current quote
- Keep responses concise but informative (under 200 words)
- Always maintain a professional, trustworthy tone
- If you don't know something specific, recommend they speak with our mortgage specialists

Remember: You represent a professional mortgage brokerage. Be helpful but always recommend speaking with our licensed mortgage professionals for personalized advice."""

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/chatbot-api', methods=['POST'])
def chatbot_api():
    """
    Handle chatbot API requests - replicates the PHP functionality exactly
    """
    data = request.get_json()
    user_message = data.get('message', '').lower()

    print("User message received:", user_message)

    # Robust booking intent detection
    booking_patterns = [
        r'book', r'schedule', r'appointment', r'meeting', r'get an appointment',
        r'see a broker', r'meet', r'consult', r'call', r'talk to', r'speak to', r'visit'
    ]
    matched = False
    for pattern in booking_patterns:
        if re.search(pattern, user_message):
            print(f"Matched pattern: {pattern}")
            matched = True
    if matched:
        return jsonify({
            "success": True,
            "message": (
                "You can book a time directly here:<br>"
                "<a href='https://calendly.com/steve-r-ennis/15min' target='_blank'>15-minute Discovery Call</a><br>"
                "<a href='https://calendly.com/steve-r-ennis/30min' target='_blank'>30-minute Mortgage Consultation</a>"
            )
        })

    try:
        # Validate request method (Flask handles this automatically, but keeping for consistency)
        if request.method != 'POST':
            return jsonify({'error': 'Method not allowed'}), 405

        # Check if API key is configured
        if not OPENAI_API_KEY:
            return jsonify({'error': 'API key not configured'}), 500

        # Get and validate input
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Invalid input'}), 400

        user_message = data['message'].strip()
        conversation_history = data.get('history', [])

        # Validate message length
        if len(user_message) > 500:
            return jsonify({'error': 'Message too long'}), 400

        # Prepare messages for OpenAI
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT}
        ]

        # Add conversation history (limit to last 6 messages for context)
        recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        
        for msg in recent_history:
            if 'role' in msg and 'content' in msg:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Add current user message
        messages.append({'role': 'user', 'content': user_message})

        # Make request to OpenAI
        try:
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                timeout=30
            )

            # Extract AI response
            if not response.choices or not response.choices[0].message:
                raise Exception("Invalid OpenAI response structure")
            
            ai_message = response.choices[0].message.content.strip()

            # Return response in the format expected by the frontend
            return jsonify({
                'role': 'assistant',
                'content': ai_message
            })

        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return jsonify({
                'error': "Sorry, I'm having trouble connecting right now. Please try again in a moment, or call us at (604) 555-0123 for immediate assistance."
            }), 500

        except Exception as e:
            logger.error(f"Unexpected error during OpenAI request: {str(e)}")
            return jsonify({
                'error': "Sorry, I'm having trouble processing your request. Please try again or contact us directly."
            }), 500

    except Exception as e:
        logger.error(f"General API error: {str(e)}")
        return jsonify({
            'error': "Sorry, I'm having trouble processing your request. Please try again or contact us directly."
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': bool(OPENAI_API_KEY)
    })

@app.route('/api/calendly-events', methods=['GET'])
def calendly_events():
    """
    Fetch Calendly event types for the authenticated user.
    Requires CALENDLY_API_KEY and CALENDLY_USER_URI in environment variables.
    """
    calendly_api_key = os.getenv('CALENDLY_API_KEY')
    calendly_user_uri = os.getenv('CALENDLY_USER_URI')  # e.g. https://api.calendly.com/users/USER_ID

    if not calendly_api_key or not calendly_user_uri:
        return jsonify({'error': 'Calendly API key or user URI not configured'}), 500

    try:
        # Fetch event types for the user
        url = f'https://api.calendly.com/event_types?user={calendly_user_uri}'
        headers = {
            'Authorization': f'Bearer {calendly_api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Return only relevant fields to frontend
        event_types = [
            {
                'name': event.get('name'),
                'scheduling_url': event.get('scheduling_url'),
                'duration': event.get('duration'),
                'description': event.get('description')
            }
            for event in data.get('collection', [])
        ]
        return jsonify({'event_types': event_types})
    except Exception as e:
        logger.error(f"Calendly API error: {str(e)}")
        return jsonify({'error': 'Failed to fetch Calendly events'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check if running in development or production
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"Starting Burnaby Home Loans Chatbot API on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"OpenAI API key configured: {bool(OPENAI_API_KEY)}")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
else:
    # Production mode when run via gunicorn
    logger.info("Starting in production mode via gunicorn")
    logger.info(f"OpenAI API key configured: {bool(OPENAI_API_KEY)}") 