from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

import asyncio
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from src.application.common import Notifier, Redirect
from src.application.dto import MediaDescriptorDto, MessagePayloadDto, UserDto
from src.application.use_cases.misc.queries.logs import GetLogs
from src.application.use_cases.user.commands.roles import RevokeRole
from src.core.config import AppConfig
from src.core.constants import ASSETS_DIR, LOG_DIR, USER_KEY
from src.core.enums import MediaType
from src.core.exceptions import LogsToFileDisabledError
from src.core.logger import LOG_FILENAME
from src.telegram.routers.dashboard.users.user.handlers import start_user_window
from src.telegram.utils import is_double_click


@inject
async def on_logs_request(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    get_logs: FromDishka[GetLogs],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]

    try:
        log_file = await get_logs(user)
        media = MediaDescriptorDto(
            kind="fs",
            value=str(log_file.path),
            filename=log_file.display_name,
        )

        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="",
                media=media,
                media_type=MediaType.DOCUMENT,
                delete_after=None,
                disable_default_markup=False,
            ),
        )
    except FileNotFoundError:
        logger.error(f"{user.log} Log file not found at '{LOG_DIR}/{LOG_FILENAME}'")
        await notifier.notify_user(user, i18n_key="ntf-error.log-not-found")
    except LogsToFileDisabledError:
        logger.debug(f"Logs request denied for '{user.telegram_id}': file logging is off")
        await notifier.notify_user(user, i18n_key="ntf-error.logs-disabled")


@inject
async def on_user_select(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    target_telegram_id = int(dialog_manager.item_id)  # type: ignore[attr-defined]
    await start_user_window(manager=dialog_manager, target_telegram_id=target_telegram_id)


@inject
async def on_role_revoke(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    redirect: FromDishka[Redirect],
    revoke_role: FromDishka[RevokeRole],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    target_telegram_id = int(dialog_manager.item_id)  # type: ignore[attr-defined]

    if not is_double_click(
        dialog_manager,
        key=f"role_confirm_{target_telegram_id}",
        cooldown=10,
    ):
        await notifier.notify_user(user, i18n_key="ntf-common.double-click-confirm")
        logger.debug(
            f"Waiting for double click confirmation to revoke role for '{target_telegram_id}'"
        )
        return

    await revoke_role(user, target_telegram_id)
    await redirect.to_main_menu(target_telegram_id)


@inject
async def on_backup_assets(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]

    await notifier.notify_user(user, i18n_key="ntf-backup.assets-started")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tmp_dir = Path(tempfile.mkdtemp())
        zip_path = tmp_dir / f"assets_backup_{timestamp}"

        await asyncio.to_thread(
            shutil.make_archive,
            str(zip_path),
            "zip",
            str(ASSETS_DIR.parent),
            str(ASSETS_DIR.name),
        )

        zip_file = Path(str(zip_path) + ".zip")

        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="",
                media=MediaDescriptorDto(
                    kind="fs",
                    value=str(zip_file),
                    filename=zip_file.name,
                ),
                media_type=MediaType.DOCUMENT,
                delete_after=None,
                disable_default_markup=False,
            ),
        )
        logger.info(f"{user.log} Assets backup sent: {zip_file.name}")

    except Exception as e:
        logger.exception(f"{user.log} Failed to create assets backup: {e}")
        await notifier.notify_user(user, i18n_key="ntf-backup.error")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@inject
async def on_backup_database(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
    config: FromDishka[AppConfig],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]

    await notifier.notify_user(user, i18n_key="ntf-backup.db-started")

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_file = tmp_dir / f"db_backup_{timestamp}.sql"

        db = config.database

        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            "-h", db.host,
            "-p", str(db.port),
            "-U", db.user,
            "-d", db.name,
            "-f", str(dump_file),
            env={**__import__("os").environ, "PGPASSWORD": db.password.get_secret_value()},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {stderr.decode()}")

        await notifier.notify_user(
            user=user,
            payload=MessagePayloadDto(
                i18n_key="",
                media=MediaDescriptorDto(
                    kind="fs",
                    value=str(dump_file),
                    filename=dump_file.name,
                ),
                media_type=MediaType.DOCUMENT,
                delete_after=None,
                disable_default_markup=False,
            ),
        )
        logger.info(f"{user.log} Database backup sent: {dump_file.name}")

    except Exception as e:
        logger.exception(f"{user.log} Failed to create database backup: {e}")
        await notifier.notify_user(user, i18n_key="ntf-backup.error")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
