from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Changer le mot de passe d\'un utilisateur'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nom d\'utilisateur')
        parser.add_argument('new_password', type=str, help='Nouveau mot de passe')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        new_password = kwargs['new_password']
        
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'Mot de passe changé avec succès pour {username}'
            ))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f'Utilisateur "{username}" introuvable'
            ))
