// ============================================================================
// ENSA Chatbot - Modern Chat Interface JavaScript (FIXED)
// ============================================================================

// Global state
let chatHistory = [];
let currentChatId = null;
let isTyping = false;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat initialized for user:', window.username);
    initializeChat();
    setupEventListeners();
    loadChatHistory();
    setupTextareaAutoResize();
});

function initializeChat() {
    focusInput();
}

function addMessageActions(messageDiv, originalQuery, responseText) {
    const contentDiv = messageDiv.querySelector('.message-content');
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    actionsDiv.innerHTML = `
        <button class="message-action-btn" onclick="copyMessage(this)" title="Copier">
            <i class="fas fa-copy"></i> Copier
        </button>
        <button class="message-action-btn" onclick="retryMessage('${escapeHtml(originalQuery)}')" title="Régénérer">
            <i class="fas fa-redo"></i> Régénérer
        </button>
        <button class="message-action-btn" onclick="provideFeedback(this, 'good')" title="Bonne réponse">
            <i class="fas fa-thumbs-up"></i>
        </button>
        <button class="message-action-btn" onclick="provideFeedback(this, 'bad')" title="Mauvaise réponse">
            <i class="fas fa-thumbs-down"></i>
        </button>
    `;
    
    // Store response text for copy function
    actionsDiv.dataset.responseText = responseText;
    
    contentDiv.appendChild(actionsDiv);
}

function copyMessage(button) {
    const actionsDiv = button.closest('.message-actions');
    const text = actionsDiv.dataset.responseText;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copié!';
        button.classList.add('active');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('active');
        }, 2000);
    }).catch(err => {
        console.error('Erreur copie:', err);
        alert('Erreur lors de la copie');
    });
}

function retryMessage(query) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = query;
        handleInputChange({ target: input });
        
        // Auto-submit
        const form = document.getElementById('chatForm');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }
}

async function provideFeedback(button, type) {
    const allButtons = button.parentElement.querySelectorAll('.message-action-btn');
    allButtons.forEach(btn => {
        if (btn.querySelector('.fa-thumbs-up') || btn.querySelector('.fa-thumbs-down')) {
            btn.classList.remove('active');
        }
    });
    
    button.classList.add('active');
    
    // Get the message content to identify which response this is for
    const messageDiv = button.closest('.message');
    const messageText = messageDiv.querySelector('.message-text').textContent;
    
    // Send feedback to backend
    try {
        const response = await fetch('/api/feedback/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrfToken
            },
            body: JSON.stringify({
                chat_id: currentChatId,
                feedback_type: type,
                message_text: messageText.substring(0, 200) // First 200 chars for identification
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save feedback');
        }
        
        console.log('Feedback saved:', type);
    } catch (error) {
        console.error('Error saving feedback:', error);
    }
    
    const message = type === 'good' ? 'Merci pour votre retour positif!' : 'Merci, nous allons améliorer nos réponses.';
    
    const toast = document.createElement('div');
    toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #10b981; color: white; padding: 12px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 9999; animation: slideIn 0.3s ease;';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function getRandomLoadingMessage() {
    const messages = [
        'Réflexion en cours...',
        'Analyse de votre question...',
        'Recherche d\'informations...',
        'Génération de la réponse...',
        'Un instant...',
        'Traitement en cours...'
    ];
    return messages[Math.floor(Math.random() * messages.length)];
}

// Make functions global
window.copyMessage = copyMessage;
window.retryMessage = retryMessage;
window.provideFeedback = provideFeedback;

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Form submission
    const form = document.getElementById('chatForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }

    // Input changes
    const input = document.getElementById('userInput');
    if (input) {
        input.addEventListener('input', handleInputChange);
        input.addEventListener('keydown', handleKeyDown);
    }

    // Prevent sidebar close on click inside
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    // Close user menu when clicking outside
    document.addEventListener('click', function(e) {
        const menu = document.getElementById('userMenu');
        const menuBtn = document.querySelector('.menu-btn');
        
        if (menu && menuBtn) {
            if (!menu.contains(e.target) && !menuBtn.contains(e.target)) {
                menu.style.display = 'none';
            }
        }
    });
}

function setupTextareaAutoResize() {
    const textarea = document.getElementById('userInput');
    if (!textarea) return;

    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// ============================================================================
// INPUT HANDLING
// ============================================================================

function handleInputChange(e) {
    const input = e.target;
    const sendBtn = document.getElementById('sendBtn');
    const charCount = document.getElementById('charCount');
    
    // Update character count
    if (charCount) {
        charCount.textContent = input.value.length;
    }
    
    // Enable/disable send button
    if (sendBtn) {
        sendBtn.disabled = input.value.trim().length === 0;
    }
}

function handleKeyDown(e) {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const form = document.getElementById('chatForm');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }
}

// ============================================================================
// FORM SUBMISSION
// ============================================================================
async function handleSubmit(e) {
    e.preventDefault();
    
    if (isTyping) return;
    
    const input = document.getElementById('userInput');
    const query = input.value.trim();
    
    if (!query) return;

    // Switch to normal mode
    hideWelcomeScreen();
    addMessage('user', query);

    input.value = '';
    input.style.height = 'auto';
    handleInputChange({ target: input });
    
    showTypingIndicator();
    isTyping = true;
    
    try {
        // Create EventSource for streaming
        const response = await fetch('/query/stream/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrfToken
            },
            body: JSON.stringify({ query: query })
        });
        
        hideTypingIndicator();
        
        if (!response.ok) {
            throw new Error('Request failed');
        }
        
        // Create bot message container
        const messageDiv = createBotMessageContainer();
        const textElement = messageDiv.querySelector('.message-text');
        
        // Read stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';
        let sources = null;
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.content) {
                        fullText += data.content;
                        textElement.innerHTML = renderMarkdown(fullText);
                        scrollToBottom();
                    }
                    
                    if (data.sources) {
                        sources = data.sources;
                    }

                    if (data.done) {
                        // Add sources if available
                        if (sources && sources.length > 0) {
                            const contentDiv = messageDiv.querySelector('.message-content');
                            const sourcesDiv = document.createElement('div');
                            sourcesDiv.className = 'message-sources';
                            sourcesDiv.innerHTML = `
                                <strong>📚 Sources:</strong>
                                ${sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}
                            `;
                            contentDiv.appendChild(sourcesDiv);
                        }
                        
                        highlightCodeBlocks(messageDiv);
                        addCopyButtons(messageDiv);
                        addMessageActions(messageDiv, query, fullText);
                    }
                }
            }
        }
        
        isTyping = false;
        loadChatHistory();
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        isTyping = false;
        addMessage('bot', 'Désolé, une erreur s\'est produite.');
    }
    
    focusInput();
}

function createBotMessageContainer() {
    const container = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">ENSA Chatbot</span>
                <span class="message-time">${timeStr}</span>
            </div>
            <div class="message-text"></div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv;
}
// ============================================================================
// MESSAGE DISPLAY WITH MARKDOWN
// ============================================================================

function addMessage(role, text, sources = null) {
    const container = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    
    const avatar = role === 'user' 
        ? window.username.charAt(0).toUpperCase()
        : '🤖';
    
    const authorName = role === 'user' ? window.username : 'ENSA Chatbot';
    
    // Render markdown for bot messages
    const messageContent = role === 'bot' ? renderMarkdown(text) : escapeHtml(text);
    
    let html = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${timeStr}</span>
            </div>
            <div class="message-text">${messageContent}</div>
    `;
    
    if (sources && sources.length > 0) {
        html += `
            <div class="message-sources">
                <strong>📚 Sources:</strong>
                ${sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}
            </div>
        `;
    }
    
    html += `</div>`;
    messageDiv.innerHTML = html;
    
    container.appendChild(messageDiv);
    
    // Highlight code blocks
    if (role === 'bot') {
        highlightCodeBlocks(messageDiv);
        addCopyButtons(messageDiv);
    }
    
    scrollToBottom();
    return messageDiv;
}

async function addMessageWithTyping(role, text, sources = null) {
    const container = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    
    const avatar = '🤖';
    const authorName = 'ENSA Chatbot';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${timeStr}</span>
            </div>
            <div class="message-text"></div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    const textElement = messageDiv.querySelector('.message-text');
    
    // Type out with progressive rendering
    await typeTextWithMarkdown(textElement, text);
    
    // Highlight code blocks after typing
    highlightCodeBlocks(messageDiv);
    addCopyButtons(messageDiv);
    
    // Add sources
    if (sources && sources.length > 0) {
        const contentDiv = messageDiv.querySelector('.message-content');
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'message-sources';
        sourcesDiv.innerHTML = `
            <strong>📚 Sources:</strong>
            ${sources.map(s => `<span class="source-tag">${escapeHtml(s)}</span>`).join('')}
        `;
        contentDiv.appendChild(sourcesDiv);
    }
    
    scrollToBottom();
}

// ============================================================================
// MARKDOWN RENDERING
// ============================================================================

function renderMarkdown(text) {
    if (!text) return '';
    
    // Configure marked options
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        mangle: false
    });
    
    return marked.parse(text);
}

async function typeTextWithMarkdown(element, text, speed = 15) {
    // Split by sentences for smoother rendering
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    let accumulated = '';
    
    for (const sentence of sentences) {
        accumulated += sentence;
        element.innerHTML = renderMarkdown(accumulated);
        scrollToBottom();
        await new Promise(resolve => setTimeout(resolve, speed * sentence.length));
    }
    
    // Final render
    element.innerHTML = renderMarkdown(text);
}

// ============================================================================
// CODE HIGHLIGHTING & COPY
// ============================================================================

function highlightCodeBlocks(messageElement) {
    const codeBlocks = messageElement.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        hljs.highlightElement(block);
    });
}

function addCopyButtons(messageElement) {
    const codeBlocks = messageElement.querySelectorAll('pre');
    
    codeBlocks.forEach(pre => {
        // Wrap in container
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
        
        // Add copy button
        const button = document.createElement('button');
        button.className = 'code-copy-btn';
        button.innerHTML = '<i class="fas fa-copy"></i> Copier';
        button.onclick = () => copyCode(button, pre);
        wrapper.appendChild(button);
    });
}

function copyCode(button, pre) {
    const code = pre.querySelector('code');
    const text = code.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        button.innerHTML = '<i class="fas fa-check"></i> Copié!';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-copy"></i> Copier';
            button.classList.remove('copied');
        }, 2000);
    });
}
// ============================================================================
// TYPING INDICATOR
// ============================================================================

function showTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        // Get random message
        const message = getRandomLoadingMessage();
        
        // Update or create message element
        let messageEl = indicator.querySelector('.typing-message');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.className = 'typing-message';
            indicator.appendChild(messageEl);
        }
        messageEl.textContent = message;
        
        indicator.style.display = 'flex';
        scrollToBottom();
    }
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// ============================================================================
// CHAT HISTORY SIDEBAR
// ============================================================================

async function loadChatHistory() {
    try {
        const response = await fetch('/api/history/?limit=50');
        
        if (!response.ok) {
            console.error('Failed to load history:', response.status);
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.chats) {
            displayChatHistory(data.chats);
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

function displayChatHistory(chats) {
    if (!chats || chats.length === 0) {
        // Show empty state
        ['todayChats', 'weekChats', 'monthChats'].forEach(id => {
            const section = document.getElementById(id);
            if (section) {
                section.innerHTML = '<div style="padding: 8px 12px; color: var(--text-secondary); font-size: 13px;">Aucune conversation</div>';
            }
        });
        return;
    }
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const todayChats = [];
    const weekChats = [];
    const monthChats = [];
    
    chats.forEach(chat => {
        const chatDate = new Date(chat.created_at);
        if (chatDate >= today) {
            todayChats.push(chat);
        } else if (chatDate >= weekAgo) {
            weekChats.push(chat);
        } else if (chatDate >= monthAgo) {
            monthChats.push(chat);
        }
    });
    
    populateHistorySection('todayChats', todayChats);
    populateHistorySection('weekChats', weekChats);
    populateHistorySection('monthChats', monthChats);
}

function populateHistorySection(sectionId, chats) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    
    section.innerHTML = '';
    
    if (chats.length === 0) {
        section.innerHTML = '<div style="padding: 8px 12px; color: var(--text-secondary); font-size: 13px;">Aucune conversation</div>';
        return;
    }
    
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <i class="fas fa-message"></i>
            <span class="history-item-text">${escapeHtml(chat.query)}</span>
        `;
        item.onclick = () => loadChat(chat);
        section.appendChild(item);
    });
}

async function loadChat(chat) {
    try {
        console.log('Loading chat data:', chat); // DEBUG
        
        // Hide welcome screen
        hideWelcomeScreen();
        
        // Clear current messages
        const container = document.getElementById('chatContainer');
        const messages = container.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        
        // Verify we have the data
        if (!chat || !chat.query || !chat.response) {
            console.error('Invalid chat data:', chat);
            addMessage('bot', 'Erreur: données de conversation invalides.');
            return;
        }
        
        console.log('Adding user message:', chat.query); // DEBUG
        // Add the original query as user message
        addMessage('user', chat.query);
        
        // Parse sources
        let sources = null;
        if (chat.sources && chat.sources.trim() !== '') {
            console.log('Raw sources:', chat.sources); // DEBUG
            // Split by comma and get just the filename
            sources = chat.sources.split(',').map(s => {
                const trimmed = s.trim();
                // Get filename from full path (handle both / and \)
                const parts = trimmed.split(/[/\\]/);
                return parts[parts.length - 1];
            }).filter(s => s.length > 0);
            console.log('Parsed sources:', sources); // DEBUG
        }
        
        console.log('Adding bot message:', chat.response); // DEBUG
        // Add the response as bot message
        addMessage('bot', chat.response, sources && sources.length > 0 ? sources : null);
        
        // Update current chat ID
        currentChatId = chat.id;
        
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            toggleSidebar();
        }
        
        console.log('Chat loaded successfully!'); // DEBUG
        
    } catch (error) {
        console.error('Error loading chat:', error);
        addMessage('bot', 'Erreur lors du chargement de la conversation.');
    }
}

// ============================================================================
// UI HELPERS
// ============================================================================
function newChat() {
    const container = document.getElementById('chatContainer');
    const welcomeScreen = document.getElementById('welcomeScreen');
    
    // Clear messages
    const messages = container.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());
        
    // Clear input
    const input = document.getElementById('userInput');
    if (input) {
        input.value = '';
        input.style.height = 'auto';
        handleInputChange({ target: input });
    }
    
    // Reset state
    currentChatId = null;
    
    focusInput();
}

function hideWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcomeScreen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
}

function fillPrompt(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        handleInputChange({ target: input });
        input.focus();
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
    if (overlay) {
        overlay.classList.toggle('active');
    }
}

function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    if (menu) {
        const isVisible = menu.style.display === 'block';
        menu.style.display = isVisible ? 'none' : 'block';
    }
}

function openSettings() {
    window.location.href = '/profile/';
}

function shareChat() {
    alert('Fonctionnalité de partage à venir!');
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}

function scrollToTop() {
    const container = document.getElementById('chatContainer');
    if (container) {
        container.scrollTop = 0;
    }
}

function focusInput() {
    const input = document.getElementById('userInput');
    if (input) {
        setTimeout(() => input.focus(), 100);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 minute
    if (diff < 60000) {
        return 'À l\'instant';
    }
    
    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `Il y a ${minutes} min`;
    }
    
    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `Il y a ${hours}h`;
    }
    
    // Otherwise show date
    return date.toLocaleDateString('fr-FR', { 
        day: 'numeric', 
        month: 'short' 
    });
}

// ============================================================================
// KEYBOARD SHORTCUTS
// ============================================================================

document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Focus search/input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        focusInput();
    }
    
    // Ctrl/Cmd + N: New chat
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        newChat();
    }
    
    // Escape: Close sidebar on mobile & close user menu
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        const menu = document.getElementById('userMenu');
        
        if (sidebar && sidebar.classList.contains('active')) {
            toggleSidebar();
        }
        
        if (menu && menu.style.display === 'block') {
            menu.style.display = 'none';
        }
    }
});

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

window.newChat = newChat;
window.fillPrompt = fillPrompt;
window.toggleSidebar = toggleSidebar;
window.toggleUserMenu = toggleUserMenu;
window.openSettings = openSettings;
window.shareChat = shareChat;