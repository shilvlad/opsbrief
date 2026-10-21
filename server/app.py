"""OpsBrief VPS: voice-safe summary ingestion and Alice webhook."""
import hmac
import json
import os
import sqlite3
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

app = FastAPI(title="OpsBrief")
DB_PATH = Path(os.getenv("OPSBRIEF_DB", "/data/opsbrief.sqlite3"))
UPLOAD_TOKEN = os.getenv("OPSBRIEF_UPLOAD_TOKEN", "")
SKILL_ID = os.getenv("OPSBRIEF_ALICE_SKILL_ID", "")
WEBHOOK_SECRET = os.getenv("OPSBRIEF_WEBHOOK_SECRET", "")
MAX_AGE_HOURS = int(os.getenv("OPSBRIEF_MAX_AGE_HOURS", "30"))
ALLOWED_USER_IDS = {x.strip() for x in os.getenv("OPSBRIEF_ALICE_ALLOWED_USER_IDS", "").split(",") if x.strip()}


class VoiceSummary(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    timezone: str = Field(max_length=80)
    meetings: list[str] = Field(max_length=30)
    recommendations: list[str] = Field(max_length=10)


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS briefs
                    (id INTEGER PRIMARY KEY CHECK (id=1),
                     payload TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    return conn


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/brief")
def upload(payload: VoiceSummary, authorization: str | None = Header(default=None)):
    if not UPLOAD_TOKEN or not authorization or not hmac.compare_digest(
        authorization, "Bearer " + UPLOAD_TOKEN
    ):
        raise HTTPException(401, "Unauthorized")
    with db() as conn:
        conn.execute(
            "INSERT INTO briefs (id,payload,updated_at) VALUES (1,?,?) "
            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (payload.model_dump_json(), datetime.now(timezone.utc).isoformat()),
        )
    return {"accepted": True}


def latest():
    with db() as conn:
        row = conn.execute("SELECT payload, updated_at FROM briefs WHERE id=1").fetchone()
    if not row:
        return None
    saved = datetime.fromisoformat(row[1])
    hours = (datetime.now(timezone.utc) - saved).total_seconds() / 3600
    if not 0 <= hours <= MAX_AGE_HOURS:
        return None
    payload = json.loads(row[0])
    try:
        tz = ZoneInfo(payload["timezone"])
        brief_day = date.fromisoformat(payload["date"])
    except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError):
        return None
    return payload if brief_day == datetime.now(tz).date() else None


def response(text, session):
    # Yandex Dialogs text is limited; don't stream full reports.
    return {
        "response": {"text": text[:1000], "end_session": False},
        "session": {"session_id": session.get("session_id", ""),
                    "message_id": session.get("message_id", 0),
                    "user_id": session.get("user_id", "")},
        "version": "1.0",
    }


@app.post("/alice/webhook/{secret}")
async def alice_webhook(secret: str, request: Request):
    if not WEBHOOK_SECRET or not hmac.compare_digest(secret, WEBHOOK_SECRET):
        raise HTTPException(404, "Not found")
    payload = await request.json()
    session = payload.get("session", {})
    if not SKILL_ID or session.get("skill_id") != SKILL_ID:
        raise HTTPException(403, "Skill not configured or unexpected skill ID")
    # Фильтр по заявленному user_id — не проверка подлинности запроса.
    if ALLOWED_USER_IDS and session.get("user_id") not in ALLOWED_USER_IDS:
        raise HTTPException(403, "User not allowed")
    # Секрет в URL и ID не заменяют полноценную авторизацию.
    brief = latest()
    if not brief:
        return response("Актуальная сводка ещё не загружена.", session)
    command = payload.get("request", {}).get("command", "").lower()
    if any(word in command for word in ("рекоменд", "совет", "важно", "главно", "приоритет")):
        items = brief["recommendations"]
        prefix = "Рекомендации на день: "
    else:
        items = brief["meetings"]
        prefix = "Встречи на день: "
    return response(prefix + ("; ".join(items) if items else "Нет данных."), session)
