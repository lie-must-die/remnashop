import re
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Final, Optional

from src.core.enums import PlanType
from src.core.utils.time import datetime_now

GB_FACTOR: Final[Decimal] = Decimal(1024**3)


def _round_decimal(value: Decimal) -> int:
    result = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(0, int(result))


def to_snake_case(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def event_to_key(class_name: str) -> str:
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    formatted_key = snake.replace("_", "-")
    return f"event-{formatted_key}"


def gb_to_bytes(value: Optional[int]) -> int:
    if not value:
        return 0

    return _round_decimal(Decimal(value) * GB_FACTOR)


def bytes_to_gb(value: Optional[int]) -> int:
    if not value:
        return 0

    return _round_decimal(Decimal(value) / GB_FACTOR)


def percent(part: int, whole: int) -> str:
    if whole == 0:
        return "N/A"

    percent = (part / whole) * 100
    return f"{percent:.2f}"


def country_code_to_flag(code: str) -> str:
    if not code.isalpha() or len(code) != 2:
        return "🏴‍☠️"

    return "".join(chr(ord("🇦") + ord(c.upper()) - ord("A")) for c in code)


def days_to_datetime(value: int, year: int = 2099) -> datetime:
    dt = datetime_now()

    if value == 0:  # UNLIMITED for panel
        try:
            return dt.replace(year=year)
        except ValueError:
            last_day = monthrange(year, dt.month)[1]
            return dt.replace(year=year, day=min(dt.day, last_day))

    return dt + timedelta(days=value)


def limits_to_plan_type(traffic: int, devices: int) -> PlanType:
    has_traffic = traffic > 0
    has_devices = devices > 0

    if has_traffic and has_devices:
        return PlanType.BOTH
    elif has_traffic:
        return PlanType.TRAFFIC
    elif has_devices:
        return PlanType.DEVICES
    else:
        return PlanType.UNLIMITED
