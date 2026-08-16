"""
Simple authentication helpers using bcrypt.
"""

import bcrypt
from database import get_session, User


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def authenticate(username: str, password: str) -> bool:
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if user and verify_password(password, user.password_hash):
            return True
        return False
    finally:
        session.close()


def change_password(username: str, new_password: str) -> bool:
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user.password_hash = hashed
        session.commit()
        return True
    finally:
        session.close()


def get_user_email(username: str) -> str | None:
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        return user.email if user else None
    finally:
        session.close()
