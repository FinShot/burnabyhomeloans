<?php
// Secure Chatbot API - Server-side OpenAI Integration
// This file handles all OpenAI API calls securely

// Enable CORS for your domain (adjust as needed)
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// Only allow POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Get OpenAI API key from environment variable
$api_key = getenv('OPENAI_API_KEY');

// If not found in environment, try to load from .env file
if (!$api_key) {
    $env_file = __DIR__ . '/.env';
    if (file_exists($env_file)) {
        $env_vars = parse_ini_file($env_file);
        $api_key = $env_vars['OPENAI_API_KEY'] ?? null;
    }
}

// If still no API key, return error
if (!$api_key) {
    http_response_code(500);
    echo json_encode(['error' => 'API key not configured']);
    exit;
}

// Get and validate input
$input = json_decode(file_get_contents('php://input'), true);

if (!$input || !isset($input['message'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid input']);
    exit;
}

$user_message = trim($input['message']);
$conversation_history = $input['history'] ?? [];

// Validate message length
if (strlen($user_message) > 500) {
    http_response_code(400);
    echo json_encode(['error' => 'Message too long']);
    exit;
}

// Mortgage-specific system prompt
$system_prompt = "You are a professional mortgage broker assistant for Burnaby Home Loans in Burnaby, BC, Canada. 

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

Remember: You represent a professional mortgage brokerage. Be helpful but always recommend speaking with our licensed mortgage professionals for personalized advice.";

// Prepare messages for OpenAI
$messages = [
    ['role' => 'system', 'content' => $system_prompt]
];

// Add conversation history (limit to last 6 messages for context)
$recent_history = array_slice($conversation_history, -6);
foreach ($recent_history as $msg) {
    if (isset($msg['role']) && isset($msg['content'])) {
        $messages[] = [
            'role' => $msg['role'],
            'content' => $msg['content']
        ];
    }
}

// Add current user message
$messages[] = ['role' => 'user', 'content' => $user_message];

// Prepare OpenAI API request
$openai_data = [
    'model' => 'gpt-3.5-turbo',
    'messages' => $messages,
    'max_tokens' => 300,
    'temperature' => 0.7
];

// Make request to OpenAI
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'https://api.openai.com/v1/chat/completions');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($openai_data));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Authorization: Bearer ' . $api_key
]);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

// Handle OpenAI API response
if ($response === false || $http_code !== 200) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Sorry, I\'m having trouble connecting right now. Please try again in a moment, or call us at (604) 555-0123 for immediate assistance.'
    ]);
    exit;
}

$openai_response = json_decode($response, true);

if (!$openai_response || !isset($openai_response['choices'][0]['message']['content'])) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Sorry, I\'m having trouble processing your request. Please try again or contact us directly.'
    ]);
    exit;
}

// Return successful response
$ai_message = trim($openai_response['choices'][0]['message']['content']);

echo json_encode([
    'success' => true,
    'message' => $ai_message,
    'timestamp' => date('c')
]);
?> 