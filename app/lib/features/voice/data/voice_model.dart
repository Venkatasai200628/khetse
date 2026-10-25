/// Voice-to-listing models — `backend/app/api/v1/voice.py`. Fields are
/// parsed defensively: the extraction model is probabilistic and every
/// field may be missing, which is exactly why the UI re-confirms them.
class VoiceStatus {
  VoiceStatus({
    required this.simulated,
    this.provider,
    this.samplePhrases = const [],
  });

  /// true while the backend runs the simulated speech provider (demo
  /// mode) — the UI must say so honestly instead of pretending ASR ran.
  final bool simulated;
  final String? provider;
  final List<String> samplePhrases;

  factory VoiceStatus.fromJson(Map<String, dynamic> json) => VoiceStatus(
        simulated: (json['simulated'] ?? false) as bool,
        provider: json['provider'] as String?,
        samplePhrases: (json['sample_phrases'] as List? ?? [])
            .map((e) => e.toString())
            .toList(),
      );
}

class VoiceDraft {
  VoiceDraft({
    required this.transcript,
    required this.provider,
    required this.simulated,
    required this.fieldsNeedingConfirmation,
    required this.extracted,
  });

  final String transcript;

  /// 'simulated' in demo mode, 'bhashini' when the real pipeline runs.
  final String? provider;
  final bool simulated;

  /// Field names the extractor is unsure about — highlighted in the
  /// confirmation form (e.g. 'quantity', 'price', 'commodity', 'unit').
  final List<String> fieldsNeedingConfirmation;
  final VoiceExtracted extracted;

  factory VoiceDraft.fromJson(Map<String, dynamic> json) => VoiceDraft(
        transcript: (json['transcript'] ?? '') as String,
        provider: json['provider'] as String?,
        simulated: (json['simulated'] ?? false) as bool,
        fieldsNeedingConfirmation:
            (json['fields_needing_confirmation'] as List? ?? [])
                .map((e) => e.toString())
                .toList(),
        extracted: VoiceExtracted.fromJson(
          (json['extracted'] as Map? ?? {}).cast<String, dynamic>(),
        ),
      );

  /// Honest provider label — never imply real speech when simulated.
  String providerLabel() {
    if (simulated) return 'Simulated (demo)';
    final p = (provider ?? '').toLowerCase();
    if (p.contains('bhashini')) return 'Bhashini';
    return provider == null || provider!.isEmpty ? 'Speech' : provider!;
  }

  bool needsConfirmation(String field) => fieldsNeedingConfirmation
      .any((f) => f.toLowerCase().trim() == field.toLowerCase().trim());
}

class VoiceExtracted {
  VoiceExtracted({
    required this.commodity,
    required this.quantity,
    required this.unit,
    required this.pricePaise,
    required this.availableFrom,
  });

  /// Commodity name as recognised from the phrase (e.g. 'tomato') — the UI
  /// matches it against the live catalogue; it may be null.
  final String? commodity;
  final double? quantity;
  final String? unit;
  final int? pricePaise;
  final DateTime? availableFrom;

  factory VoiceExtracted.fromJson(Map<String, dynamic> json) =>
      VoiceExtracted(
        commodity: json['commodity'] as String?,
        quantity: (json['quantity'] as num?)?.toDouble(),
        unit: json['unit'] as String?,
        pricePaise: (json['price_paise'] as num?)?.toInt(),
        availableFrom: _parseDate(json['available_from'] as String?),
      );

  static DateTime? _parseDate(String? value) =>
      value == null || value.isEmpty ? null : DateTime.tryParse(value);
}
