"""
Unified Password Context for User Service.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt", "pbkdf2_sha256", "sha256_crypt"],
    deprecated="auto",
)
