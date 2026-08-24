import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(BASE_DIR),
)


from core.usage_tracker import (
    FREE_OPERATION_LIMIT,
    get_usage,
    can_use,
    record_operation,
    get_remaining_operations,
)


usage = get_usage()

print("Initial usage:", usage)

if usage["operations"] < 0:
    raise AssertionError(
        "Usage cannot be negative."
    )


if not can_use():
    raise AssertionError(
        "New user should be allowed to use the product."
    )


before = usage["operations"]

success = record_operation()

if not success:
    raise AssertionError(
        "Operation should have been recorded."
    )


after = get_usage()["operations"]

if after != before + 1:
    raise AssertionError(
        "Usage count did not increase correctly."
    )


remaining = get_remaining_operations()

expected_remaining = (
    FREE_OPERATION_LIMIT - after
)

if remaining != expected_remaining:
    raise AssertionError(
        "Remaining operation count is incorrect."
    )


print("Usage tracker successful.")
print(
    f"Operations used: {after}/{FREE_OPERATION_LIMIT}"
)
print(
    f"Operations remaining: {remaining}"
)