# utils.py
import db
from config import ADMIN_IDS, OWNER_ID


def validate_age(text: str) -> int | None:
    """Return integer age if valid (10–99), else None."""
    raw = text.strip()
    if not raw.isdigit() or len(raw) != 2:
        return None
    age = int(raw)
    return age if 10 <= age <= 99 else None


def format_house_button(house: dict, taken: int, lang: str = 'en') -> str:
    """Format a house's inline button label."""
    from strings import t
    name = house['name']
    cap = house['capacity']
    if taken >= cap:
        return t(lang, 'house_full_label', name=name)
    return t(lang, 'house_spots_label', name=name, taken=taken, capacity=cap)


def get_lang(participant: dict | None) -> str:
    """Return participant's language, defaulting to 'en'."""
    if not participant:
        return 'en'
    return participant.get('lang') or 'en'


def is_admin(chat_id: int) -> bool:
    """True if chat_id is owner, in static ADMIN_IDS, or in runtime DB admin list."""
    if chat_id == OWNER_ID or chat_id in ADMIN_IDS:
        return True
    try:
        return chat_id in db.get_admin_ids_from_db()
    except Exception:
        return False


def is_owner(chat_id: int) -> bool:
    """True only for the owner."""
    return chat_id == OWNER_ID
