from dishka import Provider, Scope, provide

from src.application.use_cases.access import (
    AcceptRules,
    CheckAccess,
    CheckChannelSubscription,
    CheckRules,
)
from src.application.use_cases.menu import GetMenuData
from src.application.use_cases.redirect import RedirectMenu
from src.application.use_cases.remnawave import SyncRemnaUser
from src.application.use_cases.settings import (
    ChangeAccessMode,
    ToggleConditionRequirement,
    ToggleNotification,
    TogglePayments,
    ToggleRegistration,
    UpdateChannelRequirement,
    UpdateRulesRequirement,
)
from src.application.use_cases.user import GetOrCreateUser, SetBotBlockedStatus


class UseCasesProvider(Provider):
    scope = Scope.REQUEST

    check_access = provide(source=CheckAccess)
    check_channel_subscription = provide(source=CheckChannelSubscription)
    check_rules = provide(source=CheckRules)
    accept_rules = provide(source=AcceptRules)

    get_menu_data = provide(GetMenuData)
    redirect_menu = provide(RedirectMenu)

    get_or_create_user = provide(GetOrCreateUser)
    set_bot_blocked_status = provide(SetBotBlockedStatus)

    toggle_notification = provide(ToggleNotification)
    change_accessmode = provide(ChangeAccessMode)
    toggle_payments = provide(TogglePayments)
    toggle_registration = provide(ToggleRegistration)
    toggle_condition_requirement = provide(ToggleConditionRequirement)
    update_rules_requirement = provide(UpdateRulesRequirement)
    update_channel_requirement = provide(UpdateChannelRequirement)

    sync_remna_user = provide(SyncRemnaUser)
