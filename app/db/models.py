from app.db.base import Base, TimestampMixin

# Import all models to register with Base.metadata
from app.models.users import User, UserProfile, Address, UserActivity, RevokedToken
from app.models.catalog import Category, Brand, Product, ProductVariant, ProductMedia, ProductAttribute, PriceHistory
from app.models.inventory import Warehouse, InventoryItem, InventoryMovement, InventoryTransfer, InventoryTransferItem, StockAlert
from app.models.orders import Cart, CartItem, Wishlist, Coupon, Promotion, TaxRate, ShippingMethod, Order, OrderItem, OrderStatusHistory, OrderCancellation
from app.models.payments import Payment, PaymentTransaction, Refund, CODRecord
from app.models.logistics import Shipment, ShipmentTrackingEvent, DeliveryAssignment, ReturnRequest, ReturnItem, ExchangeRequest
from app.models.engagement import ProductReview, ProductQuestion, ProductAnswer, SupportTicket, TicketMessage, Notification, NotificationDeliveryLog
from app.models.suppliers import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierInvoice
from app.models.system import AuditLog, BackgroundTaskLog
