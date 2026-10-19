import json
import logging
from pathlib import Path

from typing import Optional, Union

logger = logging.getLogger(__name__)

PREFS_FILE = Path(__file__).resolve().parent.parent / "user_preferences.json"

def _load_prefs() -> dict:
    if not PREFS_FILE.exists():
        return {}
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading user preferences: {e}")
        return {}

def _save_prefs(prefs: dict):
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error saving user preferences: {e}")

def get_user_lang(chat_id: Union[int, str]) -> Optional[str]:
    """Foydalanuvchi tanlagan tilni qaytaradi (tanlanmagan bo'lsa None)"""
    prefs = _load_prefs()
    return prefs.get(str(chat_id))

def set_user_lang(chat_id: Union[int, str], lang: str):
    """Foydalanuvchi tilini saqlaydi ('ru' yoki 'en')"""
    prefs = _load_prefs()
    prefs[str(chat_id)] = lang
    _save_prefs(prefs)
