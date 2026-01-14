from dataclasses import dataclass
from typing import Optional

from src.application.common import Interactor
from src.application.common.dao import PlanDao, SettingsDao, SubscriptionDao
from src.application.common.policy import Permission
from src.application.dto import PlanDto, SubscriptionDto, UserDto
from src.application.services import ReferralService


@dataclass(frozen=True)
class MenuDataResultDto:
    is_referral_enabled: bool
    has_used_trial: bool
    available_trial: Optional[PlanDto]
    current_subscription: Optional[SubscriptionDto]
    referral_link: str


class GetMenuData(Interactor[None, MenuDataResultDto]):
    required_permission: Permission = Permission.PUBLIC

    def __init__(
        self,
        plan_dao: PlanDao,
        settings_dao: SettingsDao,
        subscription_dao: SubscriptionDao,
        referral_service: ReferralService,
    ) -> None:
        self.plan_dao = plan_dao
        self.settings_dao = settings_dao
        self.subscription_dao = subscription_dao
        self.referral_service = referral_service

    async def _execute(self, actor: UserDto, data: None) -> MenuDataResultDto:
        has_used_trial = await self.subscription_dao.has_used_trial(actor.telegram_id)
        current_subscription = await self.subscription_dao.get_current(actor.telegram_id)

        plan = None
        if not has_used_trial:
            plan = await self.plan_dao.get_trial_available_for_user(actor.telegram_id)

        settings = await self.settings_dao.get()
        is_referral_enabled = settings.referral.enable

        referral_link = await self.referral_service.get_referral_link(actor.referral_code)

        return MenuDataResultDto(
            is_referral_enabled=is_referral_enabled,
            has_used_trial=has_used_trial,
            available_trial=plan,
            current_subscription=current_subscription,
            referral_link=referral_link,
        )
