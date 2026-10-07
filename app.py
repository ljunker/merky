import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
  FastAPI,
  Request
)
from pydantic import BaseModel
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATABASE_FILE = BASE_DIR / "merk.db"


def get_db():
  connection = sqlite3.connect(
      DATABASE_FILE,
      timeout=5
  )

  connection.row_factory = sqlite3.Row

  return connection


def init_db():
  with get_db() as db:
    db.execute("""
               CREATE TABLE IF NOT EXISTS merks
               (
                   id         TEXT PRIMARY KEY,
                   content    TEXT    NOT NULL,
                   created_at INTEGER NOT NULL
               )
               """)

    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
  init_db()
  yield


app = FastAPI(
    title="Merk Service",
    version="1.0.0",
    lifespan=lifespan
)


def generate_id() -> str:
  return secrets.token_urlsafe(8)


@app.get("/api/health")
def health():
  return {"status": "ok"}


@app.get("/api/merk")
def get_all():
  with get_db() as db:
    rows = db.execute("SELECT * FROM merks ORDER BY created_at DESC").fetchall()
  return [dict(row) for row in rows]


@app.get("/api/merk/{id}")
def get_by_id(id: str):
  with get_db() as db:
    merk = db.execute(
        """
        SELECT *
        FROM merks
        WHERE id = ?
        """,
        (id,)
    ).fetchone()

    return dict(merk)


class UpdateRequest(BaseModel):
  content: str


@app.put("/api/merk/{id}")
def update_merk(id: str, request: UpdateRequest):
  with get_db() as db:
    db.execute(
        """
        UPDATE merks
        SET content = ?
        WHERE id = ?
        """,
        (request.content, id)
    )
    db.commit()

  return {
    "id": id,
    "content": request.content
  }


class MerkRequest(BaseModel):
  text: str


@app.post("/api/merk")
def create_merk(request: MerkRequest):
  merk_id = generate_id()
  created_at = int(time.time())

  with get_db() as db:
    db.execute(
        """
        INSERT INTO merks (id, content, created_at)
        VALUES (?, ?, ?)
        """,
        (merk_id, request.text, created_at)
    )
    db.commit()

  return {
    "id": merk_id
  }


class DeleteRequest(BaseModel):
  id: str


@app.delete("/api/merk")
def delete_merk(request: DeleteRequest):
  id = request.id
  with get_db() as db:
    db.execute(
        """
        DELETE
        FROM merks
        WHERE id = ?
        """,
        (id,)
    )
    db.commit()


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


@app.api_route("/", methods=["GET", "HEAD"])
def index(request: Request):
  return FileResponse(
      STATIC_DIR / "index.html"
  )
