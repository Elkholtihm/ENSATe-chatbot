// Get DOM elements
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

// Get CSRF token from the form
function getCSRFToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}

// Initialize chat
function initChat() {
    // Load chat history from localStorage
    loadChatHistory();
    
    // Focus on input
    userInput.focus();
}

// Add message to chat
function addMessage(text, isUser = false, sources = null) {
    // Remove welcome message if exists
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    
    let messageHTML = `
        <div class="message-content">
            <p class="message-text">${formatMessage(text)}</p>
    `;
    
    // Add sources if available
    if (sources && sources.length > 0) {
        messageHTML += `
            <div class="message-sources">
                <strong><i class="fas fa-file-alt"></i> Sources:</strong>
                ${sources.map(source => {
                    const fileName = source.split('/').pop();
                    return `<span class="source-link" title="${source}">${fileName}</span>`;
                }).join('')}
            </div>
        `;
    }
    
    messageHTML += `</div>`;
    messageDiv.innerHTML = messageHTML;
    
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
    
    // Save to localStorage
    saveChatHistory();
}

// Format message text (convert newlines to <br>)
function formatMessage(text) {
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Show/hide typing indicator
function showTypingIndicator(show = true) {
    typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        scrollToBottom();
    }
}

// Enable/disable send button
function toggleSendButton(enabled = true) {
    sendBtn.disabled = !enabled;
    userInput.disabled = !enabled;
}

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = userInput.value.trim();
    if (!query) return;
    
    // Add user message
    addMessage(query, true);
    userInput.value = '';
    
    // Disable input and show typing indicator
    toggleSendButton(false);
    showTypingIndicator(true);
    
    try {
        // Send request to Django backend
        const response = await fetch('/query/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        showTypingIndicator(false);
        
        if (response.ok) {
            // Extract response text and sources
            let responseText = data.response;
            let sources = data.sources || [];
            
            // Remove sources from response text if they're included
            if (responseText.includes('\n\nSources:')) {
                responseText = responseText.split('\n\nSources:')[0];
            }
            
            // Add bot response
            addMessage(responseText, false, sources);
        } else {
            // Handle error
            addMessage(`Erreur: ${data.error || 'Une erreur est survenue'}`, false);
        }
        
    } catch (error) {
        console.error('Error:', error);
        showTypingIndicator(false);
        addMessage('Désolé, une erreur de connexion est survenue. Veuillez réessayer.', false);
    } finally {
        toggleSendButton(true);
        userInput.focus();
    }
});

// Clear chat function
function clearChat() {
    if (confirm('Êtes-vous sûr de vouloir effacer tout l\'historique du chat?')) {
        chatContainer.innerHTML = `
            <div class="welcome-message">
                <i class="fas fa-comment-dots"></i>
                <h2>Bienvenue!</h2>
                <p>Je suis votre assistant ENSA. Posez-moi des questions sur les emplois du temps, les cours, ou toute autre information.</p>
            </div>
        `;
        localStorage.removeItem('chatHistory');
    }
}

// Save chat history to localStorage
function saveChatHistory() {
    const messages = [];
    const messageElements = chatContainer.querySelectorAll('.message');
    
    messageElements.forEach(msg => {
        const isUser = msg.classList.contains('user');
        const text = msg.querySelector('.message-text').innerHTML;
        const sourcesDiv = msg.querySelector('.message-sources');
        let sources = [];
        
        if (sourcesDiv) {
            const sourceLinks = sourcesDiv.querySelectorAll('.source-link');
            sources = Array.from(sourceLinks).map(link => link.getAttribute('title'));
        }
        
        messages.push({ text, isUser, sources });
    });
    
    localStorage.setItem('chatHistory', JSON.stringify(messages));
}

// Load chat history from localStorage
function loadChatHistory() {
    const history = localStorage.getItem('chatHistory');
    
    if (history) {
        try {
            const messages = JSON.parse(history);
            messages.forEach(msg => {
                addMessage(msg.text, msg.isUser, msg.sources);
            });
        } catch (error) {
            console.error('Error loading chat history:', error);
            localStorage.removeItem('chatHistory');
        }
    }
}

// Handle Enter key (without Shift)
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Initialize chat on page load
document.addEventListener('DOMContentLoaded', initChat);