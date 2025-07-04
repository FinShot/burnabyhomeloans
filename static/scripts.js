// Professional Mortgage Website JavaScript
// ===== SECURE CHATBOT FUNCTIONALITY =====
// Uses server-side API to keep OpenAI key secure

class MortgageChatbot {
    constructor() {
        this.messages = [];
        this.isMinimized = true;
        this.isLoading = false;
        this.apiEndpoint = '/chatbot-api'; // Use relative URL for compatibility
        this.qualificationState = {}; // Track qualification flow state
        this.leadData = {};           // Track lead data
        this.initializeElements();
        this.bindEvents();
        this.addWelcomeMessage();
        this.quickActions = [
            { label: 'Current Rates', message: 'current rates' },
            { label: 'Calculator', message: 'calculator' },
            { label: 'Apply Now', message: 'apply now' }
        ];
    }

    initializeElements() {
        this.chatContainer = document.querySelector('.chatbot-container');
        this.chatMessages = document.querySelector('.chat-messages');
        this.chatInput = document.querySelector('.chat-input');
        this.chatSendBtn = document.querySelector('.chat-send-btn');
        this.toggleBtn = document.querySelector('.toggle-btn');
        this.chatHeader = document.querySelector('.chat-header');
        this.collapsedInput = document.querySelector('.collapsed-chat-input-field');
        this.collapsedSendBtn = document.querySelector('.collapsed-send-btn');
        this.quickActions = document.querySelectorAll('.quick-action');
        
        // Initialize toggle button text
        if (this.toggleBtn) {
            this.toggleBtn.textContent = this.isMinimized ? '+' : '−';
        }
    }

    bindEvents() {
        // Toggle chatbot
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent header click
                this.toggleChatbot();
            });
        }
        if (this.chatHeader) {
            this.chatHeader.addEventListener('click', () => this.toggleChatbot());
        }

        // Send message events
        if (this.chatSendBtn) {
            this.chatSendBtn.addEventListener('click', () => this.sendMessage());
        }
        if (this.collapsedSendBtn) {
            this.collapsedSendBtn.addEventListener('click', () => this.sendMessage(true));
        }
        
        // Enter key to send
        if (this.chatInput) {
            this.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (this.collapsedInput) {
            this.collapsedInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage(true);
                }
            });
        }

        // Quick actions
        this.quickActions.forEach(action => {
            action.addEventListener('click', () => {
                const message = action.textContent.trim();
                this.sendMessage(false, message);
            });
        });
    }

    toggleChatbot() {
        this.isMinimized = !this.isMinimized;
        this.chatContainer.classList.toggle('minimized', this.isMinimized);
        
        // Update toggle button text
        if (this.toggleBtn) {
            this.toggleBtn.textContent = this.isMinimized ? '+' : '−';
        }
        
        if (!this.isMinimized) {
            this.chatInput.focus();
        }
    }

    addWelcomeMessage() {
        const initialBotMessage = `Hi there! I'm your personal mortgage AI Chat Agent :) <br>Would you like to see how much you qualify for today? Or is there something else I can help you with?`;
        const welcomeMessage = {
            role: 'assistant',
            content: initialBotMessage
        };
        this.displayMessage(welcomeMessage);
    }

    async sendMessage(fromCollapsed = false, customMessage = null) {
        if (this.isLoading) return;

        const input = fromCollapsed ? this.collapsedInput : this.chatInput;
        const message = customMessage || input.value.trim();
        
        if (!message) return;

        // Clear input
        if (!customMessage) {
            input.value = '';
        }

        // If sending from collapsed state, expand chatbot
        if (fromCollapsed) {
            this.toggleChatbot();
        }

        // Add user message
        const userMessage = { role: 'user', content: message };
        this.messages.push(userMessage);
        this.displayMessage(userMessage);

        // Show loading
        this.setLoading(true);

        try {
            // Get AI response from secure Python Flask API on Render
            const response = await this.getAIResponse(message);
            const assistantMessage = response; // Use the full response object
            this.messages.push(assistantMessage);
            this.displayMessage(assistantMessage);
        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage = {
                role: 'assistant',
                content: "I'm sorry, I'm having trouble connecting right now. Please try again in a moment, or feel free to call us at (604) 555-0123 for immediate assistance."
            };
            this.displayMessage(errorMessage);
        } finally {
            this.setLoading(false);
        }
    }

    async getAIResponse(userMessage) {
        // Send request to secure Python Flask API on Render
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: userMessage,
                history: this.messages.slice(-6),
                qualification_state: this.qualificationState, // Send state
                lead_data: this.leadData                      // Send lead data
            })
        });

        if (!response.ok) {
            throw new Error(`Render API request failed: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        // Update state from backend response
        if (data.qualification_state) {
            this.qualificationState = data.qualification_state;
        }
        if (data.lead_data) {
            this.leadData = data.lead_data;
        }
        // Reset state after flow completes
        if (this.qualificationState && this.qualificationState.completed) {
            this.qualificationState = {};
            this.leadData = {};
        }

        return data; // Return the full response object
    }

    displayMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${message.role}-message`;
        
        if (message.role === 'assistant') {
            messageDiv.innerHTML = `
                <div class="bot-avatar">🏠</div>
                <div class="message-content">${this.formatMessage(message.content)}</div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">${this.formatMessage(message.content)}</div>
            `;
        }

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Basic formatting for better readability
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
            .replace(/\n/g, '<br>') // Line breaks
            .replace(/(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})/g, '<a href="tel:$1">$1</a>'); // Phone numbers
    }

    setLoading(loading) {
        this.isLoading = loading;
        this.chatSendBtn.disabled = loading;
        this.collapsedSendBtn.disabled = loading;
        
        if (loading) {
            // Show typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-message bot-message typing-indicator';
            typingDiv.innerHTML = `
                <div class="bot-avatar">🏠</div>
                <div class="message-content">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            this.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();
        } else {
            // Remove typing indicator
            const typingIndicator = this.chatMessages.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// ===== SMOOTH SCROLLING =====
function scrollToSection(sectionId) {
    const target = document.getElementById(sectionId);
    if (target) {
        target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== MORTGAGE CALCULATOR =====
function calculatePayment() {
    // Get values from the actual form fields
    const purchasePrice = parseFloat(document.getElementById('purchasePrice').value) || 0;
    const downPayment = parseFloat(document.getElementById('downPayment').value) || 0;
    const interestRate = parseFloat(document.getElementById('interestRate').value) || 0;
    const amortization = parseInt(document.getElementById('amortization').value) || 25;
    
    if (purchasePrice <= 0 || downPayment < 0 || interestRate <= 0) {
        alert('Please enter valid values for all fields.');
        return;
    }
    
    const loanAmount = purchasePrice - downPayment;
    const monthlyRate = interestRate / 100 / 12;
    const numberOfPayments = amortization * 12;
    
    const monthlyPayment = loanAmount * 
        (monthlyRate * Math.pow(1 + monthlyRate, numberOfPayments)) / 
        (Math.pow(1 + monthlyRate, numberOfPayments) - 1);
    
    const totalPayment = monthlyPayment * numberOfPayments;
    const totalInterest = totalPayment - loanAmount;
    
    document.getElementById('monthlyPayment').textContent = 
        `$${monthlyPayment.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    // Show insights
    const insights = document.getElementById('calc-insights');
    insights.innerHTML = `
        <p><strong>Loan Amount:</strong> $${loanAmount.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        <p><strong>Total Interest:</strong> $${totalInterest.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        <p><strong>Total Paid:</strong> $${totalPayment.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        <p><em>💡 Tip: Making bi-weekly payments instead of monthly can save you thousands in interest!</em></p>
    `;
    
    document.querySelector('.calculation-result').style.display = 'block';
}

function calculateMortgage() {
    const loanAmount = parseFloat(document.getElementById('loanAmount').value) || 0;
    const interestRate = parseFloat(document.getElementById('interestRate').value) || 0;
    const loanTerm = parseInt(document.getElementById('loanTerm').value) || 0;
    
    if (loanAmount <= 0 || interestRate <= 0 || loanTerm <= 0) {
        alert('Please enter valid values for all fields.');
        return;
    }
    
    const monthlyRate = interestRate / 100 / 12;
    const numberOfPayments = loanTerm * 12;
    
    const monthlyPayment = loanAmount * 
        (monthlyRate * Math.pow(1 + monthlyRate, numberOfPayments)) / 
        (Math.pow(1 + monthlyRate, numberOfPayments) - 1);
    
    const totalPayment = monthlyPayment * numberOfPayments;
    const totalInterest = totalPayment - loanAmount;
    
    document.getElementById('monthlyPayment').textContent = 
        `$${monthlyPayment.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    
    // Show insights
    const insights = document.querySelector('.calc-insights');
    insights.innerHTML = `
        <p><strong>Total Interest:</strong> $${totalInterest.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        <p><strong>Total Paid:</strong> $${totalPayment.toLocaleString('en-CA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        <p><em>💡 Tip: Making bi-weekly payments instead of monthly can save you thousands in interest!</em></p>
    `;
    
    document.querySelector('.calculation-result').style.display = 'block';
}

// ===== FORM VALIDATION =====
function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#ef4444';
            isValid = false;
        } else {
            input.style.borderColor = '#d1d5db';
        }
    });
    
    return isValid;
}

// ===== MOBILE NAVIGATION TOGGLE =====
function initializeMobileNav() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('nav-menu-active');
            navToggle.classList.toggle('nav-toggle-active');
        });
        
        // Close menu when clicking on a link
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('nav-menu-active');
                navToggle.classList.remove('nav-toggle-active');
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('nav-menu-active');
                navToggle.classList.remove('nav-toggle-active');
            }
        });
    }
}

// ===== INITIALIZE WHEN DOM IS LOADED =====
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile navigation
    initializeMobileNav();
    
    // Initialize secure chatbot
    window.mortgageChatbot = new MortgageChatbot();
    
    // Add calculator button event
    const calcButton = document.querySelector('.calculate-btn');
    if (calcButton) {
        calcButton.addEventListener('click', calculateMortgage);
    }
    
    // Add form submit handlers
    const applicationForm = document.querySelector('.application-form');
    if (applicationForm) {
        applicationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (validateForm('applicationForm')) {
                alert('Thank you! Your application has been submitted. We\'ll contact you within 24 hours.');
                this.reset();
            }
        });
    }
    
    const contactForm = document.querySelector('.contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (validateForm('contactForm')) {
                alert('Thank you for your message! We\'ll get back to you soon.');
                this.reset();
            }
        });
    }
});

// === DYNAMIC RATE FETCHING FOR PUBLIC SITE ===
document.addEventListener('DOMContentLoaded', async function() {
  try {
    const response = await fetch('/api/rates');
    if (!response.ok) return;
    const data = await response.json();
    // Update 5-year fixed rate
    document.querySelectorAll('.rate-number-5yr, .stat-number-5yr, .table-rate-5yr').forEach(el => {
      el.textContent = data.fixed_rate ? `${parseFloat(data.fixed_rate).toFixed(2)}%` : '';
    });
    // Update variable rate
    document.querySelectorAll('.rate-number-var, .stat-number-var, .table-rate-var').forEach(el => {
      el.textContent = data.variable_rate ? `${parseFloat(data.variable_rate).toFixed(2)}%` : '';
    });
    // Update 3-year fixed rate
    document.querySelectorAll('.rate-number-3yr, .stat-number-3yr, .table-rate-3yr').forEach(el => {
      el.textContent = data.three_year_fixed_rate ? `${parseFloat(data.three_year_fixed_rate).toFixed(2)}%` : '';
    });
    // Update any summary text (example)
    const summary = document.getElementById('rate-summary-text');
    if (summary) {
      summary.textContent = `5-year fixed: ${data.fixed_rate}% APR | Variable: ${data.variable_rate}% APR | 3-year fixed: ${data.three_year_fixed_rate}% APR`;
    }
  } catch (e) {
    // Optionally log error
  }
});
