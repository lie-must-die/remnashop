from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from remnapy.enums.users import TrafficLimitStrategy

from src.application.dto import MessagePayloadDto
from src.core.enums import UserNotificationType
from src.core.types import NotificationType

from .base import BaseEvent, UserEvent


@dataclass(frozen=True, kw_only=True)
class SubscriptionLimitedEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.LIMITED,
        init=False,
    )

    is_trial: bool
    traffic_strategy: TrafficLimitStrategy
    reset_time: Any


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpiredEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.EXPIRED,
        init=True,
    )


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpiresEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.EXPIRES_IN_1_DAY,
        init=True,
    )

    day: int
