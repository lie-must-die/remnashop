from dataclasses import dataclass

from loguru import logger
from pydantic import SecretStr

from src.application.common import Interactor, Notifier
from src.application.common.dao import SettingsDao, WaitlistDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import SettingsDto, UserDto
from src.core.constants import T_ME
from src.core.enums import AccessMode, AccessRequirements
from src.core.types import NotificationType
from src.core.utils.validators import is_valid_url, is_valid_username
from src.infrastructure.taskiq.tasks.notifications import notify_payments_restored


@dataclass(frozen=True)
class ToggleNotificationDto:
    notification_type: NotificationType


@dataclass(frozen=True)
class UpdateChannelRequirementDto:
    input_text: str


@dataclass(frozen=True)
class UpdateRulesRequirementDto:
    input_text: str


@dataclass(frozen=True)
class ToggleConditionRequirementDto:
    condition_type: AccessRequirements


@dataclass(frozen=True)
class ChangeAccessModeDto:
    mode: AccessMode


class ToggleNotification(Interactor[ToggleNotificationDto, SettingsDto]):
    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao) -> None:
        self.uow = uow
        self.settings_dao = settings_dao

    async def _execute(self, actor: UserDto, data: ToggleNotificationDto) -> SettingsDto:
        async with self.uow:
            settings = await self.settings_dao.get()
            settings.notifications.toggle(data.notification_type)
            updated = await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Toggled notification '{data.notification_type}'")
        return updated


class ChangeAccessMode(Interactor[ChangeAccessModeDto, None]):
    required_permission: Permission = Permission.CHANGE_ACCESS_MODE

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao) -> None:
        self.uow = uow
        self.settings_dao = settings_dao

    async def _execute(self, actor: UserDto, data: ChangeAccessModeDto) -> None:
        async with self.uow:
            settings = await self.settings_dao.get()
            old_mode = settings.access.mode
            settings.access.mode = data.mode
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Changed access mode from '{old_mode}' to '{data.mode}'")


class TogglePayments(Interactor[None, None]):
    required_permission: Permission = Permission.TOGGLE_PAYMENTS

    def __init__(
        self,
        uow: UnitOfWork,
        settings_dao: SettingsDao,
        waitlist_dao: WaitlistDao,
    ) -> None:
        self.uow = uow
        self.settings_dao = settings_dao
        self.waitlist_dao = waitlist_dao

    async def _execute(self, actor: UserDto, data: None) -> None:
        settings = await self.settings_dao.get()
        new_state = not settings.access.payments_allowed
        settings.access.payments_allowed = new_state

        async with self.uow:
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Toggled payments availability to '{new_state}'")

        if new_state is True:
            waiting_users = await self.waitlist_dao.get_members()

            if waiting_users:
                logger.info(f"Triggering notification task for '{len(waiting_users)}' users")
                await notify_payments_restored.kiq(waiting_users)  # type: ignore[call-overload]

                await self.waitlist_dao.clear()
                logger.info("Waitlist has been cleared after triggering notifications")


class ToggleRegistration(Interactor[None, None]):
    required_permission: Permission = Permission.TOGGLE_REGISTRATION

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao) -> None:
        self.uow = uow
        self.settings_dao = settings_dao

    async def _execute(self, actor: UserDto, data: None) -> None:
        settings = await self.settings_dao.get()
        new_state = not settings.access.registration_allowed
        settings.access.registration_allowed = new_state

        async with self.uow:
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Toggled registration availability to '{new_state}'")


class ToggleConditionRequirement(Interactor[ToggleConditionRequirementDto, None]):
    required_permission: Permission = Permission.TOGGLE_CONDITION_REQUIREMENT

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao) -> None:
        self.uow = uow
        self.settings_dao = settings_dao

    async def _execute(self, actor: UserDto, data: ToggleConditionRequirementDto) -> None:
        settings = await self.settings_dao.get()

        if data.condition_type == AccessRequirements.RULES:
            settings.requirements.rules_required = not settings.requirements.rules_required
            new_state = settings.requirements.rules_required
        elif data.condition_type == AccessRequirements.CHANNEL:
            settings.requirements.channel_required = not settings.requirements.channel_required
            new_state = settings.requirements.channel_required
        else:
            logger.error(f"{actor.log} Tried to toggle unknown condition '{data.condition_type}'")
            return

        async with self.uow:
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(
            f"{actor.log} Toggled access requirement '{data.condition_type}' to '{new_state}'"
        )


class UpdateRulesRequirement(Interactor[UpdateRulesRequirementDto, bool]):
    required_permission: Permission = Permission.UPDATE_RULES_REQUIREMENT

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao, notifier: Notifier) -> None:
        self.uow = uow
        self.settings_dao = settings_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: UpdateRulesRequirementDto) -> bool:
        input_text = data.input_text.strip()

        if not is_valid_url(input_text):
            logger.warning(f"{actor.log} Provided invalid rules link format: '{input_text}'")
            await self.notifier.notify_user(actor, i18n_key="ntf-common.invalid-value")
            return False

        settings = await self.settings_dao.get()
        settings.requirements.rules_link = SecretStr(input_text)

        async with self.uow:
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Successfully updated rules link")
        await self.notifier.notify_user(actor, i18n_key="ntf-common.value-updated")
        return True


class UpdateChannelRequirement(Interactor[UpdateChannelRequirementDto, None]):
    required_permission: Permission = Permission.UPDATE_CHANNEL_REQUIREMENT

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao, notifier: Notifier) -> None:
        self.uow = uow
        self.settings_dao = settings_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: UpdateChannelRequirementDto) -> None:
        input_text = data.input_text.strip()
        settings = await self.settings_dao.get()

        if input_text.isdigit() or (input_text.startswith("-") and input_text[1:].isdigit()):
            await self._handle_id_input(input_text, settings)
            await self.notifier.notify_user(actor, i18n_key="ntf-common.value-updated")
        elif is_valid_username(input_text) or input_text.startswith(T_ME):
            settings.requirements.channel_link = SecretStr(input_text)
            await self.notifier.notify_user(actor, i18n_key="ntf-common.value-updated")

        else:
            logger.warning(f"{actor.log} Provided invalid channel format: '{input_text}'")
            await self.notifier.notify_user(actor, i18n_key="ntf-common.invalid-value")

        async with self.uow:
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Updated channel requirement")

    async def _handle_id_input(self, text: str, settings: SettingsDto) -> None:
        channel_id = int(text)
        if not text.startswith("-100") and not text.startswith("-"):
            channel_id = int(f"-100{text}")

        settings.requirements.channel_id = channel_id
