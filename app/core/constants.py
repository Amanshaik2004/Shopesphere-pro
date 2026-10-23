from app.common.enums import UserRole

# Default super admin roles
ALL_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.PRODUCT_MANAGER,
    UserRole.INVENTORY_MANAGER,
    UserRole.ORDER_MANAGER,
    UserRole.SUPPORT_AGENT,
    UserRole.DELIVERY_MANAGER,
    UserRole.FINANCE_MANAGER,
]

ADMIN_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN
]

PRODUCT_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.PRODUCT_MANAGER
]

INVENTORY_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.INVENTORY_MANAGER
]

ORDER_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.ORDER_MANAGER
]

FINANCE_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.FINANCE_MANAGER
]

DELIVERY_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.DELIVERY_MANAGER
]

SUPPORT_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.SUPPORT_AGENT
]

PAGE_DEFAULT = 1
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
