from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.apps import apps
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json
import traceback
import re

from .utils import Search, GenerationGroq
from .models import ChatHistory, UserProfile


# ============================================================================
# Public Pages
# ============================================================================

@never_cache
def landing_page(request):
    """Landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('chat_app:chatbot')
    return render(request, 'chatbot/landing.html')


# ============================================================================
# Authentication Views
# ============================================================================

@never_cache
@require_http_methods(["GET", "POST"])
def signup_view(request):
    """Handle user registration with comprehensive validation"""
    if request.user.is_authenticated:
        return redirect('chat_app:chatbot')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validation
        errors = []
        
        # Check if all fields are provided
        if not all([username, email, password, password_confirm]):
            errors.append('Tous les champs sont obligatoires.')
        
        # Username validation
        if username:
            if len(username) < 3:
                errors.append('Le nom d\'utilisateur doit contenir au moins 3 caractères.')
            elif len(username) > 150:
                errors.append('Le nom d\'utilisateur est trop long (max 150 caractères).')
            elif not re.match(r'^[\w.@+-]+$', username):
                errors.append('Le nom d\'utilisateur ne peut contenir que des lettres, chiffres et @/./+/-/_')
            elif User.objects.filter(username__iexact=username).exists():
                errors.append('Ce nom d\'utilisateur existe déjà.')
        
        # Email validation
        if email:
            try:
                validate_email(email)
                if User.objects.filter(email__iexact=email).exists():
                    errors.append('Cet email est déjà utilisé.')
            except ValidationError:
                errors.append('Email invalide.')
        
        # Password validation
        if password:
            if len(password) < 6:
                errors.append('Le mot de passe doit contenir au moins 6 caractères.')
            elif len(password) > 128:
                errors.append('Le mot de passe est trop long (max 128 caractères).')
        
        # Password confirmation
        if password and password_confirm and password != password_confirm:
            errors.append('Les mots de passe ne correspondent pas.')
        
        # Display errors
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'chatbot/signup.html', {
                'username': username,
                'email': email,
            })
        
        # Create user
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Auto-login after registration
            login(request, user)
            
            messages.success(request, 'Inscription réussie! Bienvenue sur ENSA Chatbot.')
            return redirect('chat_app:chatbot')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'inscription: {str(e)}')
            return render(request, 'chatbot/signup.html')
    
    return render(request, 'chatbot/signup.html')


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login with validation"""
    if request.user.is_authenticated:
        return redirect('chat_app:chatbot')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validate inputs
        if not username or not password:
            messages.error(request, 'Veuillez remplir tous les champs.')
            return render(request, 'chatbot/login.html')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Bienvenue, {user.username}!')
                
                # Redirect to next page or chatbot
                next_page = request.GET.get('next', 'chat_app:chatbot')
                return redirect(next_page)
            else:
                messages.error(request, 'Votre compte est désactivé. Contactez l\'administrateur.')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'chatbot/login.html')


def logout_view(request):
    """Handle user logout"""
    username = request.user.username if request.user.is_authenticated else 'Utilisateur'
    logout(request)
    messages.success(request, f'Au revoir {username}! À bientôt.')
    return redirect('chat_app:landing')


# ============================================================================
# Chatbot Views (Protected)
# ============================================================================

@login_required(login_url='chat_app:login')
@never_cache
def chatbot_view(request):
    """Render the main chatbot page (requires authentication)"""
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'username': request.user.username,
        'user': request.user,
        'total_queries': profile.total_queries,
    }
    
    return render(request, 'chatbot/chatbot.html', context)

# its not used, just as a backup
@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='chat_app:login')
def handle_query(request):
    """Handle chatbot queries (requires authentication)"""
    try:
        # Parse request data
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({"error": "No query provided"}, status=400)
        
        # Limit query length
        if len(query) > 2000:
            return JsonResponse({"error": "Query too long (max 2000 characters)"}, status=400)
        
        print(f"[{request.user.username}] Query: {query}")
        
        # Get chatbot components from app config
        chatbot_config = apps.get_app_config('chat_app')
        client = chatbot_config.client
        collection_name = chatbot_config.collection_name
        embedding_model = chatbot_config.embedding_model
        
        # Perform search
        results, sources = Search(query, client, collection_name, embedding_model, groq_key=settings.GROQ_API_KEY, mode="multi", top_k=3)

        # Process sources
        source_data = []
        valid_sources = []
        
        for source in sources:
            if source is None:
                continue
            source = source.replace("\\", "/")
            try:
                if source.endswith(".json"):
                    with open(source, 'r', encoding='utf-8') as f:
                        data_content = json.load(f)
                        source_data.append(data_content)
                        valid_sources.append(source)
                elif source.endswith(".txt"):
                    with open(source, "r", encoding="utf-8") as f:
                        data_content = f.read()
                        source_data.append(data_content)
                        valid_sources.append(source)
            except FileNotFoundError:
                print(f"[ERROR] Source file not found: {source}")
                continue
            except Exception as e:
                print(f"[ERROR] Error loading source {source}: {str(e)}")
                continue
        
        # Generate response
        if results:
            response = GenerationGroq(
                query, 
                results, 
                settings.GROQ_API_KEY, 
                temperature=0.6, 
                max_tokens=1500
            )

            #print(f"[{request.user.username}] Response: {response}")
            
            if response is None:
                raise ValueError("GenerationGroq returned None response")
            
            # Format sources for display (just filenames)
            formatted_sources = [s.split('/')[-1] for s in valid_sources]
            
            # Save to chat history
            try:
                chat_history = ChatHistory.objects.create(
                    user=request.user,
                    query=query,
                    response=response,
                    sources=', '.join(valid_sources)
                )
                
                # Update user profile
                profile = request.user.profile
                profile.total_queries = request.user.chat_history.count()
                profile.save()
                
                print(f"[{request.user.username}] Chat saved (ID: {chat_history.id})")
            except Exception as e:
                print(f"[ERROR] Failed to save chat history: {str(e)}")
            
            return JsonResponse({
                "response": response,
                "success": True
            })
        else:
            error_message = "Désolé, je n'ai pas trouvé d'informations pertinentes pour répondre à votre question."
            
            # Still save the query
            try:
                ChatHistory.objects.create(
                    user=request.user,
                    query=query,
                    response=error_message,
                    sources=""
                )
                
                # Update user profile
                profile = request.user.profile
                profile.total_queries = request.user.chat_history.count()
                profile.save()
            except Exception as e:
                print(f"[ERROR] Failed to save chat history: {str(e)}")
            
            return JsonResponse({
                "response": error_message,
                "sources": [],
                "success": False
            })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"[ERROR] Exception in handle_query:")
        traceback.print_exc()
        return JsonResponse({
            "error": "Une erreur s'est produite lors du traitement de votre question.",
            "details": str(e) if settings.DEBUG else None
        }, status=500)

from django.http import StreamingHttpResponse

@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='chat_app:login')
def handle_query_stream(request):
    """Stream chatbot responses in real-time like Claude/ChatGPT"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({"error": "No query provided"}, status=400)
        
        if len(query) > 2000:
            return JsonResponse({"error": "Query too long"}, status=400)
        
        print(f"[{request.user.username}] Streaming query: {query}")
        
        # Get components
        chatbot_config = apps.get_app_config('chat_app')
        client = chatbot_config.client
        collection_name = chatbot_config.collection_name
        embedding_model = chatbot_config.embedding_model
        
        # Search
        results, sources = Search(query, client, collection_name, embedding_model, 
                                 groq_keys=settings.GROQ_API_KEY, mode="multi", top_k=3)
        print(F"-------resuuuuuuuuuuuuuults---------------{results}")
        
        # Process sources
        valid_sources = []
        for source in sources:
            if source is None:
                continue
            source = source.replace("\\", "/")
            try:
                if source.endswith((".json", ".txt")):
                    valid_sources.append(source)
            except:
                continue
        
        # Return streaming response
        return StreamingHttpResponse(
            generate_stream(request.user, query, results, valid_sources, settings.GROQ_API_KEY),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Streaming error: {e}")
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

from groq import Groq
from groq import APIError, RateLimitError
import json
def generate_stream(user, query, results, valid_sources, groq_api_keys):
    """Generator for streaming response with multiple API key fallback"""
    
    if not results:
        error_msg = "Désolé, je n'ai pas trouvé d'informations pertinentes."
        yield f"data: {json.dumps({'content': error_msg, 'done': True})}\n\n"
        return
    
    # Ensure groq_api_keys is a list
    if isinstance(groq_api_keys, str):
        groq_api_keys = [groq_api_keys]
    
    context = results
    prompt = f""" Vous êtes un assistant utile. vous êtes integrer dans un system RAG, Utilisez le contexte suivant pour répondre à la question de l'utilisateur de manière COMPLÈTE et DÉTAILLÉE en français. IMPORTANT - FORMAT DE RÉPONSE: - Utilisez le format Markdown pour structurer votre réponse - Utilisez des titres (##, ###) pour organiser les sections - Utilisez des listes à puces ou numérotées pour les énumérations - Utilisez des tableaux Markdown pour présenter des données structurées - Mettez en **gras** les informations importantes - Utilisez des `backticks` pour le code ou les termes techniques - Assurez-vous de terminer complètement vos phrases et tableaux svp évitez de parler hors contexte. Si vous ne connaissez pas la réponse, dites simplement que vous ne savez pas. Utilisez seulement le contexte pertinent selon la question posée. Contexte: {context} Question: {query} Réponse:"""

    # Try each API key until one works
    for key_index, api_key in enumerate(groq_api_keys):
        try:
            groq_client = Groq(api_key=api_key)
            
            print(f"[INFO] Attempting with API key #{key_index + 1}")
            
            # Stream from Groq
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.6,
                max_completion_tokens=1500,
                stream=True
            )
            
            full_response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # Send each token/word individually for smoother effect
                    yield f"data: {json.dumps({'content': content, 'type': 'token'})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Send sources separately
            formatted_sources = [s.split('/')[-1] for s in valid_sources if s]
            yield f"data: {json.dumps({'sources': formatted_sources, 'type': 'sources'})}\n\n"
            
            # Save to database
            try:
                from django.apps import apps
                ChatHistory = apps.get_model('yourapp', 'ChatHistory')
                
                ChatHistory.objects.create(
                    user=user,
                    query=query,
                    response=full_response,
                    sources=', '.join(valid_sources)
                )
                profile = user.profile
                profile.total_queries = user.chat_history.count()
                profile.save()
                print(f"[{user.username}] Streamed chat saved (API key #{key_index + 1})")
            except Exception as e:
                print(f"[ERROR] Failed to save: {e}")
            
            # Success - exit the retry loop
            return
        
        except RateLimitError as e:
            print(f"[WARNING] Rate limit hit on API key #{key_index + 1}")
            
            # If this isn't the last key, try the next one
            if key_index < len(groq_api_keys) - 1:
                print(f"[INFO] Switching to next API key...")
                continue
            else:
                # All keys exhausted
                error_msg = "Désolé, tous les clés API ont atteint leur limite. Veuillez réessayer plus tard."
                yield f"data: {json.dumps({'content': error_msg, 'done': True})}\n\n"
                return
        
        except APIError as e:
            print(f"[ERROR] API error on key #{key_index + 1}: {str(e)}")
            
            # If this isn't the last key, try the next one
            if key_index < len(groq_api_keys) - 1:
                print(f"[INFO] Switching to next API key...")
                continue
            else:
                error_msg = f"Erreur API: {str(e)}"
                yield f"data: {json.dumps({'content': error_msg, 'done': True})}\n\n"
                return
        
        except Exception as e:
            print(f"[ERROR] Stream generation error on key #{key_index + 1}: {e}")
            
            # If this isn't the last key, try the next one
            if key_index < len(groq_api_keys) - 1:
                print(f"[INFO] Switching to next API key...")
                continue
            else:
                error_msg = f"Erreur lors de la génération: {str(e)}"
                yield f"data: {json.dumps({'content': error_msg, 'done': True})}\n\n"
                return
    
    # Fallback if loop completes without return (shouldn't happen)
    error_msg = "Impossible de traiter votre demande. Veuillez réessayer."
    yield f"data: {json.dumps({'content': error_msg, 'done': True})}\n\n"
# ============================================================================
# User Profile & History Views (Protected)
# ============================================================================

@login_required(login_url='chat_app:login')
def profile_view(request):
    """Display user profile and statistics"""
    user = request.user
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Update query count
    profile.total_queries = user.chat_history.count()
    profile.save()
    
    # Get chat history
    chat_history = user.chat_history.all()[:20]
    
    context = {
        'user': user,
        'profile': profile,
        'chat_history': chat_history,
        'total_queries': profile.total_queries,
    }
    
    return render(request, 'chatbot/profile.html', context)


@login_required(login_url='chat_app:login')
def history_view(request):
    """Display user's complete chat history"""
    chat_history = request.user.chat_history.all()
    
    context = {
        'chat_history': chat_history,
        'total_queries': chat_history.count(),
    }
    
    return render(request, 'chatbot/history.html', context)


@login_required(login_url='chat_app:login')
@require_http_methods(["POST"])
def delete_history(request):
    """Delete user's chat history"""
    try:
        count = request.user.chat_history.count()
        request.user.chat_history.all().delete()
        
        # Update profile
        profile = request.user.profile
        profile.total_queries = 0
        profile.save()
        
        messages.success(request, f'{count} conversations supprimées avec succès.')
        return redirect('chat_app:profile')
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
        return redirect('chat_app:profile')


@login_required(login_url='chat_app:login')
@require_http_methods(["GET", "POST"])
def change_password_view(request):
    """Allow users to change their password"""
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate
        errors = []
        
        if not old_password:
            errors.append('Ancien mot de passe requis.')
        elif not request.user.check_password(old_password):
            errors.append('Ancien mot de passe incorrect.')
        
        if not new_password:
            errors.append('Nouveau mot de passe requis.')
        elif len(new_password) < 6:
            errors.append('Le nouveau mot de passe doit contenir au moins 6 caractères.')
        elif len(new_password) > 128:
            errors.append('Le mot de passe est trop long (max 128 caractères).')
        
        if new_password != confirm_password:
            errors.append('Les mots de passe ne correspondent pas.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Change password
            request.user.set_password(new_password)
            request.user.save()
            
            # Re-login user to prevent logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Mot de passe modifié avec succès!')
            return redirect('chat_app:profile')
    
    return render(request, 'chatbot/change_password.html')


# ============================================================================
# API Endpoints for AJAX
# ============================================================================

@login_required(login_url='chat_app:login')
def get_chat_history_json(request):
    """Return chat history as JSON for AJAX requests (for sidebar)"""
    try:
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        chats = request.user.chat_history.all()[offset:offset+limit]
        
        data = [{
            'id': chat.id,
            'query': chat.query[:100],  # Truncate for sidebar display
            'response': chat.response,
            'sources': chat.sources,
            'created_at': chat.created_at.isoformat(),
            'timestamp': int(chat.created_at.timestamp() * 1000)  # JavaScript timestamp
        } for chat in chats]
        
        return JsonResponse({
            'success': True,
            'chats': data,
            'total': request.user.chat_history.count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)