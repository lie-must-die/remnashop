from enum import auto
from typing import Final

from src.application.dto import UserDto
from src.core.enums import Role, UpperStrEnum


class PermissionPolicy:
    @staticmethod
    def has_permission(actor: UserDto, permission: "Permission") -> bool:
        if permission is Permission.PUBLIC:
            return True

        if actor.role == Role.SYSTEM:
            return True

        permissions = ROLE_PERMISSIONS.get(actor.role, set())
        return permission in permissions


class Permission(UpperStrEnum):
    PUBLIC = auto()
    COMMAND_TEST = auto()
    #
    VIEW_DASHBOARD = auto()
    VIEW_REMNA = auto()
    VIEW_IMPORTER = auto()
    VIEW_ACCESS = auto()
    #
    CHANGE_ACCESS_MODE = auto()
    TOGGLE_NOTIFICATION = auto()
    TOGGLE_PAYMENTS = auto()
    TOGGLE_REGISTRATION = auto()
    TOGGLE_CONDITION_REQUIREMENT = auto()
    UPDATE_RULES_REQUIREMENT = auto()
    UPDATE_CHANNEL_REQUIREMENT = auto()
    #
    USER_SYNC = auto()
    MANAGE_SUBSCRIPTIONS = auto()


ROLE_PERMISSIONS: Final[dict[Role, set[Permission]]] = {
    Role.SYSTEM: set(Permission),
    Role.OWNER: set(Permission),
    Role.DEV: set(Permission),
    Role.ADMIN: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_ACCESS,
    },
    Role.PREVIEW: {  # TODO: Implement demo Bot instance
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_ACCESS,
    },
    Role.USER: set(),
}
