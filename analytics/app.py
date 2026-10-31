"""Private, self-hosted analytics for a Hugo blog. No visitor IP or fingerprint stored."""
import os
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse
from collections import defaultdict

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

SITE_ORIGIN = os.environ.get("SITE_ORIGIN", "https://bassettolab.com").rstrip("/")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
ADMIN_EMAILS = {x.strip().lower() for x in os.environ.get("ADMIN_EMAILS", "").split(",") if x.strip()}
DATABASE = os.environ.get("ANALYTICS_DB", "./analytics.sqlite3")
SECRET = os.environ["SESSION_SECRET"]
CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site="lax", https_only=True)
app.add_middleware(CORSMiddleware, allow_origins=[SITE_ORIGIN], allow_credentials=False,
                   allow_methods=["POST"], allow_headers=["Content-Type"])
oauth = OAuth()
oauth.register(name="google", client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
               server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
               client_kwargs={"scope": "openid email profile"})

def connection():
    db = sqlite3.connect(DATABASE, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS pageviews (
        id INTEGER PRIMARY KEY,
        path TEXT NOT NULL,
        title TEXT NOT NULL,
        viewed_at TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_viewed_at ON pageviews(viewed_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_path ON pageviews(path)")
    return db

class View(BaseModel):
    path: str = Field(min_length=1, max_length=512)
    title: str = Field(default="", max_length=256)

@app.post("/api/view", status_code=204)
async def record(view: View, request: Request):
    # Browser Origin restricts cross-site use; API does not store personal identifiers.
    if request.headers.get("origin", "").rstrip("/") != SITE_ORIGIN:
        raise HTTPException(status_code=403)
    path = urlparse(view.path).path
    if not path.startswith("/") or path.startswith("//"):
        raise HTTPException(status_code=400)
    with connection() as db:
        db.execute("INSERT INTO pageviews(path,title,viewed_at) VALUES (?,?,?)",
                   (path, view.title, datetime.now(timezone.utc).isoformat()))
    return None

@app.get("/login")
async def login(request: Request):
    if not ADMIN_EMAILS:
        raise HTTPException(503, "ADMIN_EMAILS not configured")
    return await oauth.google.authorize_redirect(request, PUBLIC_URL + "/auth")

@app.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo", {})
    email = (user.get("email") or "").lower()
    if user.get("email_verified") is not True or email not in ADMIN_EMAILS:
        request.session.clear()
        raise HTTPException(403)
    request.session["admin"] = email
    return RedirectResponse("/admin", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

def assert_admin(request):
    if request.session.get("admin") not in ADMIN_EMAILS:
        raise HTTPException(401)

@app.get("/api/stats")
async def stats(request: Request):
    assert_admin(request)
    with connection() as db:
        total = db.execute("SELECT count(*) FROM pageviews").fetchone()[0]
        today = db.execute("""SELECT count(*) FROM pageviews
            WHERE substr(viewed_at,1,10)=?""", (datetime.now(timezone.utc).date().isoformat(),)).fetchone()[0]
        ranking = db.execute("""SELECT path, MAX(title) AS title, COUNT(*) AS views
            FROM pageviews GROUP BY path ORDER BY views DESC, path LIMIT 100""").fetchall()
        daily = db.execute("""SELECT substr(viewed_at,1,10), count(*)
            FROM pageviews GROUP BY substr(viewed_at,1,10) ORDER BY 1 DESC LIMIT 30""").fetchall()
    return {"total":total,"today":today,
            "ranking":[{"path":r[0],"title":r[1],"views":r[2]} for r in ranking],
            "daily":[{"date":d[0],"views":d[1]} for d in reversed(daily)]}

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    if request.session.get("admin") not in ADMIN_EMAILS:
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>BassettoLab — Admin</title>
<style>body{font-family:system-ui;background:#101412;color:#e5eee8;margin:0}
main{width:min(1100px,90%);margin:3rem auto}header{display:flex;justify-content:space-between;align-items:center}
a{color:#a6d5bf}section{background:#1c2420;border:1px solid #344039;border-radius:8px;padding:1.3rem}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem}
strong{font-size:2rem}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:.8rem;border-bottom:1px solid #344039}
td:last-child,th:last-child{text-align:right} .muted{color:#a4b1a8}
@media(max-width:600px){.cards{grid-template-columns:1fr}}</style></head>
<body><main><header><h1>BassettoLab · Analytics</h1><a href="/logout">Sair</a></header>
<div class="cards"><section><div class="muted">Total de visualizações</div><strong id="total">—</strong></section>
<section><div class="muted">Visualizações hoje (UTC)</div><strong id="today">—</strong></section></div>
<h2>Artigos mais lidos</h2><section><table><thead><tr><th>Artigo</th><th>Visualizações</th></tr></thead>
<tbody id="ranking"></tbody></table></section>
<h2>Últimos 30 dias com visitas</h2><section><table><thead><tr><th>Data (UTC)</th><th>Visualizações</th></tr></thead><tbody id="daily"></tbody></table></section>
<p class="muted">Visualizações de página, não visitantes únicos. Sem IP, cookies de rastreamento ou identificação dos leitores.</p>
</main><script>
function row(body,left,right){let tr=document.createElement("tr"),a=document.createElement("td"),b=document.createElement("td");a.textContent=left;b.textContent=right;tr.append(a,b);body.append(tr)}
fetch("/api/stats",{credentials:"same-origin"}).then(r=>{if(!r.ok)throw Error("Falha de acesso");return r.json()}).then(d=>{
document.getElementById("total").textContent=d.total.toLocaleString("pt-BR");
document.getElementById("today").textContent=d.today.toLocaleString("pt-BR");
d.ranking.forEach(x=>row(document.getElementById("ranking"),x.title||x.path,x.views.toLocaleString("pt-BR")));
d.daily.forEach(x=>row(document.getElementById("daily"),x.date,x.views.toLocaleString("pt-BR")));
}).catch(()=>{document.getElementById("ranking").textContent="Falha ao carregar dados";});
</script></body></html>""")
