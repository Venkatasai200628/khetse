import '../../../core/utils/dates.dart';

/// Order — mirrors `OrderPublic` in `backend/app/schemas/order.py`.
class Order {
  Order({
    required this.id,
    required this.buyerId,
    required this.status,
    required this.paymentStatus,
    required this.fulfilment,
    required this.deliveryName,
    required this.deliveryAddress,
    required this.deliveryDistrict,
    required this.subtotalPaise,
    required this.deliveryFeePaise,
    required this.platformFeePaise,
    required this.totalPaise,
    required this.currency,
    required this.notes,
    required this.cancelReason,
    required this.placedAt,
    required this.deliveredAt,
    required this.isSynthetic,
    required this.createdAt,
    required this.items,
    required this.statusEvents,
  });

  final String id;
  final String buyerId;
  final String status;
  final String paymentStatus;
  final String fulfilment;
  final String? deliveryName;
  final String? deliveryAddress;
  final String? deliveryDistrict;
  final int subtotalPaise;
  final int deliveryFeePaise;
  final int platformFeePaise;
  final int totalPaise;
  final String currency;
  final String? notes;
  final String? cancelReason;
  final DateTime? placedAt;
  final DateTime? deliveredAt;
  final bool isSynthetic;
  final DateTime createdAt;
  final List<OrderItem> items;
  final List<OrderStatusEvent> statusEvents;

  factory Order.fromJson(Map<String, dynamic> json) => Order(
        id: json['id'] as String,
        buyerId: json['buyer_id'] as String,
        status: json['status'] as String,
        paymentStatus: (json['payment_status'] ?? 'PENDING') as String,
        fulfilment: (json['fulfilment'] ?? 'DELIVERY') as String,
        deliveryName: json['delivery_name'] as String?,
        deliveryAddress: json['delivery_address'] as String?,
        deliveryDistrict: json['delivery_district'] as String?,
        subtotalPaise: (json['subtotal_paise'] ?? 0) as int,
        deliveryFeePaise: (json['delivery_fee_paise'] ?? 0) as int,
        platformFeePaise: (json['platform_fee_paise'] ?? 0) as int,
        totalPaise: (json['total_paise'] ?? 0) as int,
        currency: (json['currency'] ?? 'INR') as String,
        notes: json['notes'] as String?,
        cancelReason: json['cancel_reason'] as String?,
        placedAt: _parse(json['placed_at'] as String?),
        deliveredAt: _parse(json['delivered_at'] as String?),
        isSynthetic: (json['is_synthetic'] ?? false) as bool,
        createdAt:
            DateTime.tryParse(json['created_at'] as String? ?? '') ??
                DateTime.now(),
        items: (json['items'] as List? ?? [])
            .map((e) => OrderItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        statusEvents: (json['status_events'] as List? ?? [])
            .map((e) => OrderStatusEvent.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  static DateTime? _parse(String? v) =>
      v == null || v.isEmpty ? null : DateTime.tryParse(v);

  String get itemSummary =>
      items.map((i) => '${i.commodityName ?? 'Item'} ×${i.quantityLabel}').join(', ');

  String get placedLabel => placedAt == null
      ? formatRelative(createdAt)
      : formatRelative(placedAt!);

  // Backend enum values are lowercase — compare case-insensitively.
  bool get canBuyerCancel {
    final s = status.toUpperCase();
    return s != 'CANCELLED' &&
        s != 'COMPLETED' &&
        s != 'REJECTED' &&
        s != 'DELIVERED';
  }

  bool get awaitingFarmer =>
      items.any((i) => i.farmerResponse.toUpperCase() == 'PENDING') &&
      status.toUpperCase() == 'AWAITING_FARMER_CONFIRMATION';
}

class OrderItem {
  OrderItem({
    required this.id,
    required this.listingId,
    required this.farmerId,
    required this.quantity,
    required this.unit,
    required this.unitPricePaise,
    required this.lineTotalPaise,
    required this.qualityGrade,
    required this.farmerResponse,
    required this.commodityName,
  });

  final String id;
  final String listingId;
  final String farmerId;
  final double quantity;
  final String? unit;
  final int unitPricePaise;
  final int lineTotalPaise;
  final String? qualityGrade;
  final String farmerResponse;
  final String? commodityName;

  factory OrderItem.fromJson(Map<String, dynamic> json) => OrderItem(
        id: json['id'] as String,
        listingId: json['listing_id'] as String,
        farmerId: json['farmer_id'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        unit: json['unit'] as String?,
        unitPricePaise: (json['unit_price_paise'] ?? 0) as int,
        lineTotalPaise: (json['line_total_paise'] ?? 0) as int,
        qualityGrade: json['quality_grade'] as String?,
        farmerResponse: (json['farmer_response'] ?? 'PENDING') as String,
        commodityName: json['commodity_name'] as String?,
      );

  String get quantityLabel => unit == null
      ? _trim(quantity)
      : '${_trim(quantity)} $unit';

  static String _trim(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(1);
}

class OrderStatusEvent {
  OrderStatusEvent({
    required this.id,
    required this.fromStatus,
    required this.toStatus,
    required this.actorRole,
    required this.reason,
    required this.createdAt,
  });

  final String id;
  final String? fromStatus;
  final String toStatus;
  final String? actorRole;
  final String? reason;
  final DateTime createdAt;

  factory OrderStatusEvent.fromJson(Map<String, dynamic> json) =>
      OrderStatusEvent(
        id: json['id'] as String,
        fromStatus: json['from_status'] as String?,
        toStatus: json['to_status'] as String,
        actorRole: json['actor_role'] as String?,
        reason: json['reason'] as String?,
        createdAt:
            DateTime.tryParse(json['created_at'] as String? ?? '') ??
                DateTime.now(),
      );

  String get whenLabel => formatDateTime(createdAt);
}

/// Page of orders — `OrderPage` schema.
class OrderPage {
  OrderPage({required this.items, required this.total});

  final List<Order> items;
  final int total;

  factory OrderPage.fromJson(Map<String, dynamic> json) => OrderPage(
        items: (json['items'] as List? ?? [])
            .map((e) => Order.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: (json['total'] ?? 0) as int,
      );
}
