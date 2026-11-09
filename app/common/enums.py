from enum import Enum

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PRODUCT_MANAGER = "product_manager"
    INVENTORY_MANAGER = "inventory_manager"
    ORDER_MANAGER = "order_manager"
    SUPPORT_AGENT = "support_agent"
    CUSTOMER = "customer"
    DELIVERY_MANAGER = "delivery_manager"
    FINANCE_MANAGER = "finance_manager"
    SELLER = "seller"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class AddressType(str, Enum):
    SHIPPING = "shipping"
    BILLING = "billing"
    BOTH = "both"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    STRIPE = "stripe"
    CREDIT_CARD = "credit_card"
    COD = "cod"
    BANK_TRANSFER = "bank_transfer"


class ShipmentStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    ITEM_RECEIVED = "item_received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExchangeStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REPLACEMENT_DISPATCHED = "replacement_dispatched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class InventoryTransferStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATUS_CHANGE = "status_change"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    FINANCIAL_ADJUSTMENT = "financial_adjustment"
    PERMISSION_CHANGE = "permission_change"
    ACCOUNT_RESTRICTION = "account_restriction"


class OrderItemFulfillmentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    BACKORDERED = "BACKORDERED"


class PromotionType(str, Enum):
    PRODUCT = "PRODUCT"
    CATEGORY = "CATEGORY"
    CART = "CART"
    CUSTOMER_SEGMENT = "CUSTOMER_SEGMENT"


class LoyaltyTier(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class LoyaltyTransactionType(str, Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"
    EXPIRE = "EXPIRE"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    FULFILLED = "FULFILLED"
    EXPIRED = "EXPIRED"


class WarrantyStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REPAIRED = "REPAIRED"
    REPLACED = "REPLACED"


class SellerStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    DISPUTED = "DISPUTED"


class SupportCaseCategory(str, Enum):
    ORDER = "order"
    BILLING = "billing"
    PAYMENT = "payment"
    RETURN = "return"
    PRODUCT = "product"
    DISPUTE = "dispute"
    CHARGEBACK = "chargeback"
    GENERAL = "general"


class SupportCaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IntegrationServiceType(str, Enum):
    PAYMENT = "payment"
    SHIPPING = "shipping"
    EMAIL = "email"
    SMS = "sms"


class IntegrationStatus(str, Enum):
    SUCCESS = "success"
    RECOVERABLE_FAILURE = "recoverable_failure"
    FATAL_FAILURE = "fatal_failure"

