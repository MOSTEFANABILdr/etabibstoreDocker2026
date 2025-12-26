from oauth2client.service_account import ServiceAccountCredentials
import sys

try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name('/app/.google-drive-dev.json')
    print("Successfully loaded credentials")
except Exception as e:
    print(f"Failed to load credentials: {e}")
    sys.exit(1)
