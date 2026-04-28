import os
import sys

# Add the current directory to sys.path to allow importing config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.firebase import get_firestore, init_firebase

init_firebase()
db = get_firestore()
try:
    docs = list(db.collection('violations').stream())
    deepfakes = []
    for d in docs:
        data = d.to_dict() or {}
        if data.get('detection_type') == 'deepfake':
            deepfakes.append((d.id, data.get('detected_at')))

    deepfakes.sort(key=lambda item: item[1] or 0, reverse=True)
    for doc_id, _ in deepfakes[:50]:
        print(doc_id)
except Exception as e:
    import traceback
    traceback.print_exc()
