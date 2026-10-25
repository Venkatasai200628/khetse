import '../../../core/utils/dates.dart';

/// Produce listing — mirrors `ListingPublic`/`ListingOwnerPublic`
/// in `backend/app/schemas/listing.py`. Money is integer paise.
class Listing {
  Listing({
    required this.id,
    required this.farmerId,
    required this.commodityId,
    required this.commodityName,
    required this.commodityNameTe,
    required this.commodityCategory,
    required this.description,
    required this.quantityTotal,
    required this.quantityAvailable,
    required this.unit,
    required this.qualityGrade,
    required this.harvestDate,
    required this.availableFrom,
    required this.minPricePaise,
    required this.listedPricePaise,
    required this.status,
    required this.isSynthetic,
    required this.farmerDistrict,
    required this.farmerVillage,
    required this.createdAt,
  });

  final String id;
  final String farmerId;
  final String commodityId;
  final String? commodityName;
  final String? commodityNameTe;
  final String? commodityCategory;
  final String? description;
  final double quantityTotal;
  final double quantityAvailable;
  final String unit;
  final String qualityGrade;
  final DateTime? harvestDate;
  final DateTime? availableFrom;
  final int minPricePaise;
  final int listedPricePaise;
  final String status;
  final bool isSynthetic;
  final String? farmerDistrict;
  final String? farmerVillage;
  final DateTime createdAt;

  factory Listing.fromJson(Map<String, dynamic> json) => Listing(
        id: json['id'] as String,
        farmerId: json['farmer_id'] as String,
        commodityId: json['commodity_id'] as String,
        commodityName: json['commodity_name'] as String?,
        commodityNameTe: json['commodity_name_te'] as String?,
        commodityCategory: json['commodity_category'] as String?,
        description: json['description'] as String?,
        quantityTotal: (json['quantity_total'] as num).toDouble(),
        quantityAvailable: (json['quantity_available'] as num).toDouble(),
        unit: json['unit'] as String,
        qualityGrade: (json['quality_grade'] ?? 'ungraded') as String,
        harvestDate: _parseDate(json['harvest_date'] as String?),
        availableFrom: _parseDate(json['available_from'] as String?),
        minPricePaise: (json['min_price_paise'] ?? 0) as int,
        listedPricePaise: (json['listed_price_paise'] ?? 0) as int,
        status: json['status'] as String,
        isSynthetic: (json['is_synthetic'] ?? false) as bool,
        farmerDistrict: json['farmer_district'] as String?,
        farmerVillage: json['farmer_village'] as String?,
        createdAt:
            DateTime.tryParse(json['created_at'] as String? ?? '') ??
                DateTime.now(),
      );

  static DateTime? _parseDate(String? value) =>
      value == null || value.isEmpty ? null : DateTime.tryParse(value);

  String get title => commodityName ?? 'Produce';
  String get originLabel {
    final parts = [?farmerVillage, ?farmerDistrict];
    return parts.isEmpty ? 'Farm direct' : parts.join(', ');
  }

  String get quantityLabel =>
      '${_trimNum(quantityTotal)} $unit${quantityTotal == 1 ? '' : 's'}';

  String get availableLabel =>
      '${_trimNum(quantityAvailable)} $unit available';

  String get listedLabel => '₹${_trimNum(listedPricePaise / 100)}/$unit';

  String? get harvestedLabel =>
      harvestDate == null ? null : formatRelative(harvestDate!);

  static String _trimNum(double v) =>
      v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(1);
}

/// Commodity catalogue entry — `backend/app/api/v1/commodities.py`.
class Commodity {
  Commodity({
    required this.id,
    required this.nameEn,
    required this.nameTe,
    required this.nameHi,
    required this.category,
    required this.defaultUnit,
  });

  final String id;
  final String nameEn;
  final String? nameTe;
  final String? nameHi;
  final String category;
  final String defaultUnit;

  factory Commodity.fromJson(Map<String, dynamic> json) => Commodity(
        id: json['id'] as String,
        nameEn: json['name_en'] as String,
        nameTe: json['name_te'] as String?,
        nameHi: json['name_hi'] as String?,
        category: json['category'] as String,
        defaultUnit: (json['default_unit'] ?? 'kg') as String,
      );
}

/// Page of listings — `ListingPage` schema.
class ListingPage {
  ListingPage({required this.items, required this.total});

  final List<Listing> items;
  final int total;

  factory ListingPage.fromJson(Map<String, dynamic> json) => ListingPage(
        items: (json['items'] as List? ?? [])
            .map((e) => Listing.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: (json['total'] ?? 0) as int,
      );
}
