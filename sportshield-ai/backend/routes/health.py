# SportShield AI | Google Solution Challenge 2026 | First Prize Target

from fastapi import APIRouter
from datetime import datetime, timezone
from config.firebase import get_firebase_init_error, is_firebase_available
from models.deepfake import _detector
from services.scheduler import scheduler

router = APIRouter()

@router.get("/health")
async def health_check():
    firebase_ok = is_firebase_available()
    firebase_error = None if firebase_ok else get_firebase_init_error()
        
    return {
        'status': 'operational',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '2.0.0',
        'competition': 'Google Solution Challenge 2026',
        'model_loaded': _detector is not None,
        'firebase_connected': firebase_ok,
        'firebase_error': firebase_error,
        'scheduler_running': scheduler.running if scheduler else False,
        'components': {
            'deepfake_model': _detector is not None,
            'database': firebase_ok,
            'realtime': firebase_ok,
            'storage': firebase_ok,
            'auth': firebase_ok,
            'ai': True, 
            'background_jobs': scheduler.running if scheduler else False
        }
    }
