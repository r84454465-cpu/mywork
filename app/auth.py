# app/auth.py
from typing import Optional
from fastapi import HTTPException, status

USERS = {
    "ayan": {"password": "ayan123", "token": "ayan-123"}
}

def authenticate_user(username: str, password: str) -> Optional[str]:
    user = USERS.get(username)
    if not user:
        return None
    if user.get("password") != password:
        return None
    return user.get("token")

def get_username_for_token(token: str) -> Optional[str]:
    for username, info in USERS.items():
        if info.get("token") == token:
            return username
    return None

def verify_token(token: str) -> str:
    username = get_username_for_token(token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token")
    return username
