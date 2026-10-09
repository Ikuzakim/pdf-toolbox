from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import bcrypt

from .database import get_connection


def normalize_email(email):
    return email.strip().lower()


def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_user(email, password):
    email = normalize_email(email)

    password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    email,
                    password_hash
                )
                VALUES (?, ?)
                """,
                (email, password_hash),
            )

            user_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO user_usage (
                    user_id,
                    usage_month,
                    operations
                )
                VALUES (?, ?, 0)
                """,
                (
                    user_id,
                    datetime.now().strftime("%Y-%m"),
                ),
            )

        return {
            "id": user_id,
            "email": email,
            "plan": "free",
            "subscription_status": "inactive",
        }

    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            return None

        raise


def authenticate_user(email, password):
    email = normalize_email(email)

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT
                id,
                email,
                password_hash,
                plan,
                subscription_status
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "subscription_status": user["subscription_status"],
    }


def get_user_by_id(user_id):
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT
                id,
                email,
                plan,
                subscription_status
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if user is None:
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "plan": user["plan"],
        "subscription_status": user["subscription_status"],
    }

def hash_api_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_api_token(user_id, expires_days=30):
    token = secrets.token_urlsafe(32)
    token_hash = hash_api_token(token)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=expires_days)
    ).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO api_tokens (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                token_hash,
                expires_at,
            ),
        )

    return token


def get_user_by_api_token(token):
    token_hash = hash_api_token(token)

    with get_connection() as connection:
        record = connection.execute(
            """
            SELECT
                api_tokens.user_id,
                api_tokens.expires_at,
                users.id,
                users.email,
                users.plan,
                users.subscription_status
            FROM api_tokens
            JOIN users
                ON users.id = api_tokens.user_id
            WHERE api_tokens.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

    if record is None:
        return None

    try:
        expires_at = datetime.fromisoformat(
            record["expires_at"]
        )

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

    except ValueError:
        return None

    if expires_at <= datetime.now(timezone.utc):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM api_tokens
                WHERE token_hash = ?
                """,
                (token_hash,),
            )

        return None

    return {
        "id": record["id"],
        "email": record["email"],
        "plan": record["plan"],
        "subscription_status": record["subscription_status"],
    }