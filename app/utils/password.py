from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# app/utils/password.py

def hash_password(password: str) -> str:
    """Store password as plain text (DEV ONLY)"""
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare passwords as plain text (DEV ONLY)"""
    return plain_password == hashed_password