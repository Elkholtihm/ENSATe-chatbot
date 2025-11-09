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
    
    // Hide welcome screen
    hideWelcomeScreen();
    
    // Add user message
    addMessage('user', query);
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    handleInputChange({ target: input });
    
    // Show typing indicator
    showTypingIndicator();
    isTyping = true;
    
    try {
        // Send request
        const response = await fetch('/api/query/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.csrfToken
            },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        hideTypingIndicator();
        isTyping = false;
        
        if (response.ok) {
            // Add bot response with typing effect
            await addMessageWithTyping('bot', data.response, data.sources);
            
            // Reload chat history sidebar
            loadChatHistory();
        } else {
            addMessage('bot', `Erreur: ${data.error || 'Une erreur est survenue'}`);
        }
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        isTyping = false;
        addMessage('bot', 'Désolé, une erreur s\'est produite. Veuillez réessayer.');
    }
    
    // Focus input
    focusInput();
}

// ============================================================================
// MESSAGE DISPLAY
// ============================================================================

function addMessage(role, text, sources = null) {
    const container = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    
    // Avatar
    const avatar = role === 'user' 
        ? window.username.charAt(0).toUpperCase()
        : '🤖';
    
    const authorName = role === 'user' ? window.username : 'ENSA Chatbot';
    
    let html = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${timeStr}</span>
            </div>
            <div class="message-text">${escapeHtml(text)}</div>
    `;
    
    // Add sources if provided
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
    
    // Type out the message
    await typeText(textElement, text);
    
    // Add sources after typing is complete
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

async function typeText(element, text, speed = 20) {
    const words = text.split(' ');
    
    for (let i = 0; i < words.length; i++) {
        element.textContent += (i > 0 ? ' ' : '') + words[i];
        scrollToBottom();
        
        // Faster typing for better UX
        await new Promise(resolve => setTimeout(resolve, speed));
    }
}

// ============================================================================
// TYPING INDICATOR
// ============================================================================

function showTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
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
    
    // Show welcome screen
    if (welcomeScreen) {
        welcomeScreen.style.display = 'block';
    }
    
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