# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""
Analytics route — provides real 24-hour hourly chart data for the Dashboard.
WHY: The Recharts 24hr line chart in Dashboard.jsx needs this endpoint to work.
Previously 'violations_by_hour' returned a single dummy entry.
Now it builds a real 24-bucket histogram from Firestore violation timestamps.
"""

import time
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from config.firebase import get_firestore, get_rtdb

logger = logging.getLogger(__name__)
router = APIRouter()
_cache = {'data': None, 'ts': 0}


def _build_hourly_buckets(violations: list) -> list:
    """
    Build a 24-bucket histogram of violations (one per hour, last 24h).
    Returns: [{'hour': 'HH:00', 'violations': N, 'deepfakes': N, 'theft': N}, ...]
    WHY 24 BUCKETS: Recharts LineChart needs labelled x-axis points.
    """
    now = datetime.now(timezone.utc)
    buckets = {}
    for i in range(23, -1, -1):
        dt = now - timedelta(hours=i)
        label = dt.strftime('%H:00')
        buckets[label] = {'hour': label, 'violations': 0, 'deepfakes': 0, 'theft': 0}

    for v in violations:
        try:
            detected = v.get('detected_at')
            if not detected:
                continue
            # Firestore timestamps come back as datetime objects
            if hasattr(detected, 'strftime'):
                dt = detected
            elif hasattr(detected, 'timestamp'):
                dt = datetime.fromtimestamp(detected.timestamp(), tz=timezone.utc)
            else:
                continue

            age_hours = (now - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else now - dt).total_seconds() / 3600
            if age_hours > 24:
                continue

            label = dt.strftime('%H:00')
            if label in buckets:
                buckets[label]['violations'] += 1
                dtype = v.get('detection_type', 'theft')
                if dtype == 'deepfake':
                    buckets[label]['deepfakes'] += 1
                else:
                    buckets[label]['theft'] += 1
        except Exception:
            continue

    return list(buckets.values())


@router.get("/")
async def get_analytics():
    now = time.time()
    if _cache['data'] and (now - _cache['ts'] < 30):
        return _cache['data']

    try:
        db = get_firestore()
        rtdb = get_rtdb()

        assets = list(db.collection('assets').stream())
        violations = list(db.collection('violations').stream())
        violation_dicts = [v.to_dict() for v in violations]

        # Threat type breakdown
        threats = {'deepfake': 0, 'theft': 0, 'both': 0}
        sport_bd = {}
        domain_counts = {}
        total_loss = 0.0

        for v in violation_dicts:
            t = v.get('detection_type', 'theft')
            if t in threats:
                threats[t] += 1

            s = v.get('sport_category', 'Other')
            sport_bd[s] = sport_bd.get(s, 0) + 1

            domain = v.get('source_domain', 'unknown')
            if domain and domain != 'manual_scan':
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            total_loss += float(v.get('estimated_loss_usd', 0) or 0)

        # Top 5 infringing domains
        top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_domains_list = [{'domain': d, 'count': c} for d, c in top_domains]

        # Recent scans (last 10)
        try:
            recent_scan_docs = list(db.collection('scans').order_by('scanned_at', direction='DESCENDING').limit(10).stream())
            recent_scans = [{
                'scan_id': d.id,
                'file_name': d.to_dict().get('file_name', 'unknown'),
                'trust_score': d.to_dict().get('trust_score', 0),
                'threat_level': d.to_dict().get('threat_level', 'LOW'),
                'deepfake_detected': d.to_dict().get('deepfake_is_fake', False),
                'asset_match': d.to_dict().get('asset_match_found', False),
            } for d in recent_scan_docs]
        except Exception:
            recent_scans = []

        # 24-hour hourly chart data
        hourly = _build_hourly_buckets(violation_dicts)

        # Rights value from assets
        rights = sum(a.to_dict().get('estimated_rights_value_usd', 0) for a in assets)

        # Try to get real-time scan count from RTDB
        scans_today = 0
        try:
            snap = rtdb.child('dashboard_stats/total_scans_today').get()
            scans_today = snap or 0
        except Exception:
            scans_today = len(recent_scans)

        ret = {
            'total_assets': len(assets),
            'assets_protected': len(assets),
            'scans_today': scans_today,
            'total_scans_today': scans_today,
            'violations_today': len(violation_dicts),
            'violations_total': len(violation_dicts),
            'active_violations': len(violation_dicts),
            'rights_value_protected_usd': rights,
            'threats_by_type': threats,
            'sport_breakdown': sport_bd,
            'top_infringing_domains': top_domains_list,
            'violations_by_hour': hourly,
            'recent_scans': recent_scans,
            'total_rights_value_protected_usd': rights,
            'total_estimated_loss_usd': total_loss,
            'most_targeted_sport': max(sport_bd, key=sport_bd.get) if sport_bd else 'N/A'
        }

        _cache['data'] = ret
        _cache['ts'] = now
        return ret

    except Exception as e:
        logger.error(f"get_analytics failed: {e}")
        # Return minimal safe fallback so dashboard doesn't crash
        return {
            'total_assets': 0, 'scans_today': 0, 'violations_today': 0, 'violations_total': 0,
            'threats_by_type': {'deepfake': 0, 'theft': 0, 'both': 0},
            'sport_breakdown': {}, 'top_infringing_domains': [],
            'violations_by_hour': [{'hour': f'{h:02d}:00', 'violations': 0, 'deepfakes': 0, 'theft': 0} for h in range(24)],
            'recent_scans': [], 'total_rights_value_protected_usd': 0,
            'total_estimated_loss_usd': 0, 'most_targeted_sport': 'N/A',
            'error': str(e)
        }
