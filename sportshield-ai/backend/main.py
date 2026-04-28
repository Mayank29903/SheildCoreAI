# SportShield AI | Google Solution Challenge 2026 | First Prize Target

import asyncio
import os
import time
import tempfile
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config.firebase import init_firebase, get_firebase_init_error
from models.deepfake import preload_deepfake_model
from services.scheduler import start_scheduler, stop_scheduler
from services.rate_limiter import limiter, _rate_limit_exceeded_handler

from routes.health import router as health_router
from routes.register import router as register_router
from routes.scan import router as scan_router
from routes.violations import router as violations_router
from routes.analytics import router as analytics_router
from routes.crawl import router as crawl_router
from routes.evidence import router as evidence_router
from routes.assets import router as assets_router
from routes.demo import router as demo_router

_dashboard_sockets = []
_scan_progress_sockets = {}
_model_preload_task = None
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_preload_task
    os.makedirs(os.path.join(tempfile.gettempdir(), 'sportshield'), exist_ok=True)
    # Warm the deepfake model in the background so container startup stays fast.
    _model_preload_task = asyncio.create_task(preload_deepfake_model())
    firebase_ready = init_firebase()
    if firebase_ready:
        start_scheduler()
    else:
        logger.warning("Starting without Firebase integrations: %s", get_firebase_init_error())
    
    app.state.scan_progress_sockets = _scan_progress_sockets
    app.state.dashboard_sockets = _dashboard_sockets
    yield
    if _model_preload_task and not _model_preload_task.done():
        _model_preload_task.cancel()
    stop_scheduler()

app = FastAPI(title='ShieldCore AI', version='2.0.0', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(register_router, prefix="/register")
app.include_router(scan_router, prefix="/scan")
app.include_router(violations_router, prefix="/violations")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(crawl_router, prefix="/crawl")
app.include_router(evidence_router, prefix="/evidence")
app.include_router(assets_router, prefix="/assets")
app.include_router(demo_router)

# Mount offline demo images
demo_dir = os.path.join(os.path.dirname(__file__), "DEMO_DATASET")
if os.path.exists(demo_dir):
    app.mount("/demo-assets", StaticFiles(directory=demo_dir), name="demo-assets")

@app.get("/")
async def root():
    return {
        'name': 'ShieldCore AI',
        'version': '2.0.0',
        'competition': 'Google Solution Challenge 2026',
        'endpoints': ['/register', '/scan', '/scan/url', '/scan/lite', '/assets', '/violations', '/analytics', '/crawl', '/evidence', '/ws'],
        'status': 'running'
    }

@app.websocket("/ws")
async def websocket_dashboard(websocket: WebSocket):
    await websocket.accept()
    _dashboard_sockets.append(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _dashboard_sockets: _dashboard_sockets.remove(websocket)

@app.websocket("/ws/scan/{scan_id}")
async def websocket_scan(websocket: WebSocket, scan_id: str):
    await websocket.accept()
    if scan_id not in _scan_progress_sockets: _scan_progress_sockets[scan_id] = []
    _scan_progress_sockets[scan_id].append(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if scan_id in _scan_progress_sockets and websocket in _scan_progress_sockets[scan_id]:
            _scan_progress_sockets[scan_id].remove(websocket)
            if not _scan_progress_sockets[scan_id]: del _scan_progress_sockets[scan_id]

async def push_scan_step(scan_id: str, step: str, status: str, data: dict = {}):
    payload = {'step': step, 'status': status, 'data': data, 'timestamp': time.time()}
    for ws in _scan_progress_sockets.get(scan_id, []).copy():
        try: await ws.send_json(payload)
        except:
             if ws in _scan_progress_sockets.get(scan_id, []): _scan_progress_sockets[scan_id].remove(ws)
app.push_scan_step = push_scan_step

async def broadcast_violation(violation_data: dict):
    for ws in _dashboard_sockets.copy():
        try: await ws.send_json(violation_data)
        except:
            if ws in _dashboard_sockets: _dashboard_sockets.remove(ws)
app.broadcast_violation = broadcast_violation

@app.exception_handler(413)
async def payload_too_large(request, exc):
    return JSONResponse(status_code=413, content={'error': 'File too large', 'message': str(exc), 'max_size_mb': 50})

@app.exception_handler(422)
async def unprocessable_entity(request, exc):
    return JSONResponse(status_code=422, content={'error': 'Validation error', 'message': 'Invalid input', 'details': str(exc)})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False, workers=1)
