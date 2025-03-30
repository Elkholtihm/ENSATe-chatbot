document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const statusElement = document.getElementById('status');
    
    // Function to add a message to the chat
    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Check if the response contains sources (assuming format: answer\n\nSources: source1, source2)
        const sourcesSplit = text.split('\n\nSources: ');
        let messageContent = sourcesSplit[0];
        let sources = sourcesSplit.length > 1 ? sourcesSplit[1].split(', ') : [];
        
        messageDiv.innerHTML = messageContent;
        
        // Add sources if they exist
        if (sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            sourcesDiv.innerHTML = '<strong>Sources:</strong> ';
            
            sources.forEach(source => {
                const sourceLink = document.createElement('a');
                sourceLink.className = 'source';
                sourceLink.href = source;
                sourceLink.target = '_blank';
                sourceLink.textContent = source.split('/').slice(-1)[0]; // Show only last part of URL
                sourcesDiv.appendChild(sourceLink);
            });
            
            messageDiv.appendChild(sourcesDiv);
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = time;
        messageDiv.appendChild(timeDiv);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = '<div class="loading"></div>';
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to remove typing indicator
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Function to send message to RAG backend
    async function sendToRAG(question) {
        statusElement.textContent = "Processing your question...";
        showTypingIndicator();
        sendButton.disabled = true;
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: question
                })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            hideTypingIndicator();
            addMessage(data.response, false);
            statusElement.textContent = "Ready";
        } catch (error) {
            hideTypingIndicator();
            addMessage("Sorry, I encountered an error processing your request. Please try again.", false);
            statusElement.textContent = "Error occurred";
            console.error("RAG Error:", error);
        } finally {
            sendButton.disabled = false;
            userInput.focus();
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', function() {
        const question = userInput.value.trim();
        if (question) {
            addMessage(question, true);
            userInput.value = '';
            sendToRAG(question);
        }
    });
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const question = userInput.value.trim();
            if (question) {
                addMessage(question, true);
                userInput.value = '';
                sendToRAG(question);
            }
        }
    });
    
    // Focus the input field on load
    userInput.focus();
});