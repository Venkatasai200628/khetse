import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/listing_model.dart';
import '../../marketplace/data/providers.dart';

/// Admin overview. The backend has no dedicated admin analytics endpoint
/// yet, so this computes counts from the real GET /listings page (max 100
/// rows) and labels the sampling honestly — no invented platform totals.
class AdminOverviewTab extends ConsumerWidget {
  const AdminOverviewTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(adminMarketplaceProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 4),
          Text(
            t.adminOverviewTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.adminOverviewSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          async.when(
            loading: () => const SkeletonDashboard(),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(adminMarketplaceProvider),
              compact: true,
            ),
            data: (page) {
              final live =
                  page.items.where((l) => l.status == 'active').length;
              final districts =
                  page.items.map((l) => l.farmerDistrict).whereType<String>().toSet();
              final commodities =
                  page.items.map((l) => l.commodityName).whereType<String>().toSet();
              final avgPaisePerUnit = page.items.isEmpty
                  ? 0
                  : (page.items
                          .map((l) => l.listedPricePaise)
                          .reduce((a, b) => a + b) ~/
                      page.items.length);

              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: StatTile(
                          label: t.adminTotalListings,
                          value: '${page.total}',
                          icon: Icons.sell_rounded,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: StatTile(
                          label: t.adminLiveListings,
                          value: '$live',
                          icon: Icons.check_circle_rounded,
                          accent: AppColors.fresh,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: StatTile(
                          label: t.adminDistricts,
                          value: '${districts.length}',
                          icon: Icons.location_on_rounded,
                          accent: AppColors.harvest,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: StatTile(
                          label: t.adminCommodities,
                          value: '${commodities.length}',
                          icon: Icons.grain_rounded,
                          accent: const Color(0xFF1D4ED8),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${t.adminAvgListed}: ${formatPaise(avgPaisePerUnit)}',
                          style: const TextStyle(
                              fontSize: 14.5, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          t.adminSampleNote,
                          style: const TextStyle(
                              fontSize: 12.5,
                              color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (page.items.isNotEmpty) ...[
                    SectionHeader(t.adminTopCommodities),
                    const SizedBox(height: 10),
                    for (final entry in _topCommodities(page))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _CommodityRow(
                          name: entry.$1,
                          count: entry.$2,
                          liveCount: entry.$3,
                        ),
                      ),
                  ],
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  /// (commodity, listing count, live count) sorted by count desc.
  List<(String, int, int)> _topCommodities(ListingPage page) {
    final counts = <String, (int, int)>{};
    for (final l in page.items) {
      final name = l.commodityName;
      if (name == null) continue;
      final prev = counts[name] ?? (0, 0);
      counts[name] = (prev.$1 + 1, prev.$2 + (l.status == 'active' ? 1 : 0));
    }
    final entries = counts.entries.toList()
      ..sort((a, b) => b.value.$1.compareTo(a.value.$1));
    return [
      for (final e in entries.take(6)) (e.key, e.value.$1, e.value.$2),
    ];
  }
}

class _CommodityRow extends StatelessWidget {
  const _CommodityRow({
    required this.name,
    required this.count,
    required this.liveCount,
  });

  final String name;
  final int count;
  final int liveCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(name,
                style: const TextStyle(
                    fontSize: 14.5, fontWeight: FontWeight.w600)),
          ),
          Text(
            '$liveCount/$count live',
            style: const TextStyle(
                fontSize: 13, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
