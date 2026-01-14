from typing import Optional

from aiogram import Bot
from loguru import logger

from src.application.common.dao import ReferralDao, UserDao
from src.application.dto import UserDto
from src.core.config import AppConfig
from src.core.constants import REFERRAL_PREFIX, T_ME


class ReferralService:
    def __init__(
        self,
        referral_dao: ReferralDao,
        user_dao: UserDao,
        bot: Bot,
        config: AppConfig,
    ) -> None:
        self.referral_dao = referral_dao
        self.user_dao = user_dao
        self.bot = bot
        self.config = config
        self._bot_username: Optional[str] = None

    async def get_referral_link(self, referral_code: str) -> str:
        return f"{await self._get_bot_redirect_url()}?start={REFERRAL_PREFIX}{referral_code}"

    def parse_referral_code(self, text: str) -> Optional[str]:
        parts = text.split()

        if len(parts) <= 1:
            return None

        code = parts[1]

        if not code.startswith(REFERRAL_PREFIX):
            return None

        return code[len(REFERRAL_PREFIX) :]

    async def get_valid_referrer(self, code: str, telegram_id: int) -> Optional[UserDto]:
        referrer = await self.user_dao.get_by_referral_code(code)

        if not referrer or referrer.telegram_id == telegram_id:
            logger.warning(f"Invalid referral code '{code}' or self-referral by '{telegram_id}'")
            return None

        return referrer

    async def _get_bot_redirect_url(self) -> str:
        if self._bot_username is None:
            self._bot_username = (await self.bot.get_me()).username

        return f"{T_ME}{self._bot_username}"
