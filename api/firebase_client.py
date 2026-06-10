import os
import json
import firebase_admin
from firebase_admin import credentials, firestore


def init():
    if firebase_admin._apps:
        return
    # Render stores the JSON as an env var; local uses a file path
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw:
        cred = credentials.Certificate(json.loads(raw))
    else:
        cred = credentials.Certificate(
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./firebase-service-account.json")
        )
    firebase_admin.initialize_app(cred)


def db():
    init()
    return firestore.client()
