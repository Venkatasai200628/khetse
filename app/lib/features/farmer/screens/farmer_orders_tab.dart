import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/providers.dart';
import '../../marketplace/widgets/order_card.dart';

/// Farmer orders — GET /orders/farmer, newest first. Accept/reject happens
/// on the order detail screen.
class FarmerOrdersTab extends ConsumerWidget {
  const FarmerOrdersTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(farmerOrdersProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            t.incomingOrders,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.incomingOrdersSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: const Color(0xFF647067)),
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
                    icon: Icons.receipt_long_rounded,
                    title: t.noOrdersTitle,
                    message: t.farmerNoOrders,
                  ),
                );
              }
              return Column(
                children: [
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
