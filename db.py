# db.py
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ─── Participants ──────────────────────────────────────────────────────────────

def get_participant(chat_id: int) -> dict | None:
    res = sb.table('participants').select('*').eq('chat_id', chat_id).execute()
    return res.data[0] if res.data else None

def upsert_participant(data: dict) -> dict:
    res = sb.table('participants').upsert(data, on_conflict='chat_id').execute()
    return res.data[0] if res.data else {}

def update_participant(chat_id: int, data: dict) -> dict:
    res = sb.table('participants').update(data).eq('chat_id', chat_id).execute()
    return res.data[0] if res.data else {}

def get_participants_by_status(status: str) -> list[dict]:
    res = sb.table('participants').select('*').eq('status', status).execute()
    return res.data

def get_all_participants() -> list[dict]:
    res = sb.table('participants').select('*').order('created_at').execute()
    return res.data

def delete_participant(chat_id: int) -> None:
    sb.table('participants').delete().eq('chat_id', chat_id).execute()

def delete_all_participants() -> None:
    sb.table('participants').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

def count_participants_by_status() -> dict:
    all_p = get_all_participants()
    counts = {'total': len(all_p), 'approved': 0, 'pending': 0, 'denied': 0}
    for p in all_p:
        if p['status'] == 'approved':
            counts['approved'] += 1
        elif p['status'] in ('pending_payment', 'pending_approval'):
            counts['pending'] += 1
        elif p['status'] == 'denied':
            counts['denied'] += 1
    return counts


# ─── Receipts ─────────────────────────────────────────────────────────────────

def save_receipt(participant_id: str, file_id: str) -> dict:
    res = sb.table('receipts').insert({
        'participant_id': participant_id,
        'file_id': file_id
    }).execute()
    return res.data[0] if res.data else {}

def get_latest_receipt(participant_id: str) -> dict | None:
    res = (sb.table('receipts')
             .select('*')
             .eq('participant_id', participant_id)
             .order('submitted_at', desc=True)
             .limit(1)
             .execute())
    return res.data[0] if res.data else None


# ─── Houses ───────────────────────────────────────────────────────────────────

def get_houses_for_gender(gender: str) -> list[dict]:
    res = sb.table('houses').select('*').eq('gender', gender).execute()
    return res.data

def get_all_houses() -> list[dict]:
    res = sb.table('houses').select('*').order('name').execute()
    return res.data

def get_house_by_name(name: str) -> dict | None:
    res = sb.table('houses').select('*').eq('name', name).execute()
    return res.data[0] if res.data else None

def get_house_by_id(house_id: str) -> dict | None:
    res = sb.table('houses').select('*').eq('id', house_id).execute()
    return res.data[0] if res.data else None

def add_house(name: str, gender: str, capacity: int) -> dict:
    res = sb.table('houses').insert({
        'name': name, 'gender': gender, 'capacity': capacity,
    }).execute()
    return res.data[0] if res.data else {}

def remove_house(house_id: str) -> None:
    sb.table('houses').delete().eq('id', house_id).execute()


# ─── House Reservations ────────────────────────────────────────────────────────

def get_reservation(participant_id: str) -> dict | None:
    res = (sb.table('house_reservations')
             .select('*, houses(*)')
             .eq('participant_id', participant_id)
             .execute())
    return res.data[0] if res.data else None

def get_house_occupancy(house_id: str) -> int:
    res = sb.table('house_reservations').select('id').eq('house_id', house_id).execute()
    return len(res.data)

def get_house_reservation_count(house_id: str) -> int:
    return get_house_occupancy(house_id)

def create_reservation(house_id: str, participant_id: str) -> dict:
    res = sb.table('house_reservations').insert({
        'house_id': house_id,
        'participant_id': participant_id
    }).execute()
    return res.data[0] if res.data else {}

def create_tentative_reservation(house_id: str, participant_id: str) -> dict:
    """Create a tentative reservation during registration. Confirmed on approval."""
    res = sb.table('house_reservations').insert({
        'house_id': house_id,
        'participant_id': participant_id,
        'status': 'tentative',
    }).execute()
    return res.data[0] if res.data else {}

def confirm_reservation(participant_id: str) -> None:
    """Upgrade a tentative reservation to confirmed on participant approval."""
    sb.table('house_reservations').update({'status': 'confirmed'}).eq(
        'participant_id', participant_id
    ).eq('status', 'tentative').execute()

def release_tentative_reservation(participant_id: str) -> None:
    """Delete any tentative reservation for a participant (on denial or re-entry)."""
    sb.table('house_reservations').delete().eq(
        'participant_id', participant_id
    ).eq('status', 'tentative').execute()

def delete_reservation(participant_id: str) -> None:
    sb.table('house_reservations').delete().eq('participant_id', participant_id).execute()

def move_reservation(participant_id: str, new_house_id: str) -> dict:
    res = (sb.table('house_reservations')
             .update({'house_id': new_house_id})
             .eq('participant_id', participant_id)
             .execute())
    return res.data[0] if res.data else {}

def count_housed_participants() -> int:
    res = sb.table('house_reservations').select('id').execute()
    return len(res.data)


# ─── Q&A ──────────────────────────────────────────────────────────────────────

def count_questions_by_participant(participant_id: str) -> int:
    res = sb.table('questions').select('id').eq('participant_id', participant_id).execute()
    return len(res.data)

def save_question(participant_id: str, text: str) -> dict:
    res = sb.table('questions').insert({
        'participant_id': participant_id, 'text': text
    }).execute()
    return res.data[0] if res.data else {}


# ─── Coordinator messages ──────────────────────────────────────────────────────

def save_message(participant_id: str, text: str) -> dict:
    res = sb.table('messages').insert({
        'participant_id': participant_id, 'text': text
    }).execute()
    return res.data[0] if res.data else {}


# ─── Bot settings ─────────────────────────────────────────────────────────────

def get_setting(key: str) -> str:
    res = sb.table('bot_settings').select('value').eq('key', key).execute()
    return res.data[0]['value'] if res.data else ''

def set_setting(key: str, value: str) -> None:
    sb.table('bot_settings').upsert({'key': key, 'value': value}).execute()

def is_paused(feature: str) -> bool:
    return get_setting(f'{feature}_paused') == 'true'

def get_admin_ids_from_db() -> list[int]:
    """Returns runtime admin IDs stored in bot_settings (in addition to ADMIN_IDS in config)."""
    raw = get_setting('admin_ids')
    if not raw:
        return []
    return [int(x) for x in raw.split(',') if x.strip().isdigit()]
