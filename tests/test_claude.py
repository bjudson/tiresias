import json

import pytest
from fastapi.testclient import TestClient

from lib import llm
from lib.database import connect
from web.app import create_app


@pytest.fixture
def journal(tmp_path):
    database = tmp_path / 'journal.sqlite3'
    with TestClient(create_app(database)) as client:
        for title in ['First', 'Second']:
            client.post('/dreams', data={'title': title, 'date': '2026-01-01', 'body': title + ' narrative', 'symbols': 'water'})
        yield client, database


def test_extract(journal, monkeypatch):
    client, database = journal
    monkeypatch.setattr(llm, 'extract_symbols', lambda body, inventory: {
        'matched': ['water'], 'new': [{'slug': 'red-door', 'title': 'Red door', 'summary': 'A red door'}]})
    response = client.post('/dreams/1/extract', headers={'HX-Request': 'true'})
    page = client.get(response.headers['HX-Location']).text
    assert 'red-door' in page and 'Already associated: water' in page and 'Complete' in page
    with connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM dream_symbols WHERE dream_id=1').fetchone()[0] == 2
        assert db.execute('SELECT 1 FROM dream_edits WHERE dream_id=1').fetchone()
    assert 'No new symbol connections found.' in client.post('/dreams/1/extract').text
    assert client.post('/dreams/999/extract').status_code == 404


def test_audit_partial_failure(journal, monkeypatch):
    client, database = journal
    with connect(database) as db:
        db.execute("INSERT INTO symbols(slug,title) VALUES ('bird','Bird')")
    calls = []
    def audit(body, tagged, inventory):
        calls.append(body)
        if len(calls) == 2:
            raise RuntimeError('private response')
        return ['bird', 'bird', 'water']
    monkeypatch.setattr(llm, 'audit_symbols', audit)
    page = client.post('/audit').text
    assert len(calls) == 2 and 'Stopped' in page and 'bird' in page
    assert 'private response' not in page
    with connect(database) as db:
        job = db.execute('SELECT * FROM claude_jobs').fetchone()
        assert job['status'] == 'failed'
        result = json.loads(job['results'])[0]
        assert result['added'] == ['bird']
        assert db.execute("SELECT COUNT(*) FROM dream_symbols WHERE symbol_slug='bird'").fetchone()[0] == 1


def test_invalid_and_stale_results(journal, monkeypatch):
    client, database = journal
    monkeypatch.setattr(llm, 'audit_symbols', lambda *args: ['nonexistent'])
    assert 'outside the inventory' in client.post('/audit').text
    def extract(*args):
        with connect(database) as db:
            db.execute("UPDATE dreams SET body='Updated while waiting' WHERE id=1")
        return {'matched': [], 'new': [{'slug': 'bird', 'title': 'Bird', 'summary': 'A bird'}]}
    monkeypatch.setattr(llm, 'extract_symbols', extract)
    assert 'Dream changed during the request' in client.post('/dreams/1/extract').text
    with connect(database) as db:
        assert db.execute("SELECT 1 FROM symbols WHERE slug='bird'").fetchone() is None


def test_audit_success_and_running_dedup(journal, monkeypatch):
    client, database = journal
    calls = []
    monkeypatch.setattr(llm, 'audit_symbols', lambda *args: calls.append(args) or [])
    assert '2 of 2 dreams checked' in client.post('/audit').text
    assert len(calls) == 2
    with connect(database) as db:
        job_id = db.execute("INSERT INTO claude_jobs(kind,dream_ids) VALUES ('audit','[1,2]')").lastrowid
    response = client.post('/audit', headers={'HX-Request': 'true'})
    assert response.headers['HX-Location'] == f'/claude/{job_id}' and len(calls) == 2
    assert 'every 2s' in client.get(f'/claude/{job_id}').text
