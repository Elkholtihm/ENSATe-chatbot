from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class ChatHistory(models.Model):
    """Store chat history for each user"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chat_history'
    )
    query = models.TextField(verbose_name="Question")
    response = models.TextField(verbose_name="Réponse")
    sources = models.TextField(blank=True, null=True, verbose_name="Sources")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    
    class Meta:
        verbose_name = "Historique de chat"
        verbose_name_plural = "Historiques de chat"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.query[:50]}..."


class UserProfile(models.Model):
    """Extended user profile with additional information"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    total_queries = models.IntegerField(default=0, verbose_name="Total de questions")
    last_active = models.DateTimeField(auto_now=True, verbose_name="Dernière activité")
    preferences = models.JSONField(default=dict, blank=True, verbose_name="Préférences")
    
    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"
    
    def __str__(self):
        return f"Profil de {self.user.username}"
    
    def update_query_count(self):
        """Update total queries count"""
        self.total_queries = self.user.chat_history.count()
        self.save(update_fields=['total_queries', 'last_active'])


# ============================================================================
# Signals for automatic UserProfile management
# ============================================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile automatically when new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()


@receiver(post_save, sender=ChatHistory)
def update_profile_on_chat(sender, instance, created, **kwargs):
    """Update user profile stats when new chat is created"""
    if created:
        try:
            profile, created = UserProfile.objects.get_or_create(user=instance.user)
            profile.update_query_count()
        except Exception as e:
            print(f"Error updating profile: {e}")