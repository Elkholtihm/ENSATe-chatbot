from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import os
from dotenv import load_dotenv

load_dotenv()

# Qdrant Configuration
QDRANT_USE_CLOUD = os.getenv("QDRANT_USE_CLOUD", "False").lower() == "true"

if QDRANT_USE_CLOUD:
    # Qdrant Cloud settings
    QDRANT_URL = os.getenv("QDRANT_URL")  # Full URL with https://
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_HOST = None
    QDRANT_PORT = None
else:
    # Local Qdrant settings
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_URL = None
    QDRANT_API_KEY = None

COLLECTION_NAME = "ENSA_chatbot"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / 'data' / 'data_final'

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here')

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chat_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ensa_chatbot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ensa_chatbot.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Casablanca'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom settings for the chatbot
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GROQ_API_KEY = [os.getenv("groq_api1"), os.getenv("groq_api_2"), os.getenv("groq_api_3"), os.getenv("groq_api_4"), 
                os.getenv("groq_api_5"), os.getenv("groq_api_6"), os.getenv("groq_api_7"), os.getenv("groq_api_8")]

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "ENSA_chatbot"


# Login/Logout URLs
LOGIN_URL = 'chat_app:login'
LOGIN_REDIRECT_URL = 'chat_app:chatbot'
LOGOUT_REDIRECT_URL = 'chat_app:landing'

# Optional: Configure messages framework tags for better styling
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}