from typing import Any, Awaitable, Callable, Optional

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as AiogramUser
from aiogram_dialog.utils import remove_intent_id
from dishka import AsyncContainer
from loguru import logger

from src.application.dto import TempUserDto
from src.application.services import ReferralService
from src.application.use_cases.access import CheckAccess, CheckAccessDto
from src.core.constants import CONTAINER_KEY, PAYMENT_PREFIX
from src.core.enums import MiddlewareEventType

from .base import EventTypedMiddleware


class AccessMiddleware(EventTypedMiddleware):
    __event_types__ = [MiddlewareEventType.MESSAGE, MiddlewareEventType.CALLBACK_QUERY]

    async def middleware_logic(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        aiogram_user: Optional[AiogramUser] = self._get_aiogram_user(data)

        if aiogram_user is None or aiogram_user.is_bot:
            logger.warning("Terminating middleware: event from bot or missing user")
            return

        container: AsyncContainer = data[CONTAINER_KEY]
        check_access = await container.get(CheckAccess)
        referral_service = await container.get(ReferralService)

        if await check_access.system(
            CheckAccessDto(
                temp_user=TempUserDto.from_aiogram(aiogram_user),
                is_payment_event=self._is_payment_event(event),
                is_referral_event=await self.is_referral_event(
                    referral_service,
                    event,
                    aiogram_user.id,
                ),
            )
        ):
            return await handler(event, data)

    def _is_payment_event(self, event: TelegramObject) -> bool:
        if not isinstance(event, CallbackQuery) or not event.data:
            return False

        callback_data = remove_intent_id(event.data)

        if callback_data[-1].startswith(PAYMENT_PREFIX):
            logger.debug(f"Detected payment event '{callback_data}'")
            return True

        return False

    async def is_referral_event(
        self,
        referral_service: ReferralService,
        event: TelegramObject,
        telegram_id: int,
    ) -> bool:
        if not isinstance(event, Message) or not event.text:
            return False

        code = referral_service.parse_referral_code(event.text)

        if not code:
            return False

        return bool(await referral_service.get_valid_referrer(code, telegram_id))
