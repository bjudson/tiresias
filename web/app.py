import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from lib.database import connect, database_path, initialize, list_dreams, list_symbols, set_symbols, slugify

ROOT = Path(__file__).parent


def create_app(database=None):
    db_path = database if database is not None else database_path()

    @asynccontextmanager
    async def lifespan(app):
        initialize(db_path)
        with connect(db_path) as db:
            db.execute("UPDATE claude_jobs SET status='failed', error='Server restarted before this action finished. Completed results are preserved.' WHERE status='running'")
        yield

    app = FastAPI(title="Tiresias", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=ROOT / "templates")

    @app.middleware("http")
    async def local_requests(request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or (origin and urlsplit(origin).netloc != request.headers.get("host")):
                return HTMLResponse("Cross-origin requests are not allowed.", status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def render(request, dream_id=None, symbol_slug=None, values=None, error=None, status=200, editing=False):
        with connect(db_path) as db:
            selected = None
            symbol = None
            tags = []
            if dream_id is not None:
                selected = db.execute("SELECT * FROM dreams WHERE id=?", (dream_id,)).fetchone()
                if selected is None:
                    raise HTTPException(404, "Dream not found")
                tags = db.execute("""SELECT s.* FROM symbols s JOIN dream_symbols ds ON s.slug=ds.symbol_slug
                    WHERE ds.dream_id=? ORDER BY s.title COLLATE NOCASE""", (dream_id,)).fetchall()
            if symbol_slug is not None:
                symbol = db.execute("SELECT * FROM symbols WHERE slug=?", (symbol_slug,)).fetchone()
                if symbol is None:
                    raise HTTPException(404, "Symbol not found")
            if editing and values is None:
                values = {"title": selected["title"], "date": selected["date"],
                          "body": selected["body"], "symbols": ", ".join(tag["slug"] for tag in tags)}
            context = dict(editing=editing, dreams=list_dreams(db, symbol_slug), symbols=list_symbols(db),
                           selected=selected, symbol=symbol, tags=tags, error=error,
                           values=values or {"date": date.today().isoformat()}, saved=request.query_params.get("saved"))
        return templates.TemplateResponse(request=request, name="index.html", context=context, status_code=status)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, symbol: str | None = None):
        return render(request, symbol_slug=symbol)

    @app.get("/dreams/{dream_id}", response_class=HTMLResponse)
    def detail(request: Request, dream_id: int):
        return render(request, dream_id=dream_id)

    @app.get("/dreams/{dream_id}/edit", response_class=HTMLResponse)
    def edit(request: Request, dream_id: int):
        return render(request, dream_id=dream_id, editing=True)

    def render_symbol(request, slug, values=None, error=None, status=200):
        with connect(db_path) as db:
            symbol = db.execute("SELECT * FROM symbols WHERE slug=?", (slug,)).fetchone()
            if symbol is None:
                raise HTTPException(404, "Symbol not found")
            metadata = json.loads(symbol["metadata"])
            reflections = db.execute("SELECT * FROM symbol_reflections WHERE symbol_slug=?", (slug,)).fetchone()
            if values is None:
                values = {}
                for field in ("associations", "interpretations"):
                    entries = json.loads(reflections[field]) if reflections else metadata.get(field, [])
                    values[field] = "\n".join(str(entry) for entry in entries) if isinstance(entries, list) else str(entries or "")
            context = dict(symbol=symbol, dreams=list_dreams(db, slug), values=values,
                           error=error, saved=request.query_params.get("saved"))
        return templates.TemplateResponse(request=request, name="symbol.html", context=context, status_code=status)

    @app.get("/symbols/{slug}/", response_class=HTMLResponse)
    def symbol_detail(request: Request, slug: str):
        return render_symbol(request, slug)

    @app.post("/symbols/{slug}/", response_class=HTMLResponse)
    def save_symbol(request: Request, slug: str, associations: str = Form(""), interpretations: str = Form("")):
        values = dict(associations=associations, interpretations=interpretations)
        if any(len(value) > 100_000 for value in values.values()):
            return render_symbol(request, slug, values, "Keep each field under 100,000 characters.",
                                 200 if request.headers.get("HX-Request") else 422)
        with connect(db_path) as db:
            if db.execute("SELECT 1 FROM symbols WHERE slug=?", (slug,)).fetchone() is None:
                raise HTTPException(404, "Symbol not found")
            entries = [json.dumps([line.strip() for line in value.splitlines() if line.strip()], ensure_ascii=False)
                       for value in values.values()]
            db.execute("""INSERT INTO symbol_reflections VALUES (?, ?, ?)
                ON CONFLICT(symbol_slug) DO UPDATE SET associations=excluded.associations,
                interpretations=excluded.interpretations""", (slug, *entries))
        url = f"/symbols/{quote(slug, safe='')}/?saved=1"
        if request.headers.get("HX-Request"):
            return HTMLResponse(headers={"HX-Location": url})
        return RedirectResponse(url, status_code=303)

    def start_job(request, background, kind, dream_id=None):
        with connect(db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            if dream_id is not None and db.execute("SELECT 1 FROM dreams WHERE id=?", (dream_id,)).fetchone() is None:
                raise HTTPException(404, "Dream not found")
            active = db.execute("SELECT id FROM claude_jobs WHERE status='running'").fetchone()
            if active:
                job_id = active['id']
            else:
                ids = [dream_id] if dream_id is not None else [d['id'] for d in list_dreams(db)]
                job_id = db.execute("INSERT INTO claude_jobs(kind,dream_ids) VALUES (?,?)", (kind, json.dumps(ids))).lastrowid
                from lib.claude_jobs import run
                background.add_task(run, db_path, job_id)
        url = f"/claude/{job_id}"
        if request.headers.get('HX-Request'):
            return HTMLResponse(headers={'HX-Location': url})
        return RedirectResponse(url, status_code=303)

    @app.post('/dreams/{dream_id}/extract')
    def extract(request: Request, dream_id: int, background: BackgroundTasks):
        return start_job(request, background, 'extract', dream_id)

    @app.post('/audit')
    def audit(request: Request, background: BackgroundTasks):
        return start_job(request, background, 'audit')

    @app.get('/claude/{job_id}', response_class=HTMLResponse)
    def claude_result(request: Request, job_id: int):
        with connect(db_path) as db:
            job = db.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
            if job is None:
                raise HTTPException(404, 'Action not found')
        return templates.TemplateResponse(request=request, name='claude.html', context={
            'job': job, 'results': json.loads(job['results']), 'total': len(json.loads(job['dream_ids']))})

    def save_dream(request, title, dream_date, body, symbols, dream_id=None):
        if dream_id is not None:
            with connect(db_path) as db:
                if db.execute("SELECT 1 FROM dreams WHERE id=?", (dream_id,)).fetchone() is None:
                    raise HTTPException(404, "Dream not found")
        values = {"title": title, "date": dream_date, "body": body, "symbols": symbols}
        error = None
        try:
            parsed_date = date.fromisoformat(dream_date).isoformat()
        except ValueError:
            error = "Enter a valid dream date."
        if not title.strip() or not body.strip():
            error = "Please add a title and dream narrative."
        if len(title) > 200 or len(body) > 100_000 or len(symbols) > 2000:
            error = "Please keep the title under 200 characters, narrative under 100,000, and symbols under 2,000."
        slugs = [slugify(s) for s in symbols.split(",") if s.strip()]
        if any(not s for s in slugs):
            error = "Each symbol needs at least one letter or number."
        if error:
            # HTMX swaps successful responses; regular submissions get a validation status.
            return render(request, dream_id=dream_id, editing=dream_id is not None, values=values, error=error, status=200 if request.headers.get("HX-Request") else 422)
        with connect(db_path) as db:
            if dream_id is None:
                dream_id = db.execute("INSERT INTO dreams(title,date,body) VALUES (?,?,?)",
                                      (title.strip(), parsed_date, body.strip())).lastrowid
            else:
                db.execute("UPDATE dreams SET title=?,date=?,body=? WHERE id=?",
                           (title.strip(), parsed_date, body.strip(), dream_id))
                db.execute("INSERT OR IGNORE INTO dream_edits VALUES (?)", (dream_id,))
            set_symbols(db, dream_id, slugs)
        url = f"/dreams/{dream_id}?saved=1"
        if request.headers.get("HX-Request"):
            return HTMLResponse(headers={"HX-Location": url})
        return RedirectResponse(url, status_code=303)

    @app.post("/dreams", response_class=HTMLResponse)
    def add(request: Request, title: str = Form(""), dream_date: str = Form("", alias="date"),
            body: str = Form(""), symbols: str = Form("")):
        return save_dream(request, title, dream_date, body, symbols)

    @app.post("/dreams/{dream_id}/edit", response_class=HTMLResponse)
    def update(request: Request, dream_id: int, title: str = Form(""),
               dream_date: str = Form("", alias="date"), body: str = Form(""), symbols: str = Form("")):
        return save_dream(request, title, dream_date, body, symbols, dream_id)

    return app


app = create_app()
