import '../../../core/utils/dates.dart';

/// Delivery run — mirrors the `/shipments` schemas built on the backend
/// (Phase 4). Buyer labels are privacy-safe strings produced by the API
/// and are displayed as-is. Every field is parsed defensively because the
/// backend is the single source of truth for the stop ordering.
class Shipment {
  Shipment({
    required this.id,
    required this.status,
    required this.distanceKm,
    required this.originLabel,
    required this.destinationLabel,
    required this.driverId,
    required this.stops,
    required this.crates,
    required this.createdAt,
  });

  final String id;

  /// draft | ready | in_transit | completed | failed | cancelled (defensive).
  final String status;
  final double? distanceKm;
  final String? originLabel;
  final String? destinationLabel;
  final String? driverId;
  final List<ShipmentStop> stops;
  final List<ShipmentCrate> crates;
  final DateTime? createdAt;

  factory Shipment.fromJson(Map<String, dynamic> json) => Shipment(
        id: json['id'] as String,
        status: (json['status'] ?? 'draft') as String,
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
        originLabel: json['origin_label'] as String?,
        destinationLabel: json['destination_label'] as String?,
        driverId: json['driver_id'] as String?,
        stops: (json['stops'] as List? ?? [])
            .map((e) => ShipmentStop.fromJson(e as Map<String, dynamic>))
            .toList()
          ..sort((a, b) => a.sequence.compareTo(b.sequence)),
        crates: (json['crates'] as List? ?? [])
            .map((e) => ShipmentCrate.fromJson(e as Map<String, dynamic>))
            .toList(),
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );

  int get stopCount => stops.length;

  int get pendingStopCount =>
      stops.where((s) => !s.isDone && !s.isFailed).length;

  String get distanceLabel =>
      distanceKm == null ? '—' : '${_trim(distanceKm!)} km';

  String get routeLabel {
    final parts = [?originLabel, ?destinationLabel];
    return parts.isEmpty ? 'Delivery run' : parts.join(' → ');
  }

  bool get canStart {
    final s = status.toLowerCase();
    return s == 'draft' || s == 'ready' || s == 'scheduled';
  }

  static String _trim(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(1);
}

/// One ordered stop of a run — pickup (collection centre / farmer) or
/// delivery (buyer drop-off).
class ShipmentStop {
  ShipmentStop({
    required this.id,
    required this.sequence,
    required this.kind,
    required this.label,
    required this.status,
    required this.address,
    required this.orderId,
  });

  final String id;
  final int sequence;

  /// 'pickup' | 'delivery'.
  final String kind;

  /// Privacy-safe label from the API — displayed as-is.
  final String label;

  /// pending | completed | skipped | failed (defensive).
  final String status;
  final String? address;
  final String? orderId;

  factory ShipmentStop.fromJson(Map<String, dynamic> json) => ShipmentStop(
        id: json['id'] as String,
        sequence: ((json['sequence'] ?? json['seq'] ?? 0) as num).toInt(),
        kind: (json['kind'] ?? json['type'] ?? 'delivery') as String,
        label: (json['label'] ?? '') as String,
        status: (json['status'] ?? 'pending') as String,
        address: json['address'] as String?,
        orderId: json['order_id'] as String?,
      );

  bool get isPickup => kind.toLowerCase() == 'pickup';

  bool get isDone => status.toLowerCase() == 'completed';

  bool get isFailed => status.toLowerCase() == 'failed';

  bool get isActionable =>
      !isDone && !isFailed && status.toLowerCase() != 'skipped';
}

/// Crate in the run manifest — codes are what the QR tokens resolve to.
class ShipmentCrate {
  ShipmentCrate({
    required this.code,
    required this.orderId,
    required this.status,
  });

  final String code;
  final String? orderId;
  final String? status;

  factory ShipmentCrate.fromJson(Map<String, dynamic> json) => ShipmentCrate(
        code: (json['code'] ?? json['crate_code'] ?? '') as String,
        orderId: json['order_id'] as String?,
        status: json['status'] as String?,
      );
}

/// Driver option for the FPO dispatch form — GET /drivers.
class DriverOption {
  DriverOption({
    required this.id,
    required this.name,
    required this.phone,
    required this.status,
  });

  final String id;
  final String? name;
  final String? phone;
  final String? status;

  factory DriverOption.fromJson(Map<String, dynamic> json) => DriverOption(
        id: json['id'] as String,
        name: (json['full_name'] ?? json['name']) as String?,
        phone: json['phone'] as String?,
        status: json['status'] as String?,
      );

  String get label => (name == null || name!.trim().isEmpty)
      ? 'Driver …${id.length > 6 ? id.substring(id.length - 6) : id}'
      : name!;
}

/// Timestamp helper for cards.
String shipmentCreatedLabel(Shipment s) =>
    s.createdAt == null ? '' : formatRelative(s.createdAt!);
