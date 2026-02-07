import asyncio
from typing import cast

from aiogram import Bot
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from src.application.common import Notifier
from src.application.common.dao import BroadcastDao
from src.application.dto import BroadcastDto, BroadcastMessageDto, UserDto
from src.application.use_cases.broadcast import (
    BulkUpdateBroadcastMessages,
    ClearOldBroadcasts,
    FinishBroadcast,
    FinishBroadcastDto,
    InitializeBroadcastMessages,
    InitializeBroadcastMessagesDto,
    UpdateBroadcastMessageStatus,
    UpdateBroadcastMessageStatusDto,
)
from src.core.enums import BroadcastMessageStatus, BroadcastStatus
from src.core.utils.iterables import chunked
from src.infrastructure.taskiq.broker import broker


@broker.task
@inject(patch_module=True)
async def send_broadcast_task(
    broadcast: BroadcastDto,
    users: list[UserDto],
    notifier: FromDishka[Notifier],
    initialize_broadcast_messages: FromDishka[InitializeBroadcastMessages],
    update_broadcast_message_status: FromDishka[UpdateBroadcastMessageStatus],
    finish_broadcast: FromDishka[FinishBroadcast],
    broadcast_dao: FromDishka[BroadcastDao],
) -> None:
    task_id = broadcast.task_id
    total_users = len(users)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    logger.info(f"Started sending broadcast '{task_id}', total users: {total_users}")

    try:
        messages = [
            BroadcastMessageDto(
                user_telegram_id=u.telegram_id,
                status=BroadcastMessageStatus.PENDING,
            )
            for u in users
        ]

        await initialize_broadcast_messages.system(
            InitializeBroadcastMessagesDto(task_id, messages)
        )
    except Exception:
        logger.exception(f"Failed to initialize messages for broadcast '{task_id}'")
        await finish_broadcast.system(FinishBroadcastDto(task_id, BroadcastStatus.ERROR))
        return

    for i, batch in enumerate(chunked(zip(users, messages), 20), start=1):
        batch_start = loop.time()

        current = await broadcast_dao.get_by_task_id(task_id)
        if not current or current.status == BroadcastStatus.CANCELED:
            logger.info(f"Broadcast '{task_id}' was canceled")
            break

        for user, msg_dto in batch:
            try:
                tg_message = await notifier.notify_user(user=user, payload=broadcast.payload)

                status = (
                    BroadcastMessageStatus.SENT if tg_message else BroadcastMessageStatus.FAILED
                )
                msg_id = tg_message.message_id if tg_message else None

                await update_broadcast_message_status.system(
                    UpdateBroadcastMessageStatusDto(
                        task_id=task_id,
                        telegram_id=user.telegram_id,
                        status=status,
                        message_id=msg_id,
                        success=bool(tg_message),
                    ),
                )
            except Exception:
                logger.exception(
                    f"Failed to send message to user '{user.telegram_id}' in task '{task_id}'"
                )

        batch_elapsed = loop.time() - batch_start
        logger.info(f"Batch {i}: processed batch in '{batch_elapsed:.2f}s'")

        wait_time = 1.0 - batch_elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    total_elapsed = loop.time() - start_time
    await finish_broadcast.system(FinishBroadcastDto(task_id, BroadcastStatus.COMPLETED))

    final_state: BroadcastDto = await broadcast_dao.get_by_task_id(task_id)  # type: ignore[assignment]
    logger.info(
        f"Finished broadcast '{task_id}' in {total_elapsed:.2f}s "
        f"(sent: {final_state.success_count}, failed: {final_state.failed_count})"
    )


@broker.task
@inject(patch_module=True)
async def delete_broadcast_task(
    broadcast: BroadcastDto,
    bot: FromDishka[Bot],
    bulk_update_broadcast_messages: FromDishka[BulkUpdateBroadcastMessages],
) -> tuple[int, int, int]:
    broadcast_id = cast(int, broadcast.id)
    logger.info(f"Started deleting messages for broadcast '{broadcast_id}'")

    if not broadcast.messages:
        logger.error(f"Messages list is empty for broadcast '{broadcast_id}', aborting")
        raise ValueError(f"Broadcast '{broadcast_id}' messages is empty")

    deleted_count = 0
    total_messages = len(broadcast.messages)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    async def delete_message(message: BroadcastMessageDto) -> BroadcastMessageDto:
        if message.status not in (BroadcastMessageStatus.SENT, BroadcastMessageStatus.EDITED):
            return message
        if not message.message_id:
            return message

        try:
            if await bot.delete_message(
                chat_id=message.user_telegram_id, message_id=message.message_id
            ):
                message.status = BroadcastMessageStatus.DELETED
        except Exception:
            logger.exception(f"Exception deleting message for user '{message.user_telegram_id}'")
        return message

    for i, batch in enumerate(chunked(broadcast.messages, 20), start=1):
        batch_start = loop.time()
        results = await asyncio.gather(*(delete_message(m) for m in batch))

        await bulk_update_broadcast_messages.system(results)
        deleted_count += sum(1 for m in results if m.status == BroadcastMessageStatus.DELETED)

        batch_elapsed = loop.time() - batch_start
        wait_time = 1.0 - batch_elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    total_elapsed = loop.time() - start_time
    logger.info(
        f"Deletion finished for broadcast '{broadcast_id}'. "
        f"Total: {total_messages}, Deleted: {deleted_count}, "
        f"Total time: {total_elapsed:.2f}s"
    )
    return total_messages, deleted_count, total_messages - deleted_count


@broker.task(schedule=[{"cron": "0 0 */7 * *"}])
@inject(patch_module=True)
async def delete_broadcasts_task(clear_old_broadcasts: FromDishka[ClearOldBroadcasts]) -> None:
    await clear_old_broadcasts.system()
