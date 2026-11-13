import os
import re
import secrets
import hashlib
from datetime import timedelta
import bcrypt
import jwt
import httpx
from fastapi import APIRouter, Request, Response, Depends
from pydantic import BaseModel
from core import db, now, iso, parse_dt, new_id, fail, audit, public_user, DEV_MODE
from rbac import ROLES, ensure_role_enabled, flags
import notify

router = APIRouter(prefix="/api/auth")
ALG = "HS256"
ACCESS_MIN = 30


def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def password_ok(p):
    return len(p) >= 10 and re.search(r"[A-Z]", p) and re.search(r"[a-z]", p) and re.search(r"\d", p)


def _token(uid, kind, minutes, role=None):
    return jwt.encode({"sub": uid, "type": kind, "role": role, "exp": now() + timedelta(minutes=minutes)}, os.environ["JWT_SECRET"], algorithm=ALG)


def _cookie_kw():
    # Secure+None cookies are rejected on plain HTTP (local Docker). DEV_MODE uses Lax.
    if DEV_MODE:
        return {"httponly": True, "secure": False, "samesite": "lax", "path": "/"}
    return {"httponly": True, "secure": True, "samesite": "none", "path": "/"}


def set_session(resp, user):
    kw = _cookie_kw()
    role = user.get("active_role")
    resp.set_cookie("access_token", _token(user["id"], "access", ACCESS_MIN, role), max_age=ACCESS_MIN * 60, **kw)
    resp.set_cookie("refresh_token", _token(user["id"], "refresh", 60 * 24 * 7, role), max_age=604800, **kw)


def _apply_role(u, p):
    if p.get("role") in u.get("roles", []):
        u["active_role"] = p["role"]
    return u


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    h = request.headers.get("Authorization", "")
    if not token and h.startswith("Bearer "):
        token = h[7:]
    if not token:
        fail(401, "Not authenticated", code="unauthenticated")
    try:
        p = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[ALG])
    except jwt.ExpiredSignatureError:
        fail(401, "Session expired", code="session_expired")
    except jwt.InvalidTokenError:
        fail(401, "Invalid session", code="unauthenticated")
    if p.get("type") != "access":
        fail(401, "Invalid session", code="unauthenticated")
    u = await db.users.find_one({"id": p["sub"]}, {"_id": 0})
    if not u or u.get("status") != "active":
        fail(401, "Account not active", code="unauthenticated")
    u.pop("password_hash", None)
    _apply_role(u, p)
    await ensure_role_enabled(u)
    return u


async def staff_user(user=Depends(get_current_user)):
    if user["active_role"] in ("R01", "R02", "R03"):
        fail(403, "Staff access only.", code="forbidden")
    return user


def role_required(*roles):
    async def dep(user=Depends(get_current_user)):
        if user["active_role"] not in roles:
            await audit(user, "access_denied", "endpoint", "", {"required": roles}, outcome="denied")
            fail(403, "Your role cannot access this function.", code="forbidden")
        return user
    return dep


class LoginIn(BaseModel):
    email: str
    password: str


async def _check_lock(ident):
    rec = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0})
    if rec and rec.get("count", 0) >= 5 and rec.get("locked_until") and parse_dt(rec["locked_until"]) > now():
        fail(429, "Too many failed attempts. Try again in 15 minutes.", code="locked")


async def _fail_attempt(ident):
    rec = await db.login_attempts.find_one_and_update({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"at": iso()}}, upsert=True, return_document=True)
    if rec and rec.get("count", 0) >= 5:
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"locked_until": iso(now() + timedelta(minutes=15))}})


async def _login_response(resp, user, method, request):
    set_session(resp, user)
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": iso()}})
    await audit(user, f"login:{method}", "user", user["id"], {"ip": request.client.host if request.client else ""})
    return public_user(user)


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ident = f"{request.client.host if request.client else ''}:{email}"
    await _check_lock(ident)
    u = await db.users.find_one({"email": email}, {"_id": 0})
    if not u or not u.get("password_hash") or not verify_password(body.password, u["password_hash"]):
        await _fail_attempt(ident)
        await audit({"email": email}, "login_failed", "user", "", outcome="denied")
        fail(401, "Invalid email or password.")
    if u.get("status") != "active":
        fail(403, "This account is not active.")
    await db.login_attempts.delete_one({"identifier": ident})
    return await _login_response(response, u, "password", request)


@router.post("/logout")
async def logout(response: Response):
    kw = _cookie_kw()
    for c in ("access_token", "refresh_token"):
        response.delete_cookie(c, path=kw["path"], secure=kw["secure"], samesite=kw["samesite"])
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    tok = request.cookies.get("refresh_token")
    if not tok:
        fail(401, "Session expired", code="session_expired")
    try:
        p = jwt.decode(tok, os.environ["JWT_SECRET"], algorithms=[ALG])
    except jwt.InvalidTokenError:
        fail(401, "Session expired", code="session_expired")
    u = await db.users.find_one({"id": p["sub"], "status": "active"}, {"_id": 0})
    if not u or p.get("type") != "refresh":
        fail(401, "Session expired", code="session_expired")
    _apply_role(u, p)
    set_session(response, u)
    return public_user(u)


class RoleIn(BaseModel):
    role: str


@router.post("/switch-role")
async def switch_role(body: RoleIn, response: Response, user=Depends(get_current_user)):
    if body.role not in user.get("roles", []):
        await audit(user, "role_switch_denied", "user", user["id"], {"role": body.role}, outcome="denied")
        fail(403, "You do not hold this role.")
    await db.users.update_one({"id": user["id"]}, {"$set": {"active_role": body.role}})
    await audit(user, "role_switch", "user", user["id"], {"role": body.role})
    set_session(response, {**user, "active_role": body.role})
    return public_user({**user, "active_role": body.role})


@router.post("/dev-login")
async def dev_login(body: RoleIn, request: Request, response: Response):
    if not DEV_MODE or not (await flags()).get("dev_role_switcher", True):
        fail(404, "Not available.")
    if body.role not in ROLES:
        fail(422, "Unknown role")
    u = await db.users.find_one({"demo": True, "roles": body.role, "status": "active"}, {"_id": 0}, sort=[("demo_primary", -1)])
    if not u:
        fail(404, "No demo account for this role")
    await db.users.update_one({"id": u["id"]}, {"$set": {"active_role": body.role}})
    u["active_role"] = body.role
    await audit(u, "dev_role_switcher_login", "user", u["id"], {"role": body.role})
    return await _login_response(response, u, "dev_switcher", request)


class OtpReq(BaseModel):
    identifier: str


@router.post("/otp/request")
async def otp_request(body: OtpReq):
    ident = body.identifier.strip().lower()
    u = await db.users.find_one({"$or": [{"email": ident}, {"phone": ident}], "roles": "R01", "status": "active"}, {"_id": 0})
    out = {"message": "If this contact is registered, a verification code has been sent.", "channel": "email" if "@" in ident else "sms"}
    if not u:
        return out
    code = f"{secrets.randbelow(1000000):06d}"
    await db.otp_codes.delete_many({"user_id": u["id"]})
    await db.otp_codes.insert_one({"user_id": u["id"], "hash": hashlib.sha256(code.encode()).hexdigest(), "expires_at": iso(now() + timedelta(minutes=10)), "attempts": 0})
    if "@" in ident:
        state = await notify.send_plain_email(u["email"], "Your Champion verification code", f"Your one-time verification code is {code}. It expires in 10 minutes.")
    else:
        state = "dev_adapter_not_sent"
    out["delivery"] = state
    if DEV_MODE and state != "sent":
        out["dev_code"] = code
        out["dev_note"] = "DEV MODE: code shown because the message was not delivered by a real provider."
    return out


class OtpVerify(BaseModel):
    identifier: str
    code: str


@router.post("/otp/verify")
async def otp_verify(body: OtpVerify, request: Request, response: Response):
    ident = body.identifier.strip().lower()
    u = await db.users.find_one({"$or": [{"email": ident}, {"phone": ident}], "roles": "R01", "status": "active"}, {"_id": 0})
    rec = await db.otp_codes.find_one({"user_id": u["id"]}, {"_id": 0}) if u else None
    if not rec or parse_dt(rec["expires_at"]) < now() or rec["attempts"] >= 5:
        fail(401, "Code expired or invalid. Request a new code.")
    if hashlib.sha256(body.code.strip().encode()).hexdigest() != rec["hash"]:
        await db.otp_codes.update_one({"user_id": u["id"]}, {"$inc": {"attempts": 1}})
        fail(401, "Incorrect code.")
    await db.otp_codes.delete_many({"user_id": u["id"]})
    u["active_role"] = "R01"
    await db.users.update_one({"id": u["id"]}, {"$set": {"active_role": "R01"}})
    return await _login_response(response, u, "otp", request)


class RecoverIn(BaseModel):
    email: str
    method: str = "Email link"
    support_reference: str = ""


@router.post("/recover")
async def recover(body: RecoverIn):
    email = body.email.strip().lower()
    u = await db.users.find_one({"email": email}, {"_id": 0})
    out = {"message": "If this work email is registered, recovery instructions have been sent."}
    if not u:
        return out
    tok = secrets.token_urlsafe(32)
    await db.reset_tokens.insert_one({"token_hash": hashlib.sha256(tok.encode()).hexdigest(), "user_id": u["id"], "expires_at": iso(now() + timedelta(hours=1)), "used": False})
    state = await notify.send_plain_email(email, "Champion staff access recovery", f"Use this one-time recovery token within 1 hour on the recovery page: {tok}")
    await audit(u, "recovery_requested", "user", u["id"], {"support_reference": body.support_reference, "delivery": state})
    out["delivery"] = state
    if DEV_MODE and state != "sent":
        out["dev_token"] = tok
    return out


class ResetIn(BaseModel):
    token: str
    password: str


@router.post("/reset")
async def reset(body: ResetIn):
    rec = await db.reset_tokens.find_one({"token_hash": hashlib.sha256(body.token.encode()).hexdigest()}, {"_id": 0})
    if not rec or rec["used"] or parse_dt(rec["expires_at"]) < now():
        fail(400, "Recovery token invalid or expired.")
    if not password_ok(body.password):
        fail(422, "Password must be at least 10 characters with upper, lower case and a digit.")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.reset_tokens.update_one({"token_hash": rec["token_hash"]}, {"$set": {"used": True}})
    await audit({"id": rec["user_id"]}, "password_reset", "user", rec["user_id"])
    return {"ok": True}


class GoogleIn(BaseModel):
    session_id: str


@router.post("/google/session")
async def google_session(body: GoogleIn, request: Request, response: Response):
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        fail(401, "Google sign-in could not be verified.")
    data = r.json()
    u = await db.users.find_one({"email": data["email"].lower(), "status": "active"}, {"_id": 0})
    if not u:
        await audit({"email": data["email"]}, "google_login_denied", "user", "", {"reason": "not provisioned"}, outcome="denied")
        fail(403, "This Google account is not provisioned for Champion Service Desk. Ask an administrator for an invitation.")
    await db.user_sessions.insert_one({"id": new_id("ses"), "user_id": u["id"], "provider": "google", "at": iso(), "expires_at": iso(now() + timedelta(days=7))})
    return await _login_response(response, u, "google", request)


class PrefsIn(BaseModel):
    language: str = "English"
    contact_channel: str = "Email"
    timezone: str = "Asia/Kolkata"
    service_updates: str = "All updates"
    appointment_reminder: str = "24 hours before"
    accessibility: str = "Standard"


@router.put("/preferences")
async def save_prefs(body: PrefsIn, user=Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"preferences": body.model_dump()}})
    await audit(user, "preferences_saved", "user", user["id"])
    return {"ok": True, "preferences": body.model_dump()}
