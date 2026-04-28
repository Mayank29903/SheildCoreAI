# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""
WHY: Orchestrates AI inference for deepfake detection. Pre-loads models
on startup to avoid 90-second cold start delays, enabling a sub-3-second
response time critical for live hackathon demos.

NOTE: On Windows, PyTorch may fail to load due to missing Visual C++
Redistributable (shm.dll). In that case, the module gracefully degrades
and all other AI features (Gemini, watermark, EXIF) continue working.
"""

import os
import asyncio
import logging
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Graceful import — PyTorch may not load on Windows without VC++ Runtime
try:
    import cv2
    import numpy as np
    from PIL import Image
    TORCH_AVAILABLE = True
except (OSError, ImportError) as e:
    logger.warning(f"PyTorch/Transformers unavailable: {e}")
    logger.warning("Deepfake detection disabled. All other features work.")
    TORCH_AVAILABLE = False

MODEL_ID = 'dima806/deepfake_vs_real_image_detection'

# Module-level globals
_detector = None
_executor = ThreadPoolExecutor(max_workers=2)


def _deepfake_disabled() -> bool:
    return os.environ.get("DISABLE_DEEPFAKE_MODEL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _model_cache_present() -> bool:
    repo_dir = "models--dima806--deepfake_vs_real_image_detection"
    cache_roots = []

    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        cache_roots.append(Path(hf_home))

    transformers_cache = os.environ.get("TRANSFORMERS_CACHE", "").strip()
    if transformers_cache:
        cache_roots.append(Path(transformers_cache))

    home = Path.home()
    cache_roots.extend([
        home / ".cache" / "huggingface",
        home / ".cache" / "huggingface" / "hub",
        Path("/root/.cache/huggingface"),
        Path("/root/.cache/huggingface/hub"),
    ])

    checked = set()
    for root in cache_roots:
        if not root:
            continue
        root = root.expanduser()
        if root in checked:
            continue
        checked.add(root)
        candidates = [
            root / repo_dir,
            root / "hub" / repo_dir,
        ]
        for candidate in candidates:
            if candidate.exists():
                return True
    return False

async def preload_deepfake_model():
    """
    WHY: Pre-loading at startup ensures 3-second demo response.
    Loading on first request = 90-second delay = demo dies on stage.
    Model is loaded from Docker layer cache, not downloaded at runtime.
    If model isn't cached, we timeout after 10s and fall back gracefully.
    """
    global _detector
    if _deepfake_disabled():
        logger.warning("Skipping deepfake model - disabled by DISABLE_DEEPFAKE_MODEL.")
        return
    if not TORCH_AVAILABLE:
        logger.warning("Skipping deepfake model — PyTorch not available.")
        return
    if _detector is None:
        if not _model_cache_present():
            logger.warning("Skipping deepfake model — no local HuggingFace cache found for %s.", MODEL_ID)
            return
        try:
            # Cloud Run/runtime must stay offline for model resolution.
            # The Dockerfile preloads the model during image build.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            loop = asyncio.get_event_loop()
            _detector = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    _load_detector_from_local_cache
                ),
                timeout=15
            )
            logger.info("Deepfake model loaded successfully")
        except asyncio.TimeoutError:
            logger.warning("Deepfake model load timed out (15s). Will use fallback scores.")
        except Exception as e:
            logger.warning(f"Deepfake model load failed: {e}. Will use fallback scores.")


def _load_detector_from_local_cache():
    from transformers import (
        pipeline,
        AutoImageProcessor,
        AutoModelForImageClassification,
    )

    model = AutoModelForImageClassification.from_pretrained(
        MODEL_ID,
        local_files_only=True,
    )
    processor = AutoImageProcessor.from_pretrained(
        MODEL_ID,
        local_files_only=True,
    )
    return pipeline(
        "image-classification",
        model=model,
        image_processor=processor,
    )

def _run_single_inference(image_path: str) -> dict:
    """
    WHY: Synchronous CPU-bound inference run within a ThreadPoolExecutor.
    Generates genuine AI scores ensuring zero fake numbers are shown.
    """
    try:
        if _detector is None:
            return {
                'is_fake': False, 'confidence': 0.0, 
                'verdict': 'ANALYSIS_ERROR: Model not loaded', 
                'risk_label': 'UNKNOWN', 'frames_analyzed': 0
            }
            
        img = Image.open(image_path).convert('RGB')
        results = _detector(img)
        
        # Parse the HuggingFace zero-shot classification output sequence
        fake_score = 0.0
        for res in results:
            if 'fake' in res['label'].lower():
                fake_score = res['score']
                break
                
        is_fake = fake_score > 0.5
        real_score = 1.0 - fake_score
        confidence = round(fake_score * 100 if is_fake else real_score * 100, 2)
        
        if confidence > 90 and is_fake:
            risk_label = 'CRITICAL'
        elif confidence > 70 and is_fake:
            risk_label = 'HIGH'
        elif confidence > 50 and is_fake:
            risk_label = 'MEDIUM'
        else:
            risk_label = 'LOW'
            
        verdict = "DEEPFAKE DETECTED" if is_fake else "AUTHENTIC CONTENT"
        
        return {
            'is_fake': is_fake,
            'confidence': confidence,
            'verdict': verdict,
            'risk_label': risk_label,
            'frames_analyzed': 1
        }
    except Exception as e:
        return {
            'is_fake': False, 
            'confidence': 0.0,
            'verdict': f'ANALYSIS_ERROR: {str(e)}', 
            'risk_label': 'UNKNOWN', 
            'frames_analyzed': 0
        }

async def detect_deepfake(image_path: str) -> dict:
    """
    WHY: Async wrapper so FastAPI routes don't block the event loop.
    CPU inference runs in ThreadPoolExecutor to avoid blocking.
    """
    if _deepfake_disabled():
        return {
            'is_fake': False,
            'confidence': 0.0,
            'verdict': 'DEEPFAKE_SKIPPED: disabled by config',
            'risk_label': 'UNKNOWN',
            'frames_analyzed': 0,
            'duration_seconds': None
        }
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _run_single_inference, image_path)
    result['duration_seconds'] = None
    return result

async def detect_deepfake_video(video_path: str) -> dict:
    """
    WHY: Sample 16 frames with np.linspace for temporal coverage.
    Averaging across frames reduces false positives from single bad frames.
    """
    if _deepfake_disabled():
        return {
            'is_fake': False,
            'confidence': 0.0,
            'verdict': 'DEEPFAKE_SKIPPED: disabled by config',
            'risk_label': 'UNKNOWN',
            'frames_analyzed': 0,
            'duration_seconds': None
        }
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            raise ValueError("No frames found or unsupported format")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30.0
        duration_seconds = total_frames / fps
        
        frame_indices = np.linspace(0, total_frames - 1, min(16, total_frames), dtype=int)
        
        temp_dir = tempfile.gettempdir()
        analyzed = []
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
                
            temp_frame_path = os.path.join(temp_dir, f"frame_{idx}.jpg")
            cv2.imwrite(temp_frame_path, frame)
            
            res = _run_single_inference(temp_frame_path)
            analyzed.append(res)
            
            try:
                os.remove(temp_frame_path)
            except OSError:
                pass
                
        cap.release()
        
        if not analyzed:
            raise ValueError("Could not extract any valid frames for analysis")
            
        avg_fake_score_pct = sum([r['confidence'] if r['is_fake'] else (100 - r['confidence']) for r in analyzed]) / len(analyzed)
        
        is_fake = avg_fake_score_pct > 50.0
        confidence = round(avg_fake_score_pct if is_fake else (100 - avg_fake_score_pct), 2)
        
        if confidence > 90 and is_fake:
            risk_label = 'CRITICAL'
        elif confidence > 70 and is_fake:
            risk_label = 'HIGH'
        elif confidence > 50 and is_fake:
            risk_label = 'MEDIUM'
        else:
            risk_label = 'LOW'
            
        verdict = "DEEPFAKE DETECTED" if is_fake else "AUTHENTIC CONTENT"
        
        return {
            'is_fake': is_fake,
            'confidence': confidence,
            'verdict': verdict,
            'risk_label': risk_label,
            'frames_analyzed': len(analyzed),
            'duration_seconds': round(duration_seconds, 2)
        }
        
    except Exception as e:
        return {
            'is_fake': False,
            'confidence': 0.0,
            'verdict': f'ANALYSIS_ERROR: {str(e)}',
            'risk_label': 'UNKNOWN',
            'frames_analyzed': 0,
            'duration_seconds': None
        }
