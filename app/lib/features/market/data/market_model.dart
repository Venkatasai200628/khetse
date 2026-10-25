import '../../../core/utils/dates.dart';
import '../../../core/utils/money.dart';

/// Price recommendation — mirrors `RecommendationOut` in
/// `backend/app/api/v1/market.py`. All amounts are integer paise per
/// [unit]; a `quintal` unit means the range is per-quintal (the API also
/// provides the modal price converted per kg).
class PriceRecommendation {
  PriceRecommendation({
    required this.id,
    required this.commodityId,
    required this.commodityName,
    required this.district,
    required this.recommendedMinPaise,
    required this.recommendedModalPaise,
    required this.recommendedMaxPaise,
    required this.recommendedModalPerKgPaise,
    required this.unit,
    required this.benchmarkMarket,
    required this.benchmarkObservedOn,
    required this.benchmarkSource,
    required this.confidence,
    required this.explanation,
    required this.modelRun,
  });

  final String id;
  final String commodityId;
  final String commodityName;
  final String? district;
  final int? recommendedMinPaise;
  final int recommendedModalPaise;
  final int? recommendedMaxPaise;
  final int? recommendedModalPerKgPaise;
  final String? unit;
  final String? benchmarkMarket;
  final DateTime? benchmarkObservedOn;
  final String? benchmarkSource;

  /// low | medium | high — colour-coded chip in the UI.
  final String confidence;
  final String? explanation;
  final ModelRun modelRun;

  factory PriceRecommendation.fromJson(Map<String, dynamic> json) =>
      PriceRecommendation(
        id: json['id'] as String,
        commodityId: json['commodity_id'] as String,
        commodityName: (json['commodity_name'] ?? '') as String,
        district: json['district'] as String?,
        recommendedMinPaise: (json['recommended_min_paise'] as num?)?.toInt(),
        recommendedModalPaise:
            ((json['recommended_modal_paise'] ?? 0) as num).toInt(),
        recommendedMaxPaise: (json['recommended_max_paise'] as num?)?.toInt(),
        recommendedModalPerKgPaise:
            (json['recommended_modal_per_kg_paise'] as num?)?.toInt(),
        unit: json['unit'] as String?,
        benchmarkMarket: json['benchmark_market'] as String?,
        benchmarkObservedOn: _parseDate(json['benchmark_observed_on'] as String?),
        benchmarkSource: json['benchmark_source'] as String?,
        confidence: (json['confidence'] ?? 'medium') as String,
        explanation: json['explanation'] as String?,
        modelRun: ModelRun.fromJson(
          (json['model_run'] as Map? ?? {}).cast<String, dynamic>(),
        ),
      );

  static DateTime? _parseDate(String? value) =>
      value == null || value.isEmpty ? null : DateTime.tryParse(value);

  bool get isQuintal => (unit ?? '').toLowerCase() == 'quintal';

  /// `min – modal – max` for the recommendation card headline.
  String get rangeLabel {
    String part(int? paise) =>
        paise == null ? '—' : formatPaise(paise, withSymbol: false);
    return '${part(recommendedMinPaise)} – ${part(recommendedModalPaise)} – '
        '${part(recommendedMaxPaise)}';
  }

  /// Footnote line with full model provenance — never an opaque number.
  String get provenanceLabel =>
      'Model ${modelRun.modelVersion} · ran ${formatDateTime(modelRun.ranAt)}';
}

/// Provenance of the model run behind a recommendation —
/// `ModelRunOut` in `backend/app/api/v1/market.py`.
class ModelRun {
  ModelRun({
    required this.id,
    required this.modelType,
    required this.modelVersion,
    required this.ranAt,
    required this.notes,
  });

  final String id;
  final String modelType;
  final String modelVersion;
  final DateTime ranAt;
  final String? notes;

  factory ModelRun.fromJson(Map<String, dynamic> json) => ModelRun(
        id: json['id'] as String,
        modelType: (json['model_type'] ?? '') as String,
        modelVersion: (json['model_version'] ?? '?') as String,
        ranAt: DateTime.tryParse(json['ran_at'] as String? ?? '') ??
            DateTime.now(),
        notes: json['notes'] as String?,
      );
}
