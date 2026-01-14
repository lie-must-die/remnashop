from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import UUID

from remnapy.enums.users import TrafficLimitStrategy

from src.core.enums import Currency, PlanAvailability, PlanType

from .base import BaseDto, TimestampMixin, TrackableMixin


@dataclass(kw_only=True)
class PlanSnapshotDto:
    id: int
    name: str
    tag: Optional[str] = None

    type: PlanType
    traffic_limit_strategy: TrafficLimitStrategy = TrafficLimitStrategy.NO_RESET

    traffic_limit: int
    device_limit: int
    duration: int

    internal_squads: list[UUID] = field(default_factory=list)
    external_squad: Optional[UUID] = None

    is_active: bool = False
    is_trial: bool = False


@dataclass(kw_only=True)
class PlanDto(BaseDto, TrackableMixin, TimestampMixin):
    name: str = "Default Plan"
    description: Optional[str] = None
    tag: Optional[str] = None

    type: PlanType = PlanType.BOTH
    availability: PlanAvailability = PlanAvailability.ALL
    traffic_limit_strategy: TrafficLimitStrategy = TrafficLimitStrategy.NO_RESET

    traffic_limit: int = 100
    device_limit: int = 1

    allowed_user_ids: list[int] = field(default_factory=list)
    internal_squads: list[UUID] = field(default_factory=list)
    external_squad: Optional[UUID] = None

    order_index: int = 0
    is_active: bool = False
    is_trial: bool = False

    durations: list["PlanDurationDto"] = field(default_factory=list)


@dataclass(kw_only=True)
class PlanDurationDto(BaseDto, TrackableMixin):
    days: int
    order_index: int = 0
    prices: list["PlanPriceDto"] = field(default_factory=list)


@dataclass(kw_only=True)
class PlanPriceDto(BaseDto, TrackableMixin):
    currency: Currency
    price: Decimal
