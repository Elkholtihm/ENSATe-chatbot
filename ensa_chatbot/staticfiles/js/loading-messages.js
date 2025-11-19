const loadingMessages = [
    "Même les robots ont besoin de réfléchir... 🤔",
    "Personne n'aime attendre, mais ça vaut le coup! ⏳",
    "Je consulte ma bibliothèque neuronale... 📚",
    "La patience est une vertu, même pour les IA 🧘",
    "En train de philosopher sur votre question... 💭",
    "Rome ne s'est pas construite en un jour, ni cette réponse ⚡",
    "Le savoir prend du temps à distiller... 🌟",
    "Chaque seconde d'attente rend la réponse plus sage 🦉",
    "Je parcours des milliers de documents pour vous... 📖",
    "Même Einstein réfléchissait avant de répondre 🧠",
    "Votre patience sera récompensée... 🎁",
    "Je cherche la perle rare dans l'océan de données 🌊",
    "Transformation de données en sagesse... ✨",
    "Le meilleur arrive à ceux qui attendent 🎯"
];

function getRandomLoadingMessage() {
    return loadingMessages[Math.floor(Math.random() * loadingMessages.length)];
}