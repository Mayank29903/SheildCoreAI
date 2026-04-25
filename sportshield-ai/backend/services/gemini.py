# SportShield AI | Google Solution Challenge 2026 | First Prize Target

"""Two distinct Gemini 2.0 Flash calls.
Vision: PIL Image object sent directly for multimodal analysis.
Legal: Structured JSON legal action plan in English/Hindi/Tamil."""

import asyncio
import json
import logging

import google.generativeai as genai
from PIL import Image

from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)
model = None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # We map explicitly to the experimental Flash model capable of blazing multimodal speed.
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    logger.warning("GEMINI_API_KEY not set. Gemini-powered analysis will use fallback responses.")

VISION_FALLBACK = {
    'manipulation_detected': False, 'manipulation_signals': [],
    'content_type': 'unknown', 'authenticity_confidence': 50,
    'forensic_notes': 'Gemini analysis unavailable'
}

LEGAL_FALLBACK = {
    'summary': 'Analysis unavailable', 'threat_level': 'UNKNOWN',
    'immediate_actions': ['Consult a legal professional'],
    'report_to': [{'authority': 'National Cyber Crime Portal', 'url': 'https://cybercrime.gov.in'}],
    'legal_sections': ['IT Act 2000', 'Copyright Act 1957'],
    'evidence_to_preserve': ['Original file', 'Upload timestamps'],
    'estimated_timeline': 'Consult legal counsel',
    'rights_impact': 'Unknown - seek legal advice'
}


async def analyze_image_with_gemini_vision(image_path: str) -> dict:
    """Send actual image bytes to Gemini, not just a text description."""
    if model is None:
        return VISION_FALLBACK

    prompt = '''Analyze this image for digital manipulation and authenticity.
    Respond ONLY with valid JSON (no markdown, no backticks):
    {"manipulation_detected": bool,
     "manipulation_signals": ["signal1", "signal2"],
     "content_type": "sports_photo|athlete_portrait|trophy|advertisement|screenshot|other",
     "authenticity_confidence": 0-100,
     "forensic_notes": "brief technical observation"}
    Look for: unnatural skin texture, eye reflection inconsistencies,
    hair boundary artifacts, compression artifacts at face boundaries,
    lighting inconsistencies, double edges, cloning artifacts.'''

    for _ in range(2):
        try:
            img = Image.open(image_path).convert('RGB')
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: model.generate_content([prompt, img]))

            txt = res.text.strip('` \n')
            if txt.startswith('json\n'):
                txt = txt[5:]
            return json.loads(txt)
        except Exception as e:
            logger.warning("Gemini vision error: %s", e)
            await asyncio.sleep(1)

    return VISION_FALLBACK


async def generate_legal_report(scan_data: dict, language: str = 'en') -> dict:
    """Generate a structured legal action plan in the requested language."""
    if model is None:
        return LEGAL_FALLBACK

    instructions = {
        'en': 'Respond entirely in English.',
        'hi': 'Respond entirely in Hindi script (Devanagari). All text must be in Hindi.',
        'ta': 'Respond entirely in Tamil script. All text must be in Tamil.'
    }
    lang = instructions.get(language, instructions['en'])
    ctx = json.dumps(scan_data, default=str)

    prompt = f'''{lang}
    Analyze this incident:
    {ctx}

    Respond ONLY with valid JSON formatting:
    {{"summary": "brief situation summary",
     "threat_level": "CRITICAL|HIGH|MEDIUM|LOW",
     "immediate_actions": ["action1", "action2", "action3"],
     "report_to": [{{"authority": "name", "url": "url", "how": "method"}}],
     "legal_sections": ["IT Act 2000 Section 66C", "Copyright Act 1957 Section 51"],
     "evidence_to_preserve": ["item1", "item2"],
     "estimated_timeline": "timeframe for legal action",
     "rights_impact": "economic impact description"}}

    Base legal insights around IT Act 2000 (Section 66C, 66D, 67), Copyright Act 1957 (Section 51, 55), or IPC (Section 465, 469).
    Reporting targets: National Cyber Crime Portal (https://cybercrime.gov.in), CERT-In (https://cert-in.org.in), Copyright Office of India (https://copyright.gov.in).'''

    for _ in range(2):
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
            txt = res.text.strip('` \n')
            if txt.startswith('json\n'):
                txt = txt[5:]
            return json.loads(txt)
        except Exception as e:
            logger.warning("Gemini legal format error: %s", e)
            await asyncio.sleep(1)

    return LEGAL_FALLBACK
