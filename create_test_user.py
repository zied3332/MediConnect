import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

# Create test user
email = "mediconnect53@gmail.com"
password = "Test1234!"

# Delete if exists
User.objects.filter(email=email).delete()

# Create new user
user = User.objects.create_user(
    username="mediconnect53",
    email=email,
    password=password,
    first_name="Test",
    last_name="User",
    role="patient"
)

print(f"✓ Created user: {user.email}")
print(f"  Password: {password}")
print(f"  Has usable password: {user.has_usable_password()}")
print(f"  Role: {user.role}")
