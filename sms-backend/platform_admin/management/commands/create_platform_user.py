from django.core.management.base import BaseCommand, CommandError

from platform_admin.models import PlatformUser


class Command(BaseCommand):
    help = 'Create a platform operator (email/password).'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')
        parser.add_argument(
            '--role',
            default=PlatformUser.Role.SUPER_ADMIN,
            choices=PlatformUser.Role.values,
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        if PlatformUser.objects.filter(email__iexact=email).exists():
            raise CommandError(f'Platform user already exists: {email}')

        user = PlatformUser.objects.create_user(
            email=email,
            password=options['password'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            role=options['role'],
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Created platform user {user.email} ({user.role})'))
