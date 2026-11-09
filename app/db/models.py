from app.db.base import Base, TimestampMixin

# Import all models to register with Base.metadata
from app.models.users import User, UserProfile, Address, UserActivity, RevokedToken
from app.models.catalog import Category, Brand, Product, ProductVariant, ProductMedia, ProductAttribute, PriceHistory
from app.models.inventory import (
    Warehouse, InventoryItem, InventoryMovement, InventoryTransfer,
    InventoryTransferItem, StockAlert, InventoryReservation, InventoryBatch, StockDiscrepancy
)
from app.models.orders import (
    Cart, CartItem, Wishlist, Coupon, Promotion, TaxRate, ShippingMethod,
    Order, OrderItem, OrderStatusHistory, OrderCancellation, PromotionRedemption
)
from app.models.payments import Payment, PaymentTransaction, Refund, CODRecord, PaymentExceptionLog
from app.models.logistics import (
    Shipment, ShipmentTrackingEvent, DeliveryAssignment, ReturnRequest,
    ReturnItem, ExchangeRequest, ShipmentItem, WarrantyClaim
)
from app.models.engagement import (
    ProductReview, ProductQuestion, ProductAnswer, SupportTicket,
    TicketMessage, Notification, NotificationDeliveryLog, CustomerNotificationPreference
)
from app.models.suppliers import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierInvoice
from app.models.system import AuditLog, BackgroundTaskLog
from app.models.segmentation import CustomerSegment, CustomerSegmentMember, CustomerTag, CustomerNote
from app.models.loyalty import LoyaltyAccount, LoyaltyRule, LoyaltyTransaction
from app.models.sellers import SellerProfile, CommissionRule, SellerSettlement
from app.models.support import SupportCase, CaseMessage
from app.models.integrations import IntegrationConfig, IntegrationLog
