import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from django.contrib.auth import authenticate

email = "mediconnect53@gmail.com"
password = "Test1234!"

print(f"Testing login for: {email}")
print(f"Password: {password}")
print()

# Check if user exists
try:
    user = User.objects.get(email=email)
    print(f"✓ User exists")
    print(f"  Username: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  Is active: {user.is_active}")
    print(f"  Has usable password: {user.has_usable_password()}")
    print(f"  Role: {user.role}")
    print()
    
    # Test password check directly
    correct = user.check_password(password)
    print(f"  Password check result: {correct}")
    print()
    
    # Test authentication
    print("Testing authenticate()...")
    auth_user = authenticate(username=email, password=password)
    if auth_user:
        print(f"✓ Authentication successful: {auth_user.email}")
    else:
        print("✗ Authentication failed")
        
        # Try with lowercase
        auth_user2 = authenticate(username=email.lower(), password=password)
        if auth_user2:
            print(f"✓ Authentication with lowercase successful: {auth_user2.email}")
        else:
            print("✗ Authentication with lowercase also failed")
    
except User.DoesNotExist:
    print("✗ User does not exist")
