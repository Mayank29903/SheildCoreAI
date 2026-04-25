# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""
Firebase real-time database and storage configurations and interfaces.
Handles Google Cloud integrations and data storage logic.
"""

import os
import json
import base64
import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore, storage, db
from config.settings import FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_JSON

logger = logging.getLogger(__name__)
_firebase_init_attempted = False
_firebase_init_error = None


def _resolve_credentials_path(raw_value: str) -> Path | None:
    candidate = Path(raw_value).expanduser()
    backend_dir = Path(__file__).resolve().parent.parent

    possible_paths = [candidate]
    if not candidate.is_absolute():
        possible_paths.append(backend_dir / candidate)
        possible_paths.append(Path.cwd() / candidate)

    for path in possible_paths:
        if path.is_file():
            return path.resolve()
    return None


def _load_credential_source(raw_value: str):
    resolved_path = _resolve_credentials_path(raw_value)
    if resolved_path is not None:
        logger.info("Loading Firebase credentials from %s", resolved_path)
        return credentials.Certificate(str(resolved_path))

    if raw_value.startswith('{'):
        return credentials.Certificate(json.loads(raw_value))

    normalized = ''.join(raw_value.split())
    if normalized:
        padding = (-len(normalized)) % 4
        normalized += '=' * padding
        decoded_bytes = base64.b64decode(normalized)
        return credentials.Certificate(json.loads(decoded_bytes.decode('utf-8')))

    raise ValueError("Firebase credentials were empty")


def get_firebase_init_error() -> str | None:
    return _firebase_init_error


def is_firebase_available() -> bool:
    return bool(firebase_admin._apps) or init_firebase()


def init_firebase(required: bool = False) -> bool:
    """
    Initializes the Firebase Admin SDK.
    Accepts either a path to the service account JSON, the raw JSON itself,
    or a base64-encoded JSON blob.
    """
    global _firebase_init_attempted, _firebase_init_error

    if firebase_admin._apps:
        return True

    if _firebase_init_attempted:
        if required and _firebase_init_error:
            raise RuntimeError(_firebase_init_error)
        return False

    if not FIREBASE_PROJECT_ID or not FIREBASE_CREDENTIALS_JSON:
        _firebase_init_attempted = True
        _firebase_init_error = (
            "Firebase disabled: set FIREBASE_PROJECT_ID and "
            "FIREBASE_CREDENTIALS_JSON to enable database/storage features."
        )
        logger.warning(_firebase_init_error)
        if required:
            raise RuntimeError(_firebase_init_error)
        return False

    try:
        cred = _load_credential_source(FIREBASE_CREDENTIALS_JSON)
        firebase_admin.initialize_app(cred, {
            'storageBucket': f"{FIREBASE_PROJECT_ID}.appspot.com",
            'databaseURL': f"https://{FIREBASE_PROJECT_ID}-default-rtdb.firebaseio.com"
        })
        _firebase_init_attempted = True
        _firebase_init_error = None
        logger.info("Firebase Admin Initialized Successfully")
        return True
    except Exception as e:
        _firebase_init_attempted = True
        _firebase_init_error = f"Firebase disabled: {e}"
        logger.warning(_firebase_init_error)
        if required:
            raise RuntimeError(_firebase_init_error) from e
        return False


def _require_firebase() -> None:
    if init_firebase(required=False):
        return
    raise RuntimeError(_firebase_init_error or "Firebase is not available")

def get_firestore() -> firestore.firestore.Client:
    """
    Retrieves the Firestore client after ensuring Firebase initialization.
    """
    _require_firebase()
    return firestore.client()

def get_bucket():
    """
    Retrieves the Storage bucket after ensuring Firebase initialization.
    """
    _require_firebase()
    return storage.bucket()

def get_rtdb() -> db.Reference:
    """
    Retrieves the RTDB root reference after ensuring Firebase initialization.
    """
    _require_firebase()
    return db.reference('/')

def upload_to_storage(local_path: str, remote_path: str) -> str:
    """
    Uploads a local file to Firebase Storage and makes it public.
    """
    try:
        bucket = get_bucket()
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        logger.error(f"Failed to upload {local_path} to {remote_path}: {e}")
        raise

def delete_from_storage(remote_path: str) -> None:
    """
    Deletes a file from Firebase Storage, silently continuing if it fails.
    """
    if not is_firebase_available():
        logger.warning("Skipping storage delete for %s because Firebase is unavailable", remote_path)
        return

    try:
        bucket = get_bucket()
        blob = bucket.blob(remote_path)
        if blob.exists():
            blob.delete()
    except Exception as e:
        logger.warning(f"Failed to delete {remote_path} from storage: {e}")

def increment_rtdb_counter(path: str, field: str, amount: int = 1) -> None:
    """
    Safely increments a counter in the Realtime Database using a transaction.
    This ensures concurrent increments don't overwrite each other.
    """
    ref = get_rtdb().child(path).child(field)

    def increment_transaction(current_value):
        if current_value is None:
            return amount
        return current_value + amount

    try:
        ref.transaction(increment_transaction)
    except Exception as e:
        logger.error(f"Failed to increment counter at {path}/{field}: {e}")
