"""
routers/users.py — User management endpoints.

GET  /api/users          — list all users
GET  /api/users/{cid}    — get single user by custom_id
POST /api/users          — create user (admin use)
"""
import os, hmac, hashlib, base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import get_user_by_custom_id, USE_SUPABASE, _sqlite_conn

router = APIRouter()
MASTER = os.getenv("MASTER_SECRET", "change_me")


def _make_secret(custom_id: str) -> str:
    return base64.b32encode(
        hmac.new(MASTER.encode(), custom_id.encode(), hashlib.sha256).digest()
    ).decode()


class UserCreate(BaseModel):
    custom_id:    str
    full_name:    str
    role:         str = "student"
    photo_url:    Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None


@router.get("/api/users")
def list_users():
    if USE_SUPABASE:
        from app.database import _sb
        res = _sb.table("users").select(
            "id,custom_id,full_name,role,photo_url,parent_phone,parent_email"
        ).execute()
        return res.data or []
    con = _sqlite_conn()
    rows = con.execute(
        "SELECT id,custom_id,full_name,role,photo_url,parent_phone,parent_email FROM users"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.get("/api/users/{custom_id}")
def get_user(custom_id: str):
    user = get_user_by_custom_id(custom_id)
    if not user:
        raise HTTPException(404, "Not found")
    user.pop("secret_key", None)
    return user


@router.post("/api/users", status_code=201)
def create_user(body: UserCreate):
    secret = _make_secret(body.custom_id)
    if USE_SUPABASE:
        from app.database import _sb
        res = _sb.table("users").insert({**body.model_dump(), "secret_key": secret}).execute()
        return res.data[0]
    con = _sqlite_conn()
    try:
        con.execute(
            "INSERT INTO users(custom_id,full_name,role,photo_url,parent_phone,parent_email,secret_key)"
            " VALUES(?,?,?,?,?,?,?)",
            (body.custom_id, body.full_name, body.role,
             body.photo_url, body.parent_phone, body.parent_email, secret),
        )
        con.commit()
    except Exception as exc:
        raise HTTPException(409, str(exc))
    finally:
        con.close()
    return {"custom_id": body.custom_id, "full_name": body.full_name}
