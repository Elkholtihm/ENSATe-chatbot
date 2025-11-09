from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Créer des utilisateurs de démonstration'

    def handle(self, *args, **kwargs):
        demo_users = [
            {'username': 'admin', 'email': 'admin@ensa.ma', 'password': 'admin123', 'is_staff': True, 'is_superuser': True},
            {'username': 'student1', 'email': 'student1@ensa.ma', 'password': 'student123'},
            {'username': 'student2', 'email': 'student2@ensa.ma', 'password': 'student123'},
        ]
        
        for user_data in demo_users:
            username = user_data.pop('username')
            password = user_data.pop('password')
            
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(
                    f'Utilisateur "{username}" existe déjà'
                ))
                continue
            
            user = User.objects.create_user(username=username, password=password, **user_data)
            self.stdout.write(self.style.SUCCESS(
                f'Utilisateur "{username}" créé avec succès (mot de passe: {password})'
            ))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Utilisateurs de démonstration créés!'))