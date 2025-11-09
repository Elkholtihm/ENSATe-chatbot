from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ChatHistory, UserProfile


# Unregister the default User admin
admin.site.unregister(User)


# Inline for ChatHistory in User admin
class ChatHistoryInline(admin.TabularInline):
    model = ChatHistory
    extra = 0
    can_delete = True
    readonly_fields = ('created_at', 'short_query', 'short_response')
    fields = ('short_query', 'short_response', 'created_at')
    
    def short_query(self, obj):
        return obj.query[:50] + '...' if len(obj.query) > 50 else obj.query
    short_query.short_description = 'Question'
    
    def short_response(self, obj):
        return obj.response[:50] + '...' if len(obj.response) > 50 else obj.response
    short_response.short_description = 'Réponse'
    
    def has_add_permission(self, request, obj=None):
        return False


# Inline for UserProfile in User admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'
    readonly_fields = ('total_queries', 'last_active')


# Register User with custom admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 
        'email', 
        'full_name_display',
        'is_staff', 
        'is_active', 
        'date_joined_display',
        'get_total_queries',
        'view_history_link'
    )
    list_filter = (
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'date_joined',
        'last_login'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    # Add inlines
    inlines = [UserProfileInline, ChatHistoryInline]
    
    # Add custom actions
    actions = ['activate_users', 'deactivate_users', 'reset_passwords']
    
    # Fieldsets for detailed view
    fieldsets = (
        ('Informations de connexion', {
            'fields': ('username', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 
                'is_staff', 
                'is_superuser',
                'groups', 
                'user_permissions'
            ),
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    def full_name_display(self, obj):
        """Display full name or N/A"""
        full_name = obj.get_full_name()
        return full_name if full_name else mark_safe('<em>N/A</em>')
    full_name_display.short_description = 'Nom complet'
    
    def date_joined_display(self, obj):
        """Format date joined"""
        return obj.date_joined.strftime('%d/%m/%Y %H:%M')
    date_joined_display.short_description = 'Date d\'inscription'
    date_joined_display.admin_order_field = 'date_joined'
    
    def get_total_queries(self, obj):
        """Get total queries with colored badge"""
        count = obj.chat_history.count()
        if count > 100:
            color = 'green'
        elif count > 50:
            color = 'orange'
        elif count > 0:
            color = 'blue'
        else:
            color = 'gray'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, count
        )
    get_total_queries.short_description = 'Questions'
    
    def view_history_link(self, obj):
        """Link to view all user's chat history"""
        count = obj.chat_history.count()
        if count > 0:
            url = reverse('admin:chat_app_chathistory_changelist') + f'?user__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #417690; font-weight: bold;">Voir historique ({})</a>',
                url, count
            )
        return '-'
    view_history_link.short_description = 'Historique'
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            f"{updated} utilisateur(s) activé(s) avec succès.",
            level='success'
        )
    activate_users.short_description = "✓ Activer les utilisateurs"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            f"{updated} utilisateur(s) désactivé(s).",
            level='warning'
        )
    deactivate_users.short_description = "✗ Désactiver les utilisateurs"
    
    def reset_passwords(self, request, queryset):
        """Mark passwords for reset"""
        # This just shows how many would be affected
        count = queryset.count()
        self.message_user(
            request, 
            f"{count} utilisateur(s) sélectionné(s). "
            f"Utilisez la commande 'change_password' pour changer les mots de passe.",
            level='info'
        )
    reset_passwords.short_description = "🔑 Réinitialiser mots de passe"


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'user_link',
        'short_query', 
        'short_response', 
        'created_at_display',
        'response_length'
    )
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'query', 'response')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'user', 'query', 'response')
    
    # Fields to display in detail view
    fields = ('user', 'query', 'response', 'created_at')
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user.username
        )
    user_link.short_description = 'Utilisateur'
    user_link.admin_order_field = 'user__username'
    
    def short_query(self, obj):
        """Truncate query for display"""
        query = obj.query[:80] + '...' if len(obj.query) > 80 else obj.query
        return format_html('<span title="{}">{}</span>', obj.query, query)
    short_query.short_description = 'Question'
    
    def short_response(self, obj):
        """Truncate response for display"""
        response = obj.response[:80] + '...' if len(obj.response) > 80 else obj.response
        return format_html('<span title="{}">{}</span>', obj.response, response)
    short_response.short_description = 'Réponse'
    
    def created_at_display(self, obj):
        """Format created date"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M:%S')
    created_at_display.short_description = 'Date'
    created_at_display.admin_order_field = 'created_at'
    
    def response_length(self, obj):
        """Show response length"""
        length = len(obj.response)
        return f"{length} car."
    response_length.short_description = 'Longueur'
    
    def has_add_permission(self, request):
        """Disable manual creation"""
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_link',
        'total_queries_display',
        'last_active_display',
        'account_age'
    )
    list_filter = ('last_active',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_active', 'total_queries')
    
    fields = ('user', 'total_queries', 'last_active', 'preferences')
    
    def user_link(self, obj):
        """Link to user admin page"""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.user.username
        )
    user_link.short_description = 'Utilisateur'
    user_link.admin_order_field = 'user__username'
    
    def total_queries_display(self, obj):
        """Display total queries with badge"""
        count = obj.total_queries
        return format_html(
            '<span style="background-color: #417690; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            count
        )
    total_queries_display.short_description = 'Questions'
    total_queries_display.admin_order_field = 'total_queries'
    
    def last_active_display(self, obj):
        """Format last active date"""
        return obj.last_active.strftime('%d/%m/%Y %H:%M')
    last_active_display.short_description = 'Dernière activité'
    last_active_display.admin_order_field = 'last_active'
    
    def account_age(self, obj):
        """Calculate account age"""
        from django.utils import timezone
        age = timezone.now() - obj.user.date_joined
        days = age.days
        
        if days < 1:
            return "Aujourd'hui"
        elif days == 1:
            return "1 jour"
        elif days < 30:
            return f"{days} jours"
        elif days < 365:
            months = days // 30
            return f"{months} mois"
        else:
            years = days // 365
            return f"{years} an(s)"
    account_age.short_description = 'Ancienneté'
    
    def has_add_permission(self, request):
        """Disable manual creation"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion"""
        return False


# Customize admin site headers
admin.site.site_header = "Administration ENSA Chatbot"
admin.site.site_title = "ENSA Chatbot Admin"
admin.site.index_title = "Tableau de bord d'administration"