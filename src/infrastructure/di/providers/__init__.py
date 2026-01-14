from dishka import Provider
from dishka.integrations.aiogram import AiogramProvider

from .bot import BotProvider
from .config import ConfigProvider
from .dao import DaoProvider
from .database import DatabaseProvider
from .i18n import I18nProvider
from .redis import RedisProvider
from .remnawave import RemnawaveProvider
from .retort import RetortProvider
from .services import ServicesProvider
from .use_cases import UseCasesProvider


def get_providers() -> list[Provider]:
    return [
        AiogramProvider(),
        BotProvider(),
        ConfigProvider(),
        DaoProvider(),
        DatabaseProvider(),
        I18nProvider(),
        RedisProvider(),
        RemnawaveProvider(),
        RetortProvider(),
        ServicesProvider(),
        UseCasesProvider(),
    ]
