import '../../../core/utils/dates.dart';

/// Request-for-quote — mirrors the `/rfq` schemas. A business posts what
/// it needs; farmers quote against it; accepting an offer creates an order.
/// Money is integer paise throughout.
class Rfq {
  Rfq({
    required this.id,
    required this.buyerId,
    required this.buyerLabel,
    required this.commodityId,
    required this.commodityName,
    required this.quantity,
    required this.unit,
    required this.neededBy,
    required this.maxPricePaise,
    required this.status,
    required this.createdAt,
    required this.offers,
  });

  final String id;
  final String buyerId;

  /// Privacy-safe buyer label from the API — displayed as-is.
  final String? buyerLabel;
  final String commodityId;
  final String? commodityName;
  final double quantity;
  final String unit;
  final DateTime? neededBy;
  final int maxPricePaise;

  /// open | closed | fulfilled (defensive).
  final String status;
  final DateTime? createdAt;
  final List<RfqOffer> offers;

  factory Rfq.fromJson(Map<String, dynamic> json) => Rfq(
        id: json['id'] as String,
        buyerId: (json['buyer_id'] ?? '') as String,
        buyerLabel:
            (json['buyer_label'] ?? json['buyer_name']) as String?,
        commodityId: (json['commodity_id'] ?? '') as String,
        commodityName: json['commodity_name'] as String?,
        quantity: ((json['quantity'] ?? 0) as num).toDouble(),
        unit: (json['unit'] ?? 'kg') as String,
        neededBy: _parseDate(json['needed_by'] as String?),
        maxPricePaise: ((json['max_price_paise'] ?? 0) as num).toInt(),
        status: (json['status'] ?? 'open') as String,
        createdAt: _parseDate(json['created_at'] as String?),
        offers: (json['offers'] as List? ?? [])
            .map((e) => RfqOffer.fromJson((e as Map).cast<String, dynamic>()))
            .toList(),
      );

  bool get isOpen => status.toLowerCase() == 'open';

  String get title => commodityName ?? 'Produce';

  String get quantityLabel => '${_trim(quantity)} $unit';

  String get maxPriceLabel => 'up to ₹${_trim(maxPricePaise / 100)}/$unit';

  String get neededByLabel =>
      neededBy == null ? '—' : formatDate(neededBy!);

  static DateTime? _parseDate(String? value) =>
      value == null || value.isEmpty ? null : DateTime.tryParse(value);

  static String _trim(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(1);
}

/// A farmer's quote against an RFQ.
class RfqOffer {
  RfqOffer({
    required this.id,
    required this.rfqId,
    required this.farmerLabel,
    required this.quantity,
    required this.unit,
    required this.pricePaise,
    required this.status,
    required this.createdAt,
  });

  final String id;
  final String? rfqId;

  /// Privacy-safe farmer label from the API — displayed as-is.
  final String? farmerLabel;
  final double? quantity;
  final String? unit;
  final int pricePaise;

  /// pending | accepted | rejected | withdrawn (defensive).
  final String status;
  final DateTime? createdAt;

  factory RfqOffer.fromJson(Map<String, dynamic> json) => RfqOffer(
        id: json['id'] as String,
        rfqId: json['rfq_id'] as String?,
        farmerLabel:
            (json['farmer_label'] ?? json['farmer_name']) as String?,
        quantity: (json['quantity'] as num?)?.toDouble(),
        unit: json['unit'] as String?,
        pricePaise: ((json['price_paise'] ?? json['quoted_price_paise'] ?? 0)
                as num)
            .toInt(),
        status: (json['status'] ?? 'pending') as String,
        createdAt: Rfq._parseDate(json['created_at'] as String?),
      );

  bool get isAccepted => status.toLowerCase() == 'accepted';

  bool get isPending => status.toLowerCase() == 'pending';

  String get priceLabel => '₹${_trim(pricePaise / 100)}${unit == null ? '' : '/$unit'}';

  static String _trim(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(2);
}
