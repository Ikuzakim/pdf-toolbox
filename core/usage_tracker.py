from datetime import datetime

from core.auth.database import get_connection


FREE_OPERATION_LIMIT = 10
PRO_OPERATION_LIMIT = 150


def _current_month():
    return datetime.now().strftime("%Y-%m")


def initialize_usage(user_id):
    month = _current_month()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO user_usage (
                user_id,
                usage_month,
                operations
            )
            VALUES (?, ?, 0)
            """,
            (user_id, month),
        )


def get_usage(user):
    user_id = user["id"]
    month = _current_month()

    initialize_usage(user_id)

    with get_connection() as connection:
        usage = connection.execute(
            """
            SELECT
                user_id,
                usage_month,
                operations
            FROM user_usage
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if usage is None:
        return {
            "user_id": user_id,
            "usage_month": month,
            "operations": 0,
        }

    if usage["usage_month"] != month:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE user_usage
                SET
                    usage_month = ?,
                    operations = 0
                WHERE user_id = ?
                """,
                (month, user_id),
            )

        return {
            "user_id": user_id,
            "usage_month": month,
            "operations": 0,
        }

    return dict(usage)


def get_operation_limit(user):
    if user["plan"] == "pro":
        return PRO_OPERATION_LIMIT

    return FREE_OPERATION_LIMIT


def can_use(user):
    usage = get_usage(user)
    limit = get_operation_limit(user)

    return usage["operations"] < limit


def record_operation(user):
    usage = get_usage(user)
    limit = get_operation_limit(user)

    if usage["operations"] >= limit:
        return False

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE user_usage
            SET operations = operations + 1
            WHERE user_id = ?
            """,
            (user["id"],),
        )

    return True


def get_remaining_operations(user):
    usage = get_usage(user)
    limit = get_operation_limit(user)

    return max(0, limit - usage["operations"])