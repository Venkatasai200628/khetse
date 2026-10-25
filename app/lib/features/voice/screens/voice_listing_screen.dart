import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../l10n/app_localizations.dart';
import '../../farmer/farmer_shell.dart';
import '../../marketplace/data/listing_model.dart';
import '../../marketplace/data/providers.dart';
import '../data/providers.dart';
import '../data/voice_model.dart';

const _units = ['kg', 'quintal', 'tonne', 'dozen', 'piece', 'litre', 'bunch'];

/// Speak to sell — GET /voice/status, then POST /voice/listing-draft with
/// the phrase. The extracted draft is always shown in an editable
/// confirmation form (fields the model is unsure about are highlighted)
/// before publishing through the normal POST /listings flow.
class VoiceListingScreen extends ConsumerStatefulWidget {
  const VoiceListingScreen({super.key});

  @override
  ConsumerState<VoiceListingScreen> createState() =>
      _VoiceListingScreenState();
}

class _VoiceListingScreenState extends ConsumerState<VoiceListingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phraseController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();

  VoiceDraft? _draft;
  Commodity? _commodity;
  String _unit = 'kg';
  DateTime? _availableFrom;
  bool _drafting = false;
  bool _publishing = false;
  Object? _draftError;

  @override
  void dispose() {
    _phraseController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  Future<void> _submitPhrase() async {
    final text = _phraseController.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _drafting = true;
      _draftError = null;
    });
    try {
      final t = AppLocalizations.of(context);
      final draft = await ref
          .read(voiceApiProvider)
          .draft(text: text, language: t.localeName);
      _applyDraft(draft);
      if (mounted) setState(() => _drafting = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _drafting = false;
          _draftError = e;
        });
      }
    }
  }

  /// Prefills the confirmation form from the extraction — commodity is
  /// matched against the live catalogue; anything unmatched stays blank
  /// for the farmer to choose.
  void _applyDraft(VoiceDraft draft) {
    final extracted = draft.extracted;
    _commodity = _matchCommodity(extracted.commodity);
    _unit = (extracted.unit != null && _units.contains(extracted.unit))
        ? extracted.unit!
        : _commodity?.defaultUnit ?? 'kg';
    _quantityController.text = extracted.quantity == null
        ? ''
        : _trimNum(extracted.quantity!);
    _priceController.text = extracted.pricePaise == null
        ? ''
        : _trimNum(extracted.pricePaise! / 100);
    _availableFrom = extracted.availableFrom;
    setState(() => _draft = draft);
  }

  Commodity? _matchCommodity(String? name) {
    if (name == null || name.trim().isEmpty) return null;
    final needle = name.trim().toLowerCase();
    try {
      final items = ref.read(commoditiesProvider).value ?? const [];
      for (final c in items) {
        if (c.nameEn.toLowerCase() == needle) return c;
        if ((c.nameTe ?? '').toLowerCase() == needle) return c;
      }
      for (final c in items) {
        if (c.nameEn.toLowerCase().contains(needle)) return c;
        if ((c.nameTe ?? '').toLowerCase().contains(needle)) return c;
      }
    } catch (_) {
      // Catalogue not loaded yet — the farmer picks manually.
    }
    return null;
  }

  Future<void> _pickAvailableFrom() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _availableFrom ?? now,
      firstDate: now,
      lastDate: now.add(const Duration(days: 120)),
    );
    if (picked != null) setState(() => _availableFrom = picked);
  }

  Future<void> _publish() async {
    final validated = _formKey.currentState?.validate() ?? false;
    final priceRupees = double.tryParse(_priceController.text.trim());
    if (!validated || priceRupees == null || priceRupees <= 0) return;

    setState(() => _publishing = true);
    try {
      // Same POST /listings flow as the manual form — integer paise.
      final listedPaise = rupeesToPaise(priceRupees);
      await ref.read(listingApiProvider).create(
            commodityId: _commodity!.id,
            quantityTotal: double.parse(_quantityController.text.trim()),
            unit: _unit,
            minPricePaise: (listedPaise * 0.9).round(),
            listedPricePaise: listedPaise,
            availableFrom: _availableFrom,
          );
      ref.invalidate(myListingsProvider);
      if (mounted) {
        final t = AppLocalizations.of(context);
        // Land on the farmer's listings tab with a success snackbar.
        ref.read(farmerShellTabProvider.notifier).state = 1;
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(t.voicePublished)));
        context.go('/farmer');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _publishing = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final statusAsync = ref.watch(voiceStatusProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.voiceTitle)),
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                t.voiceSubtitle,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 16),
              statusAsync.when(
                loading: () => const SkeletonBox(height: 64, radius: 14),
                error: (e, _) => ErrorView(
                  message: e.toString(),
                  onRetry: () => ref.invalidate(voiceStatusProvider),
                  compact: true,
                ),
                data: (status) => Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (status.simulated)
                      _demoBanner(),
                    if (status.samplePhrases.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      _sampleChips(status.samplePhrases),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 14),
              _sampleChips([t.voiceSampleEn, t.voiceSampleTe]),
              const SizedBox(height: 16),
              TextField(
                controller: _phraseController,
                minLines: 1,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: t.voiceFieldLabel,
                  hintText: t.voiceHint,
                  prefixIcon: const Icon(Icons.mic_rounded, size: 22),
                ),
                onSubmitted: (_) => _submitPhrase(),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _drafting || _publishing ? null : _submitPhrase,
                icon: _drafting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.2, color: Colors.white),
                      )
                    : const Icon(Icons.graphic_eq_rounded, size: 20),
                label: Text(t.voiceDraftButton),
              ),
              if (_draftError != null) ...[
                const SizedBox(height: 14),
                ErrorView(
                  message: _draftError.toString(),
                  onRetry: _submitPhrase,
                  compact: true,
                ),
              ],
              if (_draft != null) ...[
                const SizedBox(height: 24),
                _transcriptCard(context, _draft!),
                const SizedBox(height: 16),
                _confirmationForm(context),
              ],
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _demoBanner() => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.warning.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(12),
          border:
              Border.all(color: AppColors.warning.withValues(alpha: 0.4)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.speaker_notes_off_rounded,
                color: AppColors.warning, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                AppLocalizations.of(context).voiceDemoBanner,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.4,
                  fontWeight: FontWeight.w600,
                  color: AppColors.warning,
                ),
              ),
            ),
          ],
        ),
      );

  Widget _sampleChips(List<String> phrases) {
    final t = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          t.voiceSampleLabel,
          style: const TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
              color: AppColors.textSecondary),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final phrase in phrases)
              ActionChip(
                label: Text(phrase, style: const TextStyle(fontSize: 12.5)),
                backgroundColor: AppColors.paleGreen,
                side: BorderSide(color: AppColors.primary.withValues(alpha: 0.3)),
                onPressed: () {
                  _phraseController.text = phrase;
                  _submitPhrase();
                },
              ),
          ],
        ),
      ],
    );
  }

  Widget _transcriptCard(BuildContext context, VoiceDraft draft) {
    final t = AppLocalizations.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.paleGreen,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.hearing_rounded,
                  size: 18, color: AppColors.deep),
              const SizedBox(width: 6),
              Text(
                t.voiceHeardYouSay,
                style: const TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w800,
                    color: AppColors.deep),
              ),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  draft.providerLabel(),
                  style: const TextStyle(
                      fontSize: 11, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            draft.transcript.isEmpty ? '—' : draft.transcript,
            style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: AppColors.deep),
          ),
        ],
      ),
    );
  }

  InputDecoration _confirmDecoration(
    String label, {
    bool needsCheck = false,
    String? helper,
  }) {
    final t = AppLocalizations.of(context);
    return InputDecoration(
      labelText: needsCheck ? '$label · ${t.voiceNeedsCheck}' : label,
      helperText: helper,
      border: needsCheck
          ? OutlineInputBorder(
              borderSide: const BorderSide(
                  color: AppColors.harvest, width: 1.6),
              borderRadius: BorderRadius.circular(12),
            )
          : null,
      enabledBorder: needsCheck
          ? OutlineInputBorder(
              borderSide: const BorderSide(
                  color: AppColors.harvest, width: 1.6),
              borderRadius: BorderRadius.circular(12),
            )
          : null,
      suffixIcon: needsCheck
          ? const Icon(Icons.error_outline_rounded,
              size: 18, color: AppColors.harvest)
          : null,
    );
  }

  Widget _confirmationForm(BuildContext context) {
    final t = AppLocalizations.of(context);
    final draft = _draft!;
    final commoditiesAsync = ref.watch(commoditiesProvider);

    return Form(
      key: _formKey,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              t.voiceConfirmTitle,
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              t.voiceConfirmNote,
              style: const TextStyle(
                  fontSize: 12.5, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 16),
            commoditiesAsync.when(
              loading: () => const SkeletonBox(height: 56, radius: 12),
              error: (e, _) => ErrorView(
                message: '${t.commodityLoadFailed}: $e',
                onRetry: () => ref.invalidate(commoditiesProvider),
                compact: true,
              ),
              data: (items) {
                if (_commodity != null && !items.contains(_commodity)) {
                  _commodity = null;
                }
                return DropdownButtonHideUnderline(
                  child: DropdownButtonFormField<Commodity>(
                    initialValue: _commodity,
                    items: [
                      for (final c in items)
                        DropdownMenuItem(
                          value: c,
                          child: Text(c.nameEn +
                              (c.nameTe != null ? ' · ${c.nameTe}' : '')),
                        ),
                    ],
                    onChanged: (c) => setState(() => _commodity = c),
                    decoration: _confirmDecoration(
                      t.crop,
                      needsCheck: _commodity == null ||
                          draft.needsConfirmation('commodity'),
                    ),
                    validator: (c) =>
                        c == null ? t.voiceChooseCommodity : null,
                  ),
                );
              },
            ),
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    controller: _quantityController,
                    keyboardType: const TextInputType.numberWithOptions(
                        decimal: true),
                    decoration: _confirmDecoration(
                      t.quantity,
                      needsCheck: draft.needsConfirmation('quantity'),
                    ),
                    validator: (v) {
                      final n = double.tryParse(v?.trim() ?? '');
                      if (n == null || n <= 0) return t.enterQuantity;
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: DropdownButtonHideUnderline(
                    child: DropdownButtonFormField<String>(
                      initialValue: _unit,
                      items: [
                        for (final u in _units)
                          DropdownMenuItem(value: u, child: Text(u)),
                      ],
                      onChanged: (u) =>
                          setState(() => _unit = u ?? 'kg'),
                      decoration: _confirmDecoration(
                        t.unitLabel,
                        needsCheck: draft.needsConfirmation('unit'),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _priceController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: _confirmDecoration(
                '${t.pricePer} $_unit (₹)',
                needsCheck: draft.needsConfirmation('price') ||
                    draft.needsConfirmation('price_paise'),
              ),
              validator: (v) {
                final n = double.tryParse(v?.trim() ?? '');
                if (n == null || n <= 0) return t.enterPrice;
                return null;
              },
            ),
            const SizedBox(height: 14),
            InkWell(
              onTap: _pickAvailableFrom,
              borderRadius: BorderRadius.circular(12),
              child: InputDecorator(
                decoration: _confirmDecoration(
                  t.voiceAvailableFrom,
                  needsCheck: draft.needsConfirmation('available_from'),
                ),
                child: Text(
                  _availableFrom == null
                      ? t.today
                      : '${_availableFrom!.day}/${_availableFrom!.month}/${_availableFrom!.year}',
                ),
              ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _publishing ? null : _publish,
              icon: _publishing
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.2, color: Colors.white),
                    )
                  : const Icon(Icons.publish_rounded, size: 20),
              label: Text(t.publish),
            ),
          ],
        ),
      ),
    );
  }
}

String _trimNum(double v) =>
    v == v.roundToDouble() ? v.round().toString() : v.toStringAsFixed(2);
