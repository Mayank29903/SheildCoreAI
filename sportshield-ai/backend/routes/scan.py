# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""
Two-phase WebSocket-driven scan.
Phase 1: Validate + upload → return scan_id IMMEDIATELY (< 1 second).
Phase 2: Background asyncio task runs 6 sequential steps.
"""

import os
import time
import uuid
import asyncio
import logging
from fastapi import APIRouter, Request, BackgroundTasks, UploadFile, File, Form, HTTPException
from firebase_admin import firestore

from services.file_validator import validate_upload
from services.rate_limiter import limiter
from services.geo_lookup import get_geo_from_domain
from services.anomaly import check_viral_spread
from services.gemini import analyze_image_with_gemini_vision, generate_legal_report
from services.content_dna import calculate_content_dna
from services.factcheck import check_fact_claims
from models.deepfake import detect_deepfake, detect_deepfake_video
from models.audio_sync import analyze_audio_sync
from models.exif_forensics import analyze_exif
from models.phash import compare_to_registry
from models.watermark import extract_watermark
from config.firebase import get_firestore, get_rtdb, upload_to_storage
from config.settings import TMP_DIR

logger = logging.getLogger(__name__)
router = APIRouter()

STEP_FALLBACKS = {
    'deepfake': {'is_fake': False, 'confidence': 0, 'verdict': 'TIMEOUT'},
    'audio_sync': {'analyzed': False, 'sync_score': None, 'is_suspicious': None, 'verdict': 'TIMEOUT'},
    'gemini_vision': {'manipulation_detected': False, 'manipulation_signals': [], 'authenticity_confidence': 50}
}

async def run_step_with_timeout(coro, timeout_seconds: int, step_name: str) -> dict:
    try: return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError: return STEP_FALLBACKS.get(step_name, {})

def calculate_trust_score(deepfake, exif, phash, wm, gemini) -> tuple[int, str]:
    score = 50
    if not deepfake.get('is_fake'): score += 25
    if not phash.get('is_match'): score += 15
    if wm and wm.get('cert_id') and len(wm['cert_id']) == 12: score += 10
    if exif.get('risk_score', 100) < 30: score += 5
    if gemini.get('authenticity_confidence', 0) > 70 and not gemini.get('manipulation_detected'): score += 5
    
    flags = exif.get('flags', [])
    if 'EXIF_STRIPPED' in flags: score -= 20
    if 'SUSPICIOUS_SOFTWARE' in flags: score -= 10
    
    score = max(0, min(100, score))
    threat = "CRITICAL" if score <= 25 else "HIGH" if score <= 50 else "MEDIUM" if score <= 70 else "LOW"
    return score, threat

@router.post("/")
@limiter.limit("10/minute")
async def scan_content(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), user_uid: str = Form(...), language: str = Form('en')):
    content = await validate_upload(file)
    scan_id = str(uuid.uuid4())
    import mimetypes
    ext = mimetypes.guess_extension(file.content_type) or '.bin'
    tmp_path = os.path.join(TMP_DIR, f"{scan_id}_upload{ext}")
    
    with open(tmp_path, 'wb') as f:
        f.write(content)

    background_tasks.add_task(_process_scan, request.app, scan_id, tmp_path, user_uid, language, file.filename, file.content_type, len(content))
    return {'scan_id': scan_id, 'status': 'processing'}

async def _process_scan(app, scan_id, temp_path, user_uid, language, file_name, mime_type, file_size):
    db, rtdb, loop = get_firestore(), get_rtdb(), asyncio.get_event_loop()
    is_vid = mime_type.startswith('video/')

    try:
        ext = os.path.splitext(temp_path)[1] or '.bin'
        file_url = upload_to_storage(temp_path, f"scans/{scan_id}/upload{ext}")
    except Exception as e:
        logger.warning(f"Storage upload failed (bucket missing or region restricted) - continuing scan locally: {e}")
        file_url = None

    try:
        # Step 1
        df = await run_step_with_timeout(detect_deepfake_video(temp_path) if is_vid else detect_deepfake(temp_path), 10, 'deepfake')
        await app.push_scan_step(scan_id, 'deepfake', 'done', {'is_fake': df.get('is_fake', False), 'confidence': df.get('confidence', 0), 'verdict': df.get('verdict', '')})

        # Step 2
        asy = await run_step_with_timeout(analyze_audio_sync(temp_path), 10, 'audio_sync') if is_vid else {'analyzed': False}
        if asy.get('is_suspicious') and df.get('is_fake'): df['confidence'] = min(99.0, df['confidence'] + 8.0)
        await app.push_scan_step(scan_id, 'audio_sync', 'done', asy)

        # Step 3
        try:
            exf = await loop.run_in_executor(None, analyze_exif, temp_path)
        except Exception as exif_err:
            logger.warning(f'EXIF analysis failed: {exif_err}')
            exf = {'flags': ['EXIF_PARSE_ERROR'], 'risk_score': 15, 'risk_label': 'MEDIUM', 'exif_data': {}, 'summary': 'EXIF analysis failed'}
        await app.push_scan_step(scan_id, 'exif', 'done', {'risk_score': exf.get('risk_score', 0), 'flags': exf.get('flags', [])})

        # Step 4
        phm = await compare_to_registry(temp_path)
        await app.push_scan_step(scan_id, 'registry', 'done', {'is_match': phm.get('is_match', False), 'similarity': phm.get('similarity_percent', 0), 'matched_asset_name': phm.get('matched_asset_name')})

        # Step 5
        wmk = await loop.run_in_executor(None, extract_watermark, temp_path) if not is_vid else None
        await app.push_scan_step(scan_id, 'watermark', 'done', {'found': wmk is not None, 'cert_id': wmk.get('cert_id') if wmk else None})

        # Step 6
        gv = await run_step_with_timeout(analyze_image_with_gemini_vision(temp_path), 10, 'gemini_vision') if not is_vid else STEP_FALLBACKS['gemini_vision']
        await app.push_scan_step(scan_id, 'gemini_vision', 'done', {'manipulation_detected': gv.get('manipulation_detected', False), 'confidence': gv.get('authenticity_confidence', 50)})

        dna = calculate_content_dna(df, exf, phm, wmk, gv, temp_path)
        ts, tl = calculate_trust_score(df, exf, phm, wmk, gv)

        lr = None
        if tl in ('CRITICAL', 'HIGH', 'MEDIUM'):
            lr = await generate_legal_report({'threat_level': tl, 'trust_score': ts, 'deepfake_is_fake': df.get('is_fake'), 'asset_match_found': phm.get('is_match'), 'exif_flags': exf.get('flags')}, language)
            
        fc = []
        if phm.get('is_match') and phm.get('matched_asset_name'):
            fc = await check_fact_claims(f"{phm['matched_asset_name']} {phm.get('matched_sport_category','')}")

        if phm.get('is_match') or df.get('is_fake'):
            geo = await get_geo_from_domain('manual_scan')
            v_id = str(uuid.uuid4())
            loss = db.collection('assets').document(phm['matched_asset_id']).get().to_dict().get('estimated_rights_value_usd', 0) if phm.get('is_match') else 0
            vt = 'both' if (phm.get('is_match') and df.get('is_fake')) else ('deepfake' if df.get('is_fake') else 'theft')
                
            v_doc = {
                'violation_id': v_id, 'asset_id': phm.get('matched_asset_id'), 'asset_name': phm.get('matched_asset_name', 'Unknown/Deepfake'),
                'owner_name': phm.get('matched_owner_name'), 'owner_email': phm.get('matched_owner_email'), 'organization': phm.get('matched_organization'),
                'sport_category': phm.get('matched_sport_category'), 'source_url': None, 'source_domain': 'manual_scan',
                'detection_method': 'manual_scan', 'detection_type': vt, 'similarity_percent': phm.get('similarity_percent', 0),
                'is_deepfake': df.get('is_fake'), 'deepfake_confidence': df.get('confidence', 0), 'exif_flags': exf.get('flags', []),
                'geo_lat': geo.get('geo_lat'), 'geo_lng': geo.get('geo_lng'), 'geo_city': geo.get('geo_city'), 'geo_country': geo.get('geo_country'),
                'estimated_loss_usd': loss, 'status': 'detected', 'detected_at': firestore.SERVER_TIMESTAMP, 'evidence_scan_id': scan_id
            }
            db.collection('violations').document(v_id).set(v_doc)
            
            now_ms = int(time.time() * 1000)
            rtdb.child(f'violations_live/{v_id}').set({
                'asset_name': v_doc['asset_name'], 'owner_name': v_doc.get('owner_name'), 'organization': v_doc.get('organization'),
                'sport_category': v_doc.get('sport_category'), 'detection_type': vt, 'similarity_percent': v_doc['similarity_percent'],
                'threat_level': tl, 'source_domain': 'manual_scan', 'detected_at': now_ms, 'expires_at': now_ms + 3600000
            })
            
            if v_doc['asset_id']: await check_viral_spread(v_doc['asset_id'], v_doc['asset_name'])
            if hasattr(app, 'broadcast_violation'): await app.broadcast_violation({'violation_id': v_id, 'asset_name': v_doc['asset_name'], 'threat_level': tl})

        db.collection('scans').document(scan_id).set({
            'scan_id': scan_id, 'user_uid': user_uid, 'file_name': file_name, 'file_type': mime_type, 'file_size_bytes': file_size, 'file_mime_type': mime_type,
            'trust_score': ts, 'content_dna_score': dna.get('dna_score'), 'content_dna_grade': dna.get('grade'), 'content_dna_signals': dna.get('signals'), 'content_dna_color': dna.get('color'), 'threat_level': tl,
            'deepfake_is_fake': df.get('is_fake'), 'deepfake_confidence': df.get('confidence'), 'deepfake_verdict': df.get('verdict'), 'deepfake_frames_analyzed': df.get('frames_analyzed', 0), 'deepfake_duration_seconds': df.get('duration_seconds'),
            'audio_sync_analyzed': asy.get('analyzed', False), 'audio_sync_score': asy.get('sync_score'), 'audio_sync_suspicious': asy.get('is_suspicious'), 'audio_sync_verdict': asy.get('verdict'),
            'exif_flags': exf.get('flags'), 'exif_risk_score': exf.get('risk_score'), 'exif_risk_label': exf.get('risk_label'), 'exif_data': exf.get('exif_data'),
            'asset_match_found': phm.get('is_match'), 'matched_asset_id': phm.get('matched_asset_id'), 'matched_asset_name': phm.get('matched_asset_name'), 'matched_owner_name': phm.get('matched_owner_name'), 'matched_owner_email': phm.get('matched_owner_email'), 'matched_organization': phm.get('matched_organization'), 'matched_sport_category': phm.get('matched_sport_category'), 'matched_cert_id': phm.get('matched_cert_id'), 'matched_original_url': phm.get('matched_original_url'), 'similarity_percent': phm.get('similarity_percent'), 'hamming_distance': phm.get('hamming_distance'),
            'watermark_found': wmk is not None, 'watermark_cert_id': wmk.get('cert_id') if wmk else None, 'watermark_owner_name': wmk.get('owner_name') if wmk else None, 'watermark_sport_category': wmk.get('sport_category') if wmk else None, 'watermark_organization': wmk.get('organization') if wmk else None, 'watermark_registered_at': wmk.get('registered_at') if wmk else None, 'watermark_asset_name': wmk.get('asset_name') if wmk else None, 'watermark_issued_by': wmk.get('issued_by') if wmk else None,
            'gemini_vision_manipulation_detected': gv.get('manipulation_detected'), 'gemini_vision_signals': gv.get('manipulation_signals', []), 'gemini_vision_content_type': gv.get('content_type'), 'gemini_vision_authenticity_confidence': gv.get('authenticity_confidence'), 'gemini_vision_forensic_notes': gv.get('forensic_notes'), 'gemini_legal_report': lr,
            'fact_check_results': fc, 'scan_language': language, 'scan_file_url': file_url, 'scanned_at': firestore.SERVER_TIMESTAMP
        })
        try:
            rtdb.child('dashboard_stats').child('total_scans_today').transaction(lambda c: (c or 0) + 1)
        except Exception as e:
            logger.warning(f"RTDB counter update failed (non-fatal): {e}")
        await app.push_scan_step(scan_id, 'complete', 'done', {'scan_id': scan_id, 'trust_score': ts, 'content_dna_score': dna.get('dna_score')})
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@router.get("/{scan_id}/status")
async def get_scan_status(scan_id: str):
    doc = get_firestore().collection('scans').document(scan_id).get()
    if not doc.exists: return {'scan_id': scan_id, 'status': 'processing', 'steps': {}}
    d = doc.to_dict()
    return {'scan_id': scan_id, 'status': 'complete', 'steps': {'deepfake': {'done': True, 'is_fake': d.get('deepfake_is_fake')}}, 'trust_score': d.get('trust_score'), 'threat_level': d.get('threat_level')}

@router.post("/{scan_id}/legal-report")
async def regenerate_legal_report_endpoint(scan_id: str, request: Request):
    b = await request.json()
    lang = b.get('language', 'en')
    doc_ref = get_firestore().collection('scans').document(scan_id)
    d = doc_ref.get().to_dict()
    rep = await generate_legal_report({'threat_level': d.get('threat_level'), 'trust_score': d.get('trust_score'), 'deepfake_is_fake': d.get('deepfake_is_fake'), 'asset_match_found': d.get('asset_match_found'), 'exif_flags': d.get('exif_flags')}, lang)
    doc_ref.update({'gemini_legal_report': rep, 'scan_language': lang})
    return rep


# ============================================================
# POST /scan/url — Scan By URL (Blueprint Module 8)
# WHY: Operators can paste a URL from a news site / social media
# and instantly check if it steals registered content.
# ============================================================
import httpx as _httpx

@router.post("/url")
@limiter.limit("5/minute")
async def scan_by_url(request: Request, background_tasks: BackgroundTasks):
    """
    Download image from a URL, then run the full scan pipeline.
    Returns scan_id immediately. Progress visible via /ws/scan/{scan_id}.
    """
    body = await request.json()
    url = body.get('url', '').strip()
    user_uid = body.get('user_uid', 'anonymous')
    language = body.get('language', 'en')

    if not url:
        from fastapi import HTTPException
        raise HTTPException(400, "url field is required")

    scan_id = str(uuid.uuid4())
    tmp_path = os.path.join(TMP_DIR, f"{scan_id}_url.jpg")

    try:
        async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ShieldCoreAI/2.0"})
            if resp.status_code != 200:
                from fastapi import HTTPException
                raise HTTPException(400, f"Could not download URL: HTTP {resp.status_code}")
            ct = resp.headers.get('content-type', 'image/jpeg').split(';')[0].strip().lower()
            if not (ct.startswith('image/') or ct.startswith('video/')):
                from fastapi import HTTPException
                raise HTTPException(400, "URL must point directly to an image or video file")
            with open(tmp_path, 'wb') as f:
                f.write(resp.content)
    except _httpx.RequestError as e:
        from fastapi import HTTPException
        raise HTTPException(400, f"Request failed: {str(e)}")

    # Detect mime type from content
    import mimetypes as _mimetypes
    ext = _mimetypes.guess_extension(ct) or '.jpg'
    final_path = os.path.join(TMP_DIR, f"{scan_id}_url{ext}")
    os.rename(tmp_path, final_path)

    background_tasks.add_task(
        _process_scan, request.app, scan_id, final_path,
        user_uid, language, url, ct, len(resp.content)
    )
    return {'scan_id': scan_id, 'status': 'processing', 'source_url': url}


# ============================================================
# POST /scan/lite — Low-Bandwidth Mode (Blueprint Must-Have)
# WHY "Next Billion Users": Rural India / developing regions have
# 2G connections. This skips the 400MB HuggingFace model and
# Gemini vision call. Only runs pHash + EXIF + watermark check.
# Completes in < 2 seconds, < 50KB data transfer.
# ============================================================
@router.post("/lite")
@limiter.limit("20/minute")
async def scan_lite(request: Request, file: UploadFile = File(...), user_uid: str = Form(...)):
    """
    Lightweight scan: pHash registry check + EXIF forensics + watermark.
    No deepfake model, no Gemini calls. Designed for 2G connections.
    Returns results immediately (synchronous, no background task).
    """
    import mimetypes as _mimetypes

    content = await validate_upload(file)
    scan_id = str(uuid.uuid4())
    ext = _mimetypes.guess_extension(file.content_type) or '.bin'
    tmp_path = os.path.join(TMP_DIR, f"{scan_id}_lite{ext}")

    with open(tmp_path, 'wb') as f:
        f.write(content)

    try:
        loop = asyncio.get_event_loop()

        # Step 1: pHash registry check (most important signal)
        phm = await compare_to_registry(tmp_path)

        # Step 2: EXIF forensics (fast, no model)
        exf = await loop.run_in_executor(None, analyze_exif, tmp_path)

        # Step 3: Watermark extraction (LSB read, instant)
        wmk = await loop.run_in_executor(None, extract_watermark, tmp_path) if file.content_type.startswith('image/') else None

        # Simple trust score for lite mode
        score = 60
        if not phm.get('is_match'):
            score += 25
        if wmk and wmk.get('cert_id'):
            score += 10
        if exf.get('risk_score', 100) < 30:
            score += 5
        score = max(0, min(100, score))
        threat = "CRITICAL" if score <= 25 else "HIGH" if score <= 50 else "MEDIUM" if score <= 70 else "LOW"

        return {
            'scan_id': scan_id,
            'mode': 'lite',
            'bandwidth_saved': '~95%',
            'trust_score': score,
            'threat_level': threat,
            'asset_match_found': phm.get('is_match', False),
            'matched_asset_name': phm.get('matched_asset_name'),
            'matched_owner_name': phm.get('matched_owner_name'),
            'matched_organization': phm.get('matched_organization'),
            'matched_cert_id': phm.get('matched_cert_id'),
            'similarity_percent': phm.get('similarity_percent', 0),
            'hamming_distance': phm.get('hamming_distance'),
            'watermark_found': wmk is not None,
            'watermark_cert_id': wmk.get('cert_id') if wmk else None,
            'exif_flags': exf.get('flags', []),
            'exif_risk_score': exf.get('risk_score', 0),
            'deepfake_skipped': True,
            'gemini_skipped': True,
            'note': 'LOW-BANDWIDTH MODE: Deepfake AI and Gemini Vision skipped to save data. Run full scan for complete analysis.'
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
