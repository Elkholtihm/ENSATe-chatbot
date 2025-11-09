# chat_app/urls.py

from django.urls import path
from . import views

app_name = 'chat_app'

urlpatterns = [
    # ========================================================================
    # Public Pages
    # ========================================================================
    path('', views.landing_page, name='landing'),
    
    # ========================================================================
    # Authentication
    # ========================================================================
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # ========================================================================
    # Chatbot (Protected)
    # ========================================================================
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('api/query/', views.handle_query, name='handle_query'),
    
    # ========================================================================
    # User Profile & History (Protected)
    # ========================================================================
    path('profile/', views.profile_view, name='profile'),
    path('history/', views.history_view, name='history'),
    path('history/delete/', views.delete_history, name='delete_history'),
    path('change-password/', views.change_password_view, name='change_password'),
    
    # ========================================================================
    # API Endpoints (Optional - for AJAX)
    # ========================================================================
    path('api/history/', views.get_chat_history_json, name='get_history_json'),

    
    path('query/', views.handle_query, name='handle_query'), 
]