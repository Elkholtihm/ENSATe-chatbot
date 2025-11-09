from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone


class Command(BaseCommand):
    help = 'Liste tous les utilisateurs avec leurs informations détaillées'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active',
            action='store_true',
            help='Afficher uniquement les utilisateurs actifs',
        )
        parser.add_argument(
            '--staff',
            action='store_true',
            help='Afficher uniquement les membres du staff',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['detailed', 'simple'],
            default='detailed',
            help='Format d\'affichage (detailed ou simple)',
        )

    def handle(self, *args, **options):
        # Filter users based on options
        users = User.objects.all().order_by('-date_joined')
        
        if options['active']:
            users = users.filter(is_active=True)
        
        if options['staff']:
            users = users.filter(is_staff=True)
        
        # Display header
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('LISTE DES UTILISATEURS'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('Aucun utilisateur trouvé.'))
            return
        
        # Display users
        for i, user in enumerate(users, 1):
            if options['format'] == 'detailed':
                self._display_detailed(user, i)
            else:
                self._display_simple(user, i)
        
        # Display summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(
            f'Total: {users.count()} utilisateur(s)'
        ))
        
        # Display statistics
        total_queries = sum(u.chat_history.count() for u in users)
        self.stdout.write(self.style.SUCCESS(
            f'Questions totales: {total_queries}'
        ))
        self.stdout.write('=' * 80 + '\n')
    
    def _display_detailed(self, user, index):
        """Display user in detailed format"""
        self.stdout.write(f'\n{index}. ' + '-' * 75)
        self.stdout.write(f'   ID: {user.id}')
        self.stdout.write(f'   Username: {self.style.HTTP_INFO(user.username)}')
        self.stdout.write(f'   Email: {user.email or "N/A"}')
        self.stdout.write(f'   Nom complet: {user.get_full_name() or "N/A"}')
        
        # Status badges
        status = []
        if user.is_staff:
            status.append(self.style.WARNING('STAFF'))
        if user.is_superuser:
            status.append(self.style.ERROR('SUPERUSER'))
        if user.is_active:
            status.append(self.style.SUCCESS('ACTIF'))
        else:
            status.append(self.style.ERROR('INACTIF'))
        
        self.stdout.write(f'   Statut: {" | ".join(status)}')
        
        # Dates
        self.stdout.write(
            f'   Inscription: {user.date_joined.strftime("%d/%m/%Y %H:%M")}'
        )
        self.stdout.write(
            f'   Dernière connexion: '
            f'{user.last_login.strftime("%d/%m/%Y %H:%M") if user.last_login else "Jamais"}'
        )
        
        # Chat statistics
        try:
            chat_count = user.chat_history.count()
            self.stdout.write(f'   Questions posées: {chat_count}')
            
            if hasattr(user, 'profile'):
                last_active = user.profile.last_active.strftime("%d/%m/%Y %H:%M")
                self.stdout.write(f'   Dernière activité: {last_active}')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'   Erreur statistiques: {str(e)}')
            )
    
    def _display_simple(self, user, index):
        """Display user in simple format"""
        status = '✓' if user.is_active else '✗'
        staff = '👑' if user.is_staff else '  '
        chat_count = user.chat_history.count()
        
        self.stdout.write(
            f'{index:3d}. {status} {staff} '
            f'{user.username:20s} | {user.email:30s} | '
            f'Questions: {chat_count:4d}'
        )


# ============================================================================
# chat_app/management/commands/change_password.py
# ============================================================================

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from getpass import getpass


class Command(BaseCommand):
    help = 'Changer le mot de passe d\'un utilisateur'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Nom d\'utilisateur'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Nouveau mot de passe (si non spécifié, sera demandé)',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Ne pas demander de confirmation',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options.get('password')
        no_input = options.get('no_input', False)
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Utilisateur "{username}" introuvable')
        
        # Display user info
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING(
            f'Changement de mot de passe pour: {username}'
        ))
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(
            f'Dernière connexion: '
            f'{user.last_login.strftime("%d/%m/%Y %H:%M") if user.last_login else "Jamais"}'
        )
        self.stdout.write('=' * 60 + '\n')
        
        # Get password if not provided
        if not password:
            if no_input:
                raise CommandError(
                    'Le mot de passe doit être fourni avec --password '
                    'quand --no-input est utilisé'
                )
            
            password = getpass('Nouveau mot de passe: ')
            password_confirm = getpass('Confirmer le mot de passe: ')
            
            if password != password_confirm:
                raise CommandError('Les mots de passe ne correspondent pas')
        
        # Validate password
        if len(password) < 6:
            raise CommandError(
                'Le mot de passe doit contenir au moins 6 caractères'
            )
        
        # Confirm action
        if not no_input:
            confirm = input(
                f'\nConfirmez-vous le changement de mot de passe '
                f'pour "{username}"? (oui/non): '
            )
            if confirm.lower() not in ['oui', 'o', 'yes', 'y']:
                self.stdout.write(self.style.WARNING('Opération annulée'))
                return
        
        # Change password
        try:
            user.set_password(password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Mot de passe changé avec succès pour "{username}"\n'
                )
            )
        except Exception as e:
            raise CommandError(f'Erreur lors du changement: {str(e)}')


# ============================================================================
# chat_app/management/commands/create_demo_users.py
# ============================================================================

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Créer des utilisateurs de démonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprimer et recréer les utilisateurs existants',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Nombre d\'étudiants à créer (défaut: 3)',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        student_count = options.get('count', 3)
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('CRÉATION DES UTILISATEURS DEMO'))
        self.stdout.write('=' * 60 + '\n')
        
        # Admin user
        admin_data = {
            'username': 'admin',
            'email': 'admin@ensa.ma',
            'password': 'admin123',
            'first_name': 'Admin',
            'last_name': 'ENSA',
            'is_staff': True,
            'is_superuser': True
        }
        
        self._create_user(admin_data, reset)
        
        # Student users
        for i in range(1, student_count + 1):
            student_data = {
                'username': f'student{i}',
                'email': f'student{i}@ensa.ma',
                'password': 'student123',
                'first_name': f'Étudiant',
                'last_name': f'{i}',
                'is_staff': False,
                'is_superuser': False
            }
            self._create_user(student_data, reset)
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(
            f'✓ {1 + student_count} utilisateurs créés/vérifiés'
        ))
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.WARNING(
            '\nMot de passe par défaut:'
        ))
        self.stdout.write(f'  - Admin: admin123')
        self.stdout.write(f'  - Étudiants: student123')
        self.stdout.write(self.style.WARNING(
            '\n⚠️  Changez ces mots de passe en production!\n'
        ))
    
    def _create_user(self, user_data, reset=False):
        """Create or update a user"""
        username = user_data['username']
        password = user_data.pop('password')
        
        # Check if user exists
        if User.objects.filter(username=username).exists():
            if reset:
                User.objects.filter(username=username).delete()
                self.stdout.write(
                    self.style.WARNING(f'  Supprimé: {username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'  Existe déjà: {username} (utilisez --reset pour recréer)'
                    )
                )
                return
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            **user_data
        )
        
        role = 'Admin' if user.is_superuser else 'Étudiant'
        self.stdout.write(
            self.style.SUCCESS(
                f'  ✓ Créé: {username:15s} ({role}) - {user.email}'
            )
        )


# ============================================================================
# chat_app/management/commands/delete_user.py
# NEW: Delete user command
# ============================================================================

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Supprimer un utilisateur et son historique'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Nom d\'utilisateur à supprimer'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Ne pas demander de confirmation',
        )

    def handle(self, *args, **options):
        username = options['username']
        no_input = options.get('no_input', False)
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Utilisateur "{username}" introuvable')
        
        # Display user info
        chat_count = user.chat_history.count()
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING(
            f'SUPPRESSION DE L\'UTILISATEUR: {username}'
        ))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Questions: {chat_count}')
        self.stdout.write(f'Staff: {"Oui" if user.is_staff else "Non"}')
        self.stdout.write(f'Superuser: {"Oui" if user.is_superuser else "Non"}')
        self.stdout.write('=' * 60 + '\n')
        
        # Confirm deletion
        if not no_input:
            self.stdout.write(self.style.ERROR(
                '⚠️  ATTENTION: Cette action est irréversible!'
            ))
            confirm = input(
                f'\nTapez "{username}" pour confirmer la suppression: '
            )
            if confirm != username:
                self.stdout.write(self.style.WARNING('Suppression annulée'))
                return
        
        # Delete user
        try:
            user.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Utilisateur "{username}" supprimé avec succès\n'
                )
            )
        except Exception as e:
            raise CommandError(f'Erreur lors de la suppression: {str(e)}')


# ============================================================================
# chat_app/management/commands/user_stats.py
# NEW: User statistics command
# ============================================================================

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta


class Command(BaseCommand):
    help = 'Afficher les statistiques des utilisateurs'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('STATISTIQUES DES UTILISATEURS'))
        self.stdout.write('=' * 80 + '\n')
        
        # Total users
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        
        self.stdout.write('📊 Utilisateurs:')
        self.stdout.write(f'   Total: {total_users}')
        self.stdout.write(f'   Actifs: {active_users}')
        self.stdout.write(f'   Staff: {staff_users}')
        self.stdout.write(f'   Inactifs: {total_users - active_users}')
        
        # Recent activity
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        recent_week = User.objects.filter(last_login__gte=week_ago).count()
        recent_month = User.objects.filter(last_login__gte=month_ago).count()
        
        self.stdout.write('\n🕐 Activité récente:')
        self.stdout.write(f'   Dernière semaine: {recent_week}')
        self.stdout.write(f'   Dernier mois: {recent_month}')
        
        # Chat statistics
        total_chats = 0
        for user in User.objects.all():
            total_chats += user.chat_history.count()
        
        avg_chats = total_chats / total_users if total_users > 0 else 0
        
        self.stdout.write('\n💬 Questions:')
        self.stdout.write(f'   Total: {total_chats}')
        self.stdout.write(f'   Moyenne par utilisateur: {avg_chats:.1f}')
        
        # Top users
        self.stdout.write('\n🏆 Top 5 utilisateurs:')
        top_users = User.objects.annotate(
            chat_count=Count('chat_history')
        ).order_by('-chat_count')[:5]
        
        for i, user in enumerate(top_users, 1):
            self.stdout.write(
                f'   {i}. {user.username:20s} - {user.chat_count} questions'
            )
        
        self.stdout.write('\n' + '=' * 80 + '\n')