import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from allauth.socialaccount.models import SocialAccount

print('=== USERS ===')
for u in User.objects.all():
    has_social = SocialAccount.objects.filter(user=u).exists()
    print(f'{u.email:40} | Password: {u.has_usable_password()} | Google: {has_social} | Role: {u.role}')

print(f'\nTotal Users: {User.objects.count()}')
print(f'Total Social Accounts: {SocialAccount.objects.count()}')
