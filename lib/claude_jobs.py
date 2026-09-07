"""Persisted results for sequential Claude work on the SQLite journal."""
import json
import re

from lib import llm
from lib.database import connect, list_symbols


class InvalidResult(ValueError):
    pass


def slugs(value):
    if not isinstance(value, list) or any(not isinstance(s, str) or not re.fullmatch(r'[\w]+(?:-[\w]+)*', s) for s in value):
        raise InvalidResult('Claude returned an invalid symbol list.')
    return list(dict.fromkeys(value))


def run(database, job_id):
    with connect(database) as db:
        job = db.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
        dreams = json.loads(job['dream_ids'])
    results = []
    try:
        for dream_id in dreams:
            with connect(database) as db:
                dream = db.execute('SELECT * FROM dreams WHERE id=?', (dream_id,)).fetchone()
                inventory = [dict(s) for s in list_symbols(db)]
                tagged = [r[0] for r in db.execute('SELECT symbol_slug FROM dream_symbols WHERE dream_id=?', (dream_id,))]
            if dream is None:
                continue
            known = {s['slug'] for s in inventory}
            new = []
            if job['kind'] == 'extract':
                response = llm.extract_symbols(dream['body'], inventory)
                if not isinstance(response, dict) or 'matched' not in response or 'new' not in response:
                    raise InvalidResult('Claude returned an invalid extraction response.')
                matched = slugs(response['matched'])
                new = response['new']
                if not isinstance(new, list):
                    raise InvalidResult('Claude returned invalid new symbols.')
                for symbol in new:
                    if not isinstance(symbol, dict) or any(not isinstance(symbol.get(k), str) or not symbol[k].strip() for k in ('slug', 'title', 'summary')):
                        raise InvalidResult('Claude returned an incomplete symbol.')
                    slugs([symbol['slug']])
                candidates = list(dict.fromkeys(matched + [s['slug'] for s in new]))
                if set(matched) - known:
                    raise InvalidResult('Claude matched symbols outside the inventory.')
            else:
                candidates = slugs(llm.audit_symbols(dream['body'], tagged, inventory))
                if set(candidates) - known:
                    raise InvalidResult('Claude suggested audit symbols outside the inventory.')
            with connect(database) as db:
                db.execute('BEGIN IMMEDIATE')
                current = db.execute('SELECT * FROM dreams WHERE id=?', (dream_id,)).fetchone()
                current_tags = {r[0] for r in db.execute('SELECT symbol_slug FROM dream_symbols WHERE dream_id=?', (dream_id,))}
                changed = current is None or any(current[k] != dream[k] for k in ('body', 'title', 'date')) or current_tags != set(tagged)
                added, created = [], []
                if not changed:
                    for symbol in new:
                        cursor = db.execute('INSERT OR IGNORE INTO symbols(slug,title,summary) VALUES (?,?,?)',
                                            (symbol['slug'], symbol['title'], symbol['summary']))
                        if cursor.rowcount:
                            created.append(symbol['slug'])
                    for slug in candidates:
                        if slug not in current_tags:
                            db.execute('INSERT OR IGNORE INTO dream_symbols VALUES (?,?)', (dream_id, slug))
                            added.append(slug)
                    if added:
                        db.execute('INSERT OR IGNORE INTO dream_edits VALUES (?)', (dream_id,))
                results.append(dict(id=dream_id, title=dream['title'], added=added, created=created,
                                    existing=[s for s in candidates if s in current_tags], skipped=changed))
                db.execute('UPDATE claude_jobs SET results=? WHERE id=?', (json.dumps(results), job_id))
        with connect(database) as db:
            db.execute("UPDATE claude_jobs SET status='complete' WHERE id=?", (job_id,))
    except Exception as exc:
        # Do not expose provider response bodies or journal text in error messages.
        import anthropic
        if isinstance(exc, anthropic.AuthenticationError):
            error = 'Claude authentication failed. Check ANTHROPIC_API_KEY in .env.'
        elif isinstance(exc, anthropic.RateLimitError):
            error = 'Claude rate limit reached. Try again later.'
        elif isinstance(exc, InvalidResult):
            error = str(exc)
        else:
            error = 'Claude could not finish this action. Check your API key, model access, and connection, then try again.'
        with connect(database) as db:
            db.execute("UPDATE claude_jobs SET status='failed', error=? WHERE id=?", (error, job_id))
