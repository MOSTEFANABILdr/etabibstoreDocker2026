import os
import django
import jwt
import datetime
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etabibWebsite.settings')
django.setup()

from core.utils import generateJwtToken
from django.contrib.auth.models import User

# Create a dummy user for testing
user = User(username='testuser', email='test@example.com', first_name='Test', last_name='User', id=1)

print(f"Using Secret: |{settings.JWT_APP_SECRET}|")

# Generate Token
try:
    token = generateJwtToken(user)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    print(f"Generated Token: {token}")
except Exception as e:
    print(f"Token Generation Failed: {e}")
    exit(1)

# Verify Token
try:
    decoded = jwt.decode(token, settings.JWT_APP_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    print("Verification Successful!")
    print(decoded)
except Exception as e:
    print(f"Verification Failed: {e}")
