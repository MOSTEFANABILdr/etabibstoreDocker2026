import json

with open('private_key.pem', 'r') as f:
    private_key = f.read()

data = {
  "type": "service_account",
  "project_id": "dummy-project",
  "private_key_id": "dummy-key-id",
  "private_key": private_key,
  "client_email": "dummy@dummy-project.iam.gserviceaccount.com",
  "client_id": "1234567890",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy%40dummy-project.iam.gserviceaccount.com"
}

with open('.google-drive-dev.json', 'w') as f:
    json.dump(data, f)
