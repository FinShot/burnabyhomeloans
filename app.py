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
import sqlite3
from typing import Dict, Any, Optional

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

# Lead Qualification System
LEAD_QUALIFICATION_QUESTIONS = [
    {
        "id": 1,
        "question": "What is your approximate annual household income before taxes?",
        "field": "annual_income",
        "type": "number",
        "options": None
    },
    {
        "id": 2,
        "question": "How much of a downpayment do you have approximately?",
        "field": "down_payment",
        "type": "number",
        "options": None
    },
    {
        "id": 3,
        "question": "Monthly debt payments? (e.g., car loans, student loans, credit card minimums, excluding rent/mortgage)",
        "field": "monthly_debt",
        "type": "number",
        "options": None
    },
    {
        "id": 4,
        "question": "What is your credit score approximately?",
        "field": "credit_score",
        "type": "select",
        "options": [
            "Excellent (740+)",
            "Good (670-739)",
            "Fair (580-669)",
            "Not sure"
        ]
    },
    {
        "id": 5,
        "question": "What are the proposed property taxes, heating, and strata costs on a monthly basis (e.g. $2,400 in property taxes would be $200 per month). ?",
        "field": "property_costs",
        "type": "number",
        "options": None
    },
    {
        "id": 6,
        "question": "When are you needing financing?",
        "field": "timeline",
        "type": "select",
        "options": [
            "Right away / Immediately",
            "0-3 months",
            "3-6 months",
            "Longer than 6 months",
            "Just exploring"
        ]
    }
]

# Lead scoring criteria
LEAD_SCORING_CRITERIA = {
    "hot": {
        "timeline": ["Right away / Immediately", "0-3 months"],
        "credit_score_min": 650,
        "income_min": 100000,
        "action": "immediate_followup",
        "message": "This looks promising! May I have one of our mortgage advisors contact you right away? Can I get your phone number and email?"
    },
    "warm": {
        "timeline": ["3-6 months"],
        "credit_score_min": 650,
        "income_min": 75000,
        "action": "monthly_followup",
        "message": "Since you're planning ahead, we'd love to stay in touch! Would you like to receive our monthly mortgage market updates and tips? Can I get your email address?"
    },
    "cold": {
        "timeline": ["Longer than 6 months", "Just exploring"],
        "credit_score_max": 625,
        "income_max": 50000,
        "action": "educational_content",
        "message": "Based on the information, it looks like you're in the early stages of preparing for a mortgage. While an immediate pre-approval might be challenging, there's definitely a path forward! Would you like some resources on how to improve your credit score, save for a down payment, or understand the mortgage process better?"
    }
}

# Initialize database
def init_database():
    """Initialize SQLite database for storing leads"""
    conn = sqlite3.connect('leads.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            annual_income REAL,
            down_payment REAL,
            monthly_debt REAL,
            credit_score TEXT,
            property_costs REAL,
            timeline TEXT,
            lead_score TEXT,
            contact_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

def init_rates_table():
    """Initialize rates table and set default rates if not present."""
    conn = sqlite3.connect('leads.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            fixed_rate REAL,
            variable_rate REAL,
            three_year_fixed_rate REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Check if a row exists; if not, insert defaults
    cursor.execute('SELECT COUNT(*) FROM rates WHERE id = 1')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO rates (id, fixed_rate, variable_rate, three_year_fixed_rate) VALUES (1, 5.5, 5.8, 5.2)
        ''')
    conn.commit()
    conn.close()

def migrate_rates_table():
    conn = sqlite3.connect('leads.db')
    cursor = conn.cursor()
    # Try to add the column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE rates ADD COLUMN three_year_fixed_rate REAL DEFAULT 5.2")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    conn.close()

# Call this function at startup
migrate_rates_table()

# Lead Qualification Helper Functions
def extract_number_from_text(text: str) -> Optional[float]:
    """Extract numeric value from text input"""
    import re
    numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', text.replace(',', ''))
    if numbers:
        return float(numbers[0])
    return None

def get_credit_score_numeric(credit_score_text: str) -> Optional[int]:
    """Convert credit score text to numeric value"""
    if "740+" in credit_score_text:
        return 740
    elif "670-739" in credit_score_text:
        return 670
    elif "580-669" in credit_score_text:
        return 580
    elif "Not sure" in credit_score_text:
        return None
    return None

def score_lead(lead_data: Dict[str, Any]) -> str:
    """Score lead based on criteria and return hot/warm/cold"""
    timeline = lead_data.get('timeline', '')
    credit_score_text = lead_data.get('credit_score', '')
    annual_income = lead_data.get('annual_income', 0)
    
    credit_score_numeric = get_credit_score_numeric(credit_score_text)
    
    # Check hot lead criteria
    if (timeline in LEAD_SCORING_CRITERIA["hot"]["timeline"] and
        credit_score_numeric and credit_score_numeric >= LEAD_SCORING_CRITERIA["hot"]["credit_score_min"] and
        annual_income >= LEAD_SCORING_CRITERIA["hot"]["income_min"]):
        return "hot"
    
    # Check warm lead criteria
    if (timeline in LEAD_SCORING_CRITERIA["warm"]["timeline"] and
        credit_score_numeric and credit_score_numeric >= LEAD_SCORING_CRITERIA["warm"]["credit_score_min"] and
        annual_income >= LEAD_SCORING_CRITERIA["warm"]["income_min"]):
        return "warm"
    
    # Default to cold lead
    return "cold"

def save_lead_to_database(session_id: str, lead_data: Dict[str, Any], lead_score: str):
    """Save lead data to SQLite database"""
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (
                session_id, annual_income, down_payment, monthly_debt, 
                credit_score, property_costs, timeline, lead_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            lead_data.get('annual_income'),
            lead_data.get('down_payment'),
            lead_data.get('monthly_debt'),
            lead_data.get('credit_score'),
            lead_data.get('property_costs'),
            lead_data.get('timeline'),
            lead_score
        ))
        conn.commit()
        conn.close()
        logger.info(f"Lead saved to database for session {session_id}")
    except Exception as e:
        logger.error(f"Error saving lead to database: {str(e)}")

def get_current_fixed_rate() -> float:
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('SELECT fixed_rate FROM rates WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return float(row[0])
    except Exception as e:
        logger.error(f"Error fetching fixed rate: {str(e)}")
    return 5.5  # fallback default

def calculate_mortgage_estimate(lead_data: Dict[str, Any]) -> str:
    """Calculate rough mortgage estimate based on lead data and current fixed rate"""
    annual_income = lead_data.get('annual_income', 0)
    down_payment = lead_data.get('down_payment', 0)
    monthly_debt = lead_data.get('monthly_debt', 0)
    property_costs = lead_data.get('property_costs', 0)
    
    if not annual_income:
        return "I'd need your income information to provide an accurate estimate."
    
    # Get the current fixed rate
    fixed_rate = get_current_fixed_rate()
    rate_display = f"{fixed_rate:.2f}%"
    interest = fixed_rate / 100
    
    # Rough calculation: 4-5x annual income, minus down payment
    max_mortgage = annual_income * 4.5
    max_property_value = max_mortgage + down_payment
    
    # Monthly payment estimate (using current fixed rate, 25-year amortization)
    monthly_interest = interest / 12
    n_payments = 25 * 12
    try:
        monthly_payment = (max_mortgage * monthly_interest) / (1 - (1 + monthly_interest) ** -n_payments)
    except Exception:
        monthly_payment = 0
    
    return (
        f"Based on your information and a current 5-year fixed rate of {rate_display}, you might qualify for a mortgage of approximately ${max_mortgage:,.0f}, "
        f"allowing you to purchase a property up to around ${max_property_value:,.0f}. "
        f"Your estimated monthly mortgage payment would be approximately ${monthly_payment:,.0f}. "
        "Please note this is a rough estimate - actual approval amounts depend on many factors including credit score, debt ratios, and current market conditions."
    )

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
    Handle chatbot API requests with lead qualification system
    """
    try:
        # Validate request method
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
        session_id = data.get('session_id', 'default_session')
        conversation_history = data.get('history', [])
        qualification_state = data.get('qualification_state', {})
        lead_data = data.get('lead_data', {})

        # Validate message length
        if len(user_message) > 500:
            return jsonify({'error': 'Message too long'}), 400

        print(f"User message: {user_message}")
        print(f"Qualification state: {qualification_state}")
        print(f"Lead data: {lead_data}")

        # Check for booking intent first
        booking_patterns = [
            r'book', r'schedule', r'appointment', r'meeting', r'get an appointment',
            r'see a broker', r'meet', r'consult', r'call', r'talk to', r'speak to', r'visit'
        ]
        for pattern in booking_patterns:
            if re.search(pattern, user_message.lower()):
                return jsonify({
                    "role": "assistant",
                    "content": (
                        "You can book a time directly here:<br>"
                        "<a href='https://calendly.com/steve-r-ennis' target='_blank'>Book a Consultation</a>"
                    )
                })

        # Check for qualification intent (improved regex-based matching)
        qualification_patterns = [
            r'qualif(y|ication|ied)',
            r'how much.*(qualify|afford|get|borrow)',
            r'what.*(qualify for|max(imum)? mortgage|can i afford|can i get|can i borrow)',
            r'can i afford',
            r'pre-approval',
            r'preapproval',
            r'pre-qual',
            r'prequal',
            r'estimate',
            r'budget',
            r'purchase power',
            r'mortgage amount',
            r'afford.*house',
            r'afford.*home',
            r'how much.*house',
            r'how much.*home',
            r'eligible',
            r'eligibility',
            r'approval'
        ]
        is_qualification_request = any(re.search(pattern, user_message.lower()) for pattern in qualification_patterns)
        
        # If this is a qualification request and we haven't started the flow yet
        if is_qualification_request and not qualification_state.get('in_progress'):
            return jsonify({
                "role": "assistant",
                "content": f"Great! Let's get started. {LEAD_QUALIFICATION_QUESTIONS[0]['question']}",
                "qualification_state": {
                    "in_progress": True,
                    "current_question": 1,
                    "waiting_for_response": False
                }
            })

        # Special trigger for quick action button
        if user_message.strip().lower() == 'start qualification':
            return jsonify({
                "role": "assistant",
                "content": "Great! Let's get started. " + LEAD_QUALIFICATION_QUESTIONS[0]['question'],
                "qualification_state": {
                    "in_progress": True,
                    "current_question": 1,
                    "waiting_for_response": False
                },
                "lead_data": lead_data
            })

        # Handle qualification flow
        if qualification_state.get('in_progress'):
            current_question = qualification_state.get('current_question', 0)
            
            # If we're waiting for a response to the qualification prompt
            if qualification_state.get('waiting_for_response'):
                if any(word in user_message.lower() for word in ['yes', 'yeah', 'sure', 'okay', 'ok', 'yep']):
                    # Start the qualification questions
                    return jsonify({
                        "role": "assistant",
                        "content": f"Great! Let's get started. {LEAD_QUALIFICATION_QUESTIONS[0]['question']}",
                        "qualification_state": {
                            "in_progress": True,
                            "current_question": 1,
                            "waiting_for_response": False
                        }
                    })
                else:
                    # User doesn't want to qualify, return to normal chat
                    return jsonify({
                        "role": "assistant",
                        "content": "No problem! How else can I help you with your mortgage questions today?",
                        "qualification_state": {
                            "in_progress": False,
                            "current_question": 0,
                            "waiting_for_response": False
                        }
                    })
            
            # Handle qualification question responses
            if current_question > 0 and current_question <= len(LEAD_QUALIFICATION_QUESTIONS):
                question_data = LEAD_QUALIFICATION_QUESTIONS[current_question - 1]
                field_name = question_data['field']
                
                # Process the answer
                if question_data['type'] == 'number':
                    # Extract number from text
                    numeric_value = extract_number_from_text(user_message)
                    if numeric_value is not None:
                        lead_data[field_name] = numeric_value
                    else:
                        return jsonify({
                            "role": "assistant",
                            "content": "I need a number for that. Could you please provide a numeric value?",
                            "qualification_state": qualification_state,
                            "lead_data": lead_data
                        })
                elif question_data['type'] == 'select':
                    # Special handling for credit score question (Question 4)
                    if current_question == 4:
                        user_input = user_message.strip().lower()
                        selected_option = None
                        # Try to extract a number
                        numeric_value = extract_number_from_text(user_message)
                        if numeric_value is not None:
                            if numeric_value >= 740:
                                selected_option = "Excellent (740+)"
                            elif 670 <= numeric_value < 740:
                                selected_option = "Good (670-739)"
                            elif 580 <= numeric_value < 670:
                                selected_option = "Fair (580-669)"
                            elif numeric_value < 580:
                                selected_option = "Poor below 580"
                        else:
                            # Try to match a word
                            if "excellent" in user_input:
                                selected_option = "Excellent (740+)"
                            elif "good" in user_input:
                                selected_option = "Good (670-739)"
                            elif "fair" in user_input:
                                selected_option = "Fair (580-669)"
                            elif "poor" in user_input:
                                selected_option = "Poor below 580"
                            elif "not sure" in user_input or "unsure" in user_input:
                                selected_option = "Not sure"
                        if selected_option:
                            lead_data[field_name] = selected_option
                        else:
                            # Inline options for credit score
                            options_inline = "Excellent (740+); Good (670-739); Fair (580-669); Poor below 580; Not sure."
                            return jsonify({
                                "role": "assistant",
                                "content": f"Question 4 of 6. What is your credit score approximately? {options_inline}",
                                "qualification_state": qualification_state,
                                "lead_data": lead_data
                            })
                    else:
                        # Check if user selected one of the options
                        selected_option = None
                        for option in question_data['options']:
                            if option.lower() in user_message.lower() or any(word in user_message.lower() for word in option.lower().split()):
                                selected_option = option
                                break
                        if selected_option:
                            lead_data[field_name] = selected_option
                        else:
                            # Show options again (for other select questions)
                            options_text = "\n".join([f"- {option}" for option in question_data['options']])
                            return jsonify({
                                "role": "assistant",
                                "content": f"Please select one of these options:\n{options_text}",
                                "qualification_state": qualification_state,
                                "lead_data": lead_data
                            })
                
                # Move to next question or finish
                if current_question < len(LEAD_QUALIFICATION_QUESTIONS):
                    next_question = LEAD_QUALIFICATION_QUESTIONS[current_question]
                    return jsonify({
                        "role": "assistant",
                        "content": f"Question {current_question + 1} of {len(LEAD_QUALIFICATION_QUESTIONS)}. {next_question['question']}",
                        "qualification_state": {
                            "in_progress": True,
                            "current_question": current_question + 1,
                            "waiting_for_response": False
                        },
                        "lead_data": lead_data
                    })
                else:
                    # All questions answered - calculate estimate and score lead
                    mortgage_estimate = calculate_mortgage_estimate(lead_data)
                    lead_score = score_lead(lead_data)
                    
                    # Save lead to database
                    save_lead_to_database(session_id, lead_data, lead_score)
                    
                    # Get appropriate response based on lead score
                    score_response = LEAD_SCORING_CRITERIA[lead_score]["message"]
                    
                    # Add educational content for cold leads
                    if lead_score == "cold":
                        educational_content = """
                        
                        Here are some helpful resources:
                        • <a href='https://www.cmhc-schl.gc.ca/en/consumers/home-buying' target='_blank'>CMHC Home Buying Guide</a>
                        • <a href='https://www.transunion.ca/credit-score' target='_blank'>Understanding Your Credit Score</a>
                        • <a href='https://www.canada.ca/en/financial-consumer-agency/services/mortgages.html' target='_blank'>Government of Canada Mortgage Information</a>
                        
                        Would you like me to send you a guide on improving your credit score or saving for a down payment?"""
                        score_response += educational_content
                    
                    return jsonify({
                        "role": "assistant",
                        "content": f"{mortgage_estimate}\n\n{score_response}",
                        "qualification_state": {
                            "in_progress": False,
                            "current_question": 0,
                            "waiting_for_response": False,
                            "completed": True
                        },
                        "lead_data": lead_data,
                        "lead_score": lead_score
                    })

        # Default: Use OpenAI for general conversation
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
    calendly_user_uri = os.getenv('CALENDLY_USER_URI')  # e.g. https://calendly.com/steve-r-ennis

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

@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads from database (for admin purposes)"""
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, session_id, annual_income, down_payment, monthly_debt, 
                   credit_score, property_costs, timeline, lead_score, 
                   contact_info, created_at 
            FROM leads 
            ORDER BY created_at DESC
        ''')
        leads = []
        for row in cursor.fetchall():
            leads.append({
                'id': row[0],
                'session_id': row[1],
                'annual_income': row[2],
                'down_payment': row[3],
                'monthly_debt': row[4],
                'credit_score': row[5],
                'property_costs': row[6],
                'timeline': row[7],
                'lead_score': row[8],
                'contact_info': row[9],
                'created_at': row[10]
            })
        conn.close()
        return jsonify({'leads': leads})
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        return jsonify({'error': 'Failed to fetch leads'}), 500

@app.route('/api/leads/export', methods=['GET'])
def export_leads():
    """Export leads to CSV format"""
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, annual_income, down_payment, monthly_debt, 
                   credit_score, property_costs, timeline, lead_score, 
                   contact_info, created_at 
            FROM leads 
            ORDER BY created_at DESC
        ''')
        
        # Create CSV content
        csv_content = "Session ID,Annual Income,Down Payment,Monthly Debt,Credit Score,Property Costs,Timeline,Lead Score,Contact Info,Created At\n"
        for row in cursor.fetchall():
            csv_content += f"{row[0]},{row[1] or ''},{row[2] or ''},{row[3] or ''},{row[4] or ''},{row[5] or ''},{row[6] or ''},{row[7] or ''},{row[8] or ''},{row[9] or ''},{row[10] or ''}\n"
        
        conn.close()
        
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=leads_export.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting leads: {str(e)}")
        return jsonify({'error': 'Failed to export leads'}), 500

@app.route('/api/leads/stats', methods=['GET'])
def get_lead_stats():
    """Get lead statistics"""
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        
        # Total leads
        cursor.execute('SELECT COUNT(*) FROM leads')
        total_leads = cursor.fetchone()[0]
        
        # Leads by score
        cursor.execute('SELECT lead_score, COUNT(*) FROM leads GROUP BY lead_score')
        leads_by_score = dict(cursor.fetchall())
        
        # Recent leads (last 7 days)
        cursor.execute('''
            SELECT COUNT(*) FROM leads 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_leads = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_leads': total_leads,
            'leads_by_score': leads_by_score,
            'recent_leads': recent_leads
        })
    except Exception as e:
        logger.error(f"Error fetching lead stats: {str(e)}")
        return jsonify({'error': 'Failed to fetch lead statistics'}), 500

@app.route('/api/rates', methods=['GET'])
def get_rates():
    """Get the current mortgage rates."""
    try:
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('SELECT fixed_rate, variable_rate, three_year_fixed_rate, updated_at FROM rates WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({
                'fixed_rate': row[0],
                'variable_rate': row[1],
                'three_year_fixed_rate': row[2],
                'updated_at': row[3]
            })
        else:
            return jsonify({'error': 'Rates not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching rates: {str(e)}")
        return jsonify({'error': 'Failed to fetch rates'}), 500

@app.route('/api/rates', methods=['POST'])
def update_rates():
    """Update the current mortgage rates (admin only)."""
    try:
        data = request.get_json()
        fixed_rate = float(data.get('fixed_rate'))
        variable_rate = float(data.get('variable_rate'))
        three_year_fixed_rate = float(data.get('three_year_fixed_rate'))
        conn = sqlite3.connect('leads.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rates SET fixed_rate = ?, variable_rate = ?, three_year_fixed_rate = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1
        ''', (fixed_rate, variable_rate, three_year_fixed_rate))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'fixed_rate': fixed_rate, 'variable_rate': variable_rate, 'three_year_fixed_rate': three_year_fixed_rate})
    except Exception as e:
        logger.error(f"Error updating rates: {str(e)}")
        return jsonify({'error': 'Failed to update rates'}), 500

@app.route('/admin.html')
def serve_admin():
    return send_from_directory('.', 'admin.html')

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