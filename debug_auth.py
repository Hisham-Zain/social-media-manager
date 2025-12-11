import os

import google.auth

print(f"Environment Variable: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

try:
    creds, project = google.auth.default()
    print("✅ Success!")
    print(f"Project: {project}")
    print(f"Creds Type: {type(creds)}")
    print(f"Valid: {creds.valid}")
except Exception as e:
    print("❌ Failed:")
    print(e)
