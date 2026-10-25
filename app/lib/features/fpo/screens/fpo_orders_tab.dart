import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/providers.dart';
import '../../marketplace/widgets/order_card.dart';

/// FPO orders — GET /orders/farmer with the FPO operator's involvement
/// rule: the backend also returns orders containing member farmers' items.
class FpoOrdersTab extends ConsumerWidget {
  const FpoOrdersTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(farmerOrdersProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 4),
          Text(
            t.fpoOrdersTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.fpoOrdersSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          async.when(
            loading: () => const SkeletonList(itemCount: 4, itemHeight: 100),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(farmerOrdersProvider),
              compact: true,
            ),
            data: (page) {
              if (page.items.isEmpty) {
                return SizedBox(
                  height: 420,
                  child: EmptyState(
                    icon: Icons.warehouse_rounded,
                    title: t.noOrdersTitle,
                    message: t.fpoNoOrders,
                  ),
                );
              }
              return Column(
                children: [
                  StatTile(
                    label: t.fpoOrderCount,
                    value: '${page.total}',
                    icon: Icons.inventory_rounded,
                  ),
                  const SizedBox(height: 14),
                  for (final order in page.items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: OrderCard(order: order, showFarmerResponse: true),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
