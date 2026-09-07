from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from actions.import_markdown import run
from lib.database import connect, initialize, list_symbols
from web.app import create_app


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "journal.sqlite3"
    initialize(path)
    return path


@pytest.fixture
def client(database):
    with TestClient(create_app(database)) as client:
        yield client


def test_create_browse_and_filter(client, database):
    assert "What did you dream?" in client.get("/").text
    for title, day, symbols in [("Earlier", "2025-01-01", "water, Water, bird"), ("Later", "2026-01-01", "water")]:
        response = client.post("/dreams", data={"title": title, "date": day, "body": "<script>alert(1)</script>\nA river.", "symbols": symbols})
        assert response.status_code == 200
        assert "Dream saved." in response.text
        assert "&lt;script&gt;" in response.text
        assert "<script>alert(1)</script>" not in response.text
    page = client.get("/").text
    assert page.index('>Later</p>') < page.index('>Earlier</p>')
    with connect(database) as db:
        assert [(s["slug"], s["count"]) for s in list_symbols(db)] == [("water", 2), ("bird", 1)]
    page = client.get("/?symbol=bird").text
    assert '>Earlier</p>' in page and '>Later</p>' not in page
    assert client.get("/dreams/9999").status_code == 404
    assert client.get("/symbols/missing").status_code == 404
    with TestClient(create_app(database)) as reopened:
        assert '>Later</p>' in reopened.get('/').text


def test_validation_and_htmx(client, database):
    data = {"title": "Keep this", "date": "bad", "body": "My dream"}
    response = client.post("/dreams", data=data)
    assert response.status_code == 422
    assert 'value="Keep this"' in response.text
    response = client.post("/dreams", data=data, headers={"HX-Request": "true"})
    assert response.status_code == 200 and 'role="alert"' in response.text
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM dreams").fetchone()[0] == 0
    response = client.post("/dreams", data={**data, "date": "2026-09-01"}, headers={"HX-Request": "true"})
    assert response.headers["HX-Location"].startswith("/dreams/")
    assert client.post("/dreams", data=data, headers={"Origin": "https://example.com"}).status_code == 403
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def make_journal(root):
    (root / "dreams").mkdir()
    (root / "symbols").mkdir()
    (root / "symbols/water.md").write_text('---\ntitle: Water\nsummary: A river\nassociations: [blue]\ninterpretations: [personal]\n---\nMy notes')
    dream = root / "dreams/2026-01-01 - river.md"
    dream.write_text('---\ntitle: River\ndate: 2026-01-01\nsymbols: [water, water, bird]\ncustom: preserved\n---\nA river dream')
    return dream


def test_import_repeat_update_preserve(tmp_path, database):
    dream = make_journal(tmp_path)
    original = dream.read_bytes()
    assert run(tmp_path, database)["dreams_added"] == 1
    assert run(tmp_path, database)["dreams_skipped"] == 1
    assert dream.read_bytes() == original
    with connect(database) as db:
        symbol = db.execute("SELECT * FROM symbols WHERE slug='water'").fetchone()
        assert symbol["body"] == "My notes" and 'personal' in symbol["metadata"]
        assert db.execute("SELECT COUNT(*) FROM dream_symbols").fetchone()[0] == 2
        assert 'preserved' in db.execute("SELECT metadata FROM dreams").fetchone()[0]
        db.execute("INSERT INTO dreams(title,date,body) VALUES ('Web dream','2026-02-01','Body')")
    dream.write_text(dream.read_text().replace('[water, water, bird]', '[bird]').replace('A river dream', 'Changed'))
    assert run(tmp_path, database)["dreams_updated"] == 1
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM dreams").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM dream_symbols").fetchone()[0] == 1
        assert db.execute("SELECT body FROM dreams WHERE source IS NOT NULL").fetchone()[0] == 'Changed'


def test_import_rolls_back(tmp_path, database):
    make_journal(tmp_path)
    (tmp_path / 'dreams/z-invalid.md').write_text('---\ndate: bad\n---\nInvalid')
    with pytest.raises(ValueError, match='z-invalid.md'):
        run(tmp_path, database)
    with connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM dreams').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM symbols').fetchone()[0] == 0


def test_symbol_detail_edit_and_reimport(client, database, tmp_path):
    import json
    make_journal(tmp_path)
    run(tmp_path, database)
    filtered = client.get('/?symbol=water').text
    assert 'href="/symbols/water/"' in filtered
    assert 'What did you dream?' in filtered
    assert 'href="/?symbol=water"' in filtered
    with connect(database) as db:
        dream_id = db.execute('SELECT id FROM dreams').fetchone()[0]
    assert 'href="/symbols/water/"' in client.get(f'/dreams/{dream_id}').text
    page = client.get('/symbols/water/').text
    assert 'A river dream' in page and 'My notes' in page and 'A river' in page
    assert '>blue</textarea>' in page and '>personal</textarea>' in page
    assert 'What did you dream?' not in page
    response = client.post('/symbols/water/', data={
        'associations': ' blue\n\nA memory, with commas\n<script>test</script>',
        'interpretations': 'My meaning',
    })
    assert response.status_code == 200
    assert 'Associations and interpretations saved.' in response.text
    assert '&lt;script&gt;test&lt;/script&gt;' in response.text
    with connect(database) as db:
        row = db.execute('SELECT * FROM symbol_reflections').fetchone()
        assert json.loads(row['associations']) == ['blue', 'A memory, with commas', '<script>test</script>']
        assert json.loads(row['interpretations']) == ['My meaning']
    symbol_file = tmp_path / 'symbols/water.md'
    symbol_file.write_text(symbol_file.read_text().replace('A river', 'Updated summary'))
    run(tmp_path, database)
    page = client.get('/symbols/water/').text
    assert 'Updated summary' in page and 'My meaning' in page
    response = client.post('/symbols/water/', data={'associations': '', 'interpretations': ''}, headers={'HX-Request': 'true'})
    assert response.headers['HX-Location'] == '/symbols/water/?saved=1'
    with TestClient(create_app(database)) as reopened:
        page = reopened.get('/symbols/water/').text
        assert 'My meaning' not in page and '>blue</textarea>' not in page
    assert client.get('/symbols/bird/').status_code == 200
    assert client.get('/?symbol=missing').status_code == 404
    assert client.post('/symbols/missing/', data={}).status_code == 404


def test_symbol_validation_and_empty_state(client, database):
    with connect(database) as db:
        db.execute("INSERT INTO symbols(slug,title) VALUES ('music','Music')")
    assert 'No dreams contain this symbol yet.' in client.get('/symbols/music/').text
    response = client.post('/symbols/music/', data={'associations': 'a' * 100001, 'interpretations': 'Keep this'})
    assert response.status_code == 422 and 'Keep this' in response.text
    with connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM symbol_reflections').fetchone()[0] == 0


def test_edit_dream(client, database, tmp_path):
    source = make_journal(tmp_path)
    run(tmp_path, database)
    with connect(database) as db:
        dream_id = db.execute('SELECT id FROM dreams').fetchone()[0]
    url = f'/dreams/{dream_id}/edit'
    assert f'href="{url}"' in client.get(f'/dreams/{dream_id}').text
    page = client.get(url).text
    assert 'value="River"' in page and 'A river dream</textarea>' in page
    assert 'value="bird, water"' in page and '>Cancel</a>' in page
    data = {'title': 'Remembered more', 'date': '2026-03-02', 'body': 'A river dream\nMore details.', 'symbols': 'garden, garden'}
    response = client.post(url, data=data)
    assert response.status_code == 200 and 'More details.' in response.text
    with connect(database) as db:
        row = db.execute('SELECT * FROM dreams').fetchone()
        assert row['id'] == dream_id and row['title'] == 'Remembered more' and row['date'] == '2026-03-02'
        assert db.execute('SELECT COUNT(*) FROM dreams').fetchone()[0] == 1
        assert [(s['slug'], s['count']) for s in list_symbols(db)] == [('garden', 1), ('bird', 0), ('water', 0)]
    response = client.post(url, data={**data, 'date': 'invalid', 'body': 'Keep my draft'})
    assert response.status_code == 422 and 'Keep my draft</textarea>' in response.text
    assert f'action="{url}"' in response.text
    assert 'More details.' in client.get(f'/dreams/{dream_id}').text
    source.write_text(source.read_text().replace('A river dream', 'Changed source'))
    assert run(tmp_path, database)['dreams_skipped'] == 1
    assert 'More details.' in client.get(f'/dreams/{dream_id}').text
    response = client.post(url, data={**data, 'symbols': ''}, headers={'HX-Request': 'true'})
    assert response.headers['HX-Location'] == f'/dreams/{dream_id}?saved=1'
    with TestClient(create_app(database)) as reopened:
        assert 'No symbols yet' in reopened.get(f'/dreams/{dream_id}').text
    assert client.get('/dreams/99999/edit').status_code == 404
    assert client.post('/dreams/99999/edit', data=data).status_code == 404
