"""Passwords, tokens and the rules for both."""

import hashlib
import re
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id with the library's recommended memory and time cost.
_hasher = PasswordHasher()

MIN_PASSWORD = 10
MAX_PASSWORD = 200
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_COMMON = {
    "password12", "password123", "password1234", "1234567890", "12345678910", "qwertyuiop", "iloveyou12",
    "stockai123", "admin12345", "letmein123", "welcome123", "qwerty1234",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Checked against when the email is unknown, so a wrong email takes as long as a wrong password."""
    return hash_password("not-a-real-password-" + secrets.token_hex(8))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(_EMAIL.match(email))


def password_problem(password: str, email: str = "") -> str | None:
    """A plain-English reason the password can't be used, or None if it's fine."""
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return "That password is too long."
    if email and password.strip().lower() == email.strip().lower():
        return "Don't use your email address as your password."
    if password.lower() in _COMMON:
        return "That password is too common. Choose another."
    return None
