import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../../l10n/app_localizations.dart';
import '../../marketplace/data/listing_model.dart';
import '../../marketplace/data/providers.dart';
import '../data/market_model.dart';
import '../data/providers.dart';

/// Market prices — GET /market-prices/recommendation. Shared by the farmer
/// and buyer bottom navs (and the /market route). The recommendation card
/// shows exactly what the API returned: range, benchmark, confidence,
/// explanation and full model provenance. A 404 is presented honestly as
/// "no data for this selection yet", never as a crash.
class MarketScreen extends ConsumerStatefulWidget {
  const MarketScreen({super.key});

  @override
  ConsumerState<MarketScreen> createState() => _MarketScreenState();
}

class _MarketScreenState extends ConsumerState<MarketScreen> {
  Commodity? _commodity;
  final _districtController = TextEditingController();
  PriceRecommendation? _data;
  Object? _error;
  bool _loading = false;

  @override
  void dispose() {
    _districtController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final commodity = _commodity;
    if (commodity == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rec = await ref.read(marketApiProvider).recommendation(
            commodityId: commodity.id,
            district: _districtController.text,
          );
      if (mounted) {
        setState(() {
          _data = rec;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final commoditiesAsync = ref.watch(commoditiesProvider);

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            t.marketTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.marketSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          _selectorCard(context, commoditiesAsync),
          const SizedBox(height: 18),
          _resultSection(context),
        ],
      ),
    );
  }

  Widget _selectorCard(
    BuildContext context,
    AsyncValue<List<Commodity>> commoditiesAsync,
  ) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          commoditiesAsync.when(
            loading: () => const SkeletonBox(height: 56, radius: 12),
            error: (e, _) => ErrorView(
              message: '${t.commodityLoadFailed}: $e',
              onRetry: () => ref.invalidate(commoditiesProvider),
              compact: true,
            ),
            data: (items) {
              _commodity ??= items.isNotEmpty ? items.first : null;
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
                  decoration: InputDecoration(labelText: t.marketCommodity),
                ),
              );
            },
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _districtController,
            textCapitalization: TextCapitalization.words,
            decoration: InputDecoration(
              labelText: t.marketDistrict,
              hintText: t.marketDistrictHint,
            ),
            onSubmitted: (_) => _load(),
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.query_stats_rounded, size: 20),
            label: Text(t.marketGetPrice),
          ),
        ],
      ),
    );
  }

  Widget _resultSection(BuildContext context) {
    final t = AppLocalizations.of(context);

    // First load in flight.
    if (_loading && _data == null && _error == null) {
      return const Padding(
        padding: EdgeInsets.only(top: 8),
        child: SkeletonList(itemCount: 2, itemHeight: 110),
      );
    }
    // A previous query failed with no data to fall back on.
    if (_error != null && _data == null) {
      final error = _error!;
      // 404 = the model has no data for this selection — say so honestly.
      if (error is ApiException && error.statusCode == 404) {
        return SizedBox(
          height: 380,
          child: EmptyState(
            icon: Icons.search_off_rounded,
            title: t.marketNoDataTitle,
            message: t.marketNoDataMessage,
            actionLabel: t.retryLabel,
            onAction: _load,
          ),
        );
      }
      return ErrorView(message: error.toString(), onRetry: _load);
    }
    // Nothing queried yet.
    if (_data == null) {
      return SizedBox(
        height: 320,
        child: EmptyState(
          icon: Icons.query_stats_rounded,
          title: t.marketPickCommodity,
          message: t.marketPickCommodityMessage,
        ),
      );
    }
    return RecommendationCard(
      rec: _data!,
      refreshing: _loading,
    );
  }
}

class RecommendationCard extends StatelessWidget {
  const RecommendationCard({super.key, required this.rec, this.refreshing = false});

  final PriceRecommendation rec;
  final bool refreshing;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final unit = rec.unit ?? 'kg';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  rec.commodityName,
                  style: const TextStyle(
                      fontSize: 17, fontWeight: FontWeight.w800),
                ),
              ),
              StatusChip(
                  label: rec.confidence, tone: _confidenceTone(rec.confidence)),
            ],
          ),
          if (rec.district != null && rec.district!.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              rec.district!,
              style: const TextStyle(
                  fontSize: 12.5, color: AppColors.textSecondary),
            ),
          ],
          const SizedBox(height: 12),
          Text(
            t.marketRangeLabel(unit),
            style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: AppColors.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            '₹${rec.rangeLabel}',
            style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
          ),
          Text(
            rec.isQuintal ? t.marketPerQuintal : t.marketPerUnit(unit),
            style:
                const TextStyle(fontSize: 12, color: AppColors.textSecondary),
          ),
          if (rec.isQuintal && rec.recommendedModalPerKgPaise != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '${t.marketPerKgPrefix} ${formatPaise(rec.recommendedModalPerKgPaise!)}/kg',
                style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primary),
              ),
            ),
          if (refreshing)
            const Padding(
              padding: EdgeInsets.only(top: 10),
              child: LinearProgressIndicator(minHeight: 2),
            ),
          const Divider(height: 24),
          _factRow(t.marketBenchmark, rec.benchmarkMarket),
          if (rec.benchmarkObservedOn != null)
            _factRow(
                t.marketObserved,
                '${rec.benchmarkObservedOn!.day}/${rec.benchmarkObservedOn!.month}/'
                '${rec.benchmarkObservedOn!.year}'),
          _factRow(t.marketSource, rec.benchmarkSource),
          if (rec.explanation != null && rec.explanation!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.paleGreen,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    t.marketWhyThisRange,
                    style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        color: AppColors.deep),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    rec.explanation!,
                    style: const TextStyle(
                        fontSize: 13, height: 1.4, color: AppColors.deep),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.memory_rounded,
                  size: 14, color: AppColors.textSecondary),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  rec.provenanceLabel,
                  style: const TextStyle(
                      fontSize: 11.5, color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _factRow(String label, String? value) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 128,
            child: Text(
              label,
              style:
                  const TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style:
                  const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

StatusTone _confidenceTone(String confidence) {
  switch (confidence.toLowerCase()) {
    case 'high':
      return StatusTone.success;
    case 'low':
      return StatusTone.danger;
    default:
      return StatusTone.warning;
  }
}
