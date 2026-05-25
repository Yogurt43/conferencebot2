# tests/test_db.py
import pytest
from unittest.mock import MagicMock
import db  # conftest.py sets env vars before this import

@pytest.fixture
def mock_sb(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(db, 'sb', mock)
    return mock

def test_get_participant_returns_none_when_not_found(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    result = db.get_participant(99999)
    assert result is None

def test_get_participant_returns_data(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'chat_id': 123, 'full_name': 'Test User', 'status': 'approved'}
    ]
    result = db.get_participant(123)
    assert result['chat_id'] == 123
    assert result['status'] == 'approved'

def test_upsert_participant(mock_sb):
    mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
        {'chat_id': 123, 'lang': 'uk'}
    ]
    result = db.upsert_participant({'chat_id': 123, 'lang': 'uk'})
    assert result['lang'] == 'uk'

def test_get_houses_for_gender(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'id': 'abc', 'name': 'Test House', 'gender': 'M', 'capacity': 12}
    ]
    result = db.get_houses_for_gender('M')
    assert len(result) == 1
    assert result[0]['gender'] == 'M'

def test_get_setting(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'key': 'schedule_text', 'value': 'Day 1: ...'}
    ]
    result = db.get_setting('schedule_text')
    assert result == 'Day 1: ...'

def test_get_setting_returns_empty_when_not_found(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    result = db.get_setting('missing_key')
    assert result == ''

def test_create_tentative_reservation(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
        {'id': 'res-1', 'house_id': 'h1', 'participant_id': 'p1', 'status': 'tentative'}
    ]
    result = db.create_tentative_reservation('h1', 'p1')
    assert result['status'] == 'tentative'
    # Verify the insert was called with status='tentative'
    call_args = mock_sb.table.return_value.insert.call_args[0][0]
    assert call_args['status'] == 'tentative'
    assert call_args['house_id'] == 'h1'
    assert call_args['participant_id'] == 'p1'

def test_confirm_reservation(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.confirm_reservation('p1')
    update_call = mock_sb.table.return_value.update.call_args[0][0]
    assert update_call == {'status': 'confirmed'}
    # Verify both eq filters are applied
    first_eq = mock_sb.table.return_value.update.return_value.eq.call_args
    assert first_eq[0] == ('participant_id', 'p1')
    second_eq = mock_sb.table.return_value.update.return_value.eq.return_value.eq.call_args
    assert second_eq[0] == ('status', 'tentative')

def test_release_tentative_reservation(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.release_tentative_reservation('p1')
    # Verify delete was called (not update)
    mock_sb.table.return_value.delete.assert_called_once()
    # Verify both eq filters are applied
    first_eq = mock_sb.table.return_value.delete.return_value.eq.call_args
    assert first_eq[0] == ('participant_id', 'p1')
    second_eq = mock_sb.table.return_value.delete.return_value.eq.return_value.eq.call_args
    assert second_eq[0] == ('status', 'tentative')
