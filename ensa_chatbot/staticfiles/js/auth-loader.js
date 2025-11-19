const authMessages = [
    "Loading like my life decisions... please wait 😂",
    "Hold on, the hamsters are running the server wheel 🐹💨",
    "Authenticating... or pretending to, who knows 🤷‍♂️",
    "BRB, asking the server nicely to let you in 🙏",
    "Processing your request like a Windows XP machine 💾",
    "Secure connection incoming, hopefully... 🤞🛡️",
    "Preparing your space, removing suspicious cookies 🍪😆"
];


function togglePassword(fieldId) {
    const field = document.getElementById(fieldId || 'password');
    const icon = field.nextElementSibling || document.querySelector('.password-toggle');
    
    if (field.type === 'password') {
        field.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        field.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            const loader = document.getElementById('authLoader');
            const message = document.getElementById('authMessage');
            if (loader && message) {
                message.textContent = authMessages[Math.floor(Math.random() * authMessages.length)];
                loader.style.display = 'flex';
            }
        });
    }
});