from dishka import AnyOf, Provider, Scope, alias, provide

from src.application.common import (
    Cryptographer,
    EventPublisher,
    EventSubscriber,
    Notifier,
    Remnawave,
)
from src.application.services import (
    CommandService,
    NotificationService,
    ReferralService,
    WebhookService,
)
from src.infrastructure.services import (
    CryptographerImpl,
    EventBusImpl,
    NotificationQueue,
    RemnawaveImpl,
)


class ServicesProvider(Provider):
    scope = Scope.APP

    cryptographer = provide(source=CryptographerImpl, provides=Cryptographer)

    event_bus = provide(EventBusImpl)
    publisher = alias(source=EventBusImpl, provides=EventPublisher)
    subscriber = alias(source=EventBusImpl, provides=EventSubscriber)

    command = provide(source=CommandService)
    webhook = provide(source=WebhookService)

    remnawave = provide(source=RemnawaveImpl, provides=Remnawave)

    notification_queue = provide(source=NotificationQueue)
    notification = provide(
        NotificationService,
        scope=Scope.REQUEST,
        provides=AnyOf[Notifier, NotificationService],
    )

    referral = provide(source=ReferralService, scope=Scope.REQUEST)
