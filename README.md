# Burnaby Home Loans Chatbot

A web-based AI chatbot assistant for Burnaby Home Loans, built with Flask and OpenAI.

## Features

- Mortgage chatbot powered by OpenAI GPT
- Secure API key management with `.env` file
- Ready for deployment on Render
- Frontend and backend separation

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/burnabyhomeloans.git
   cd burnabyhomeloans
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```

4. Run the Flask app:
   ```
   python app.py
   ```

5. Visit [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health) to check the server status.

## Deployment

- Deploy to [Render](https://render.com/) or your preferred cloud platform.
- Set the `OPENAI_API_KEY` as an environment variable in your deployment dashboard.

## API

- **POST** `/chatbot-api`
  - Request body: `{ "message": "Your question here" }`
  - Response: `{ "message": "...", "success": true, "timestamp": "..." }`

## License

MIT

---

*Feel free to customize this README for your project!*
