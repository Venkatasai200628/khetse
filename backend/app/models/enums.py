"""Shared enumerations used across the schema.

Quantity columns are Float (kg/pieces — precision handled by rounding in
services); ALL monetary columns are integer paise — never floats.
"""

import enum


class RoleEnum(str, enum.Enum):
    FARMER = "farmer"
    BUYER = "buyer"
    BUSINESS = "business"
    DRIVER = "driver"
    FPO_OPERATOR = "fpo_operator"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UnitEnum(str, enum.Enum):
    KG = "kg"
    QUINTAL = "quintal"
    TONNE = "tonne"
    DOZEN = "dozen"
    PIECE = "piece"
    LITRE = "litre"
    BUNCH = "bunch"


class CommodityCategory(str, enum.Enum):
    FRUIT = "fruit"
    VEGETABLE = "vegetable"
    GRAIN = "grain"
    PULSE = "pulse"
    OTHER = "other"


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD_OUT = "sold_out"
    WITHDRAWN = "withdrawn"


class QualityGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    UNGRADED = "ungraded"


class DataQualityStatus(str, enum.Enum):
    VALID = "valid"
    STALE = "stale"
    ANOMALOUS = "anomalous"
    MISSING_FIELDS = "missing_fields"


class PriceSourceType(str, enum.Enum):
    AGMARKNET = "agmarknet"
    CONSUMER_AFFAIRS = "consumer_affairs"
    PLATFORM_TRANSACTION = "platform_transaction"
    SYNTHETIC = "synthetic"


class RecommendationConfidence(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OrderStatus(str, enum.Enum):
    CREATED = "created"
    AWAITING_FARMER_CONFIRMATION = "awaiting_farmer_confirmation"
    ACCEPTED = "accepted"
    PAYMENT_PENDING = "payment_pending"
    CONFIRMED = "confirmed"
    PICKUP_SCHEDULED = "pickup_scheduled"
    PICKED_UP = "picked_up"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    # Terminal / exception states
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    DELIVERY_FAILED = "delivery_failed"
    DISPUTED = "disputed"


class PaymentStatus(str, enum.Enum):
    """Tracked separately from OrderStatus — delivery ≠ settlement."""
    INITIATED = "initiated"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUND_PENDING = "refund_pending"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


class PaymentProviderKind(str, enum.Enum):
    MOCK = "mock"  # clearly-labelled sandbox
    RAZORPAY = "razorpay"


class FulfilmentType(str, enum.Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"  # buyer collects from collection centre


class OfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class PurchaseRequestStatus(str, enum.Enum):
    OPEN = "open"
    QUOTED = "quoted"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    RELEASED = "released"


class FarmerResponseStatus(str, enum.Enum):
    """Per-farmer response on an order line (multi-farmer carts)."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ShipmentStatus(str, enum.Enum):
    PLANNED = "planned"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class StopType(str, enum.Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class StopStatus(str, enum.Enum):
    PENDING = "pending"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    FAILED = "failed"


class CrateStatus(str, enum.Enum):
    CREATED = "created"
    SCANNED_PICKUP = "scanned_pickup"
    SCANNED_DELIVERY = "scanned_delivery"


class QrPurpose(str, enum.Enum):
    PICKUP_VERIFICATION = "pickup_verification"
    DELIVERY_VERIFICATION = "delivery_verification"


class QrMethod(str, enum.Enum):
    QR_SCAN = "qr_scan"
    MANUAL_CODE = "manual_code"
    OPERATOR_OVERRIDE = "operator_override"


class LedgerEntryType(str, enum.Enum):
    PAYMENT_IN = "payment_in"            # buyer payment received (escrow/sandbox)
    FARMER_PROCEEDS = "farmer_proceeds"  # gross owed to farmer
    PLATFORM_FEE = "platform_fee"
    DELIVERY_FEE_IN = "delivery_fee_in"  # delivery fee charged to buyer
    DRIVER_PAYOUT = "driver_payout"      # delivery fee paid to driver
    REFUND_OUT = "refund_out"
    ADJUSTMENT = "adjustment"


class SettlementStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    PAID = "paid"
    FAILED = "failed"


class RefundStatus(str, enum.Enum):
    REQUESTED = "requested"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    SMS = "sms"
    VOICE = "voice"


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class CommunicationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class GrievanceStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class GrievanceCategory(str, enum.Enum):
    ORDER = "order"
    PAYMENT = "payment"
    QUALITY = "quality"
    DELIVERY = "delivery"
    OTHER = "other"


class ModelType(str, enum.Enum):
    PRICE_RECOMMENDATION = "price_recommendation"
    DEMAND_FORECAST = "demand_forecast"
    ROUTING = "routing"
    QUALITY = "quality"


class ImportJobStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BusinessType(str, enum.Enum):
    KIRANA = "kirana"
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    CANTEEN = "canteen"
    INSTITUTION = "institution"
    OTHER = "other"


class VehicleType(str, enum.Enum):
    BIKE = "bike"
    AUTO = "auto"
    MINI_TRUCK = "mini_truck"
    TEMPO = "tempo"
    TRUCK = "truck"
