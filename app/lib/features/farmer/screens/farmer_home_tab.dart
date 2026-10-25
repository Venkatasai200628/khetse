import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/empty_state.dart';
import '../../auth/controllers/auth_controller.dart';
import '../../marketplace/data/providers.dart';
import '../../marketplace/widgets/order_card.dart';
import '../../rfq/screens/open_demand_section.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';

/// Farmer dashboard — every number comes from live API responses:
/// listings from GET /listings/mine and orders from GET /orders/farmer.
/// The big "Speak to sell" button opens the voice listing flow and the
/// "Open demand" section quotes real business RFQs.
class FarmerHomeTab extends ConsumerWidget {
  const FarmerHomeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(currentUserProvider);
    final listingsAsync = ref.watch(myListingsProvider);
    final ordersAsync = ref.watch(farmerOrdersProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DashboardHeader(
            greeting: '${t.hello}, ${user?.displayName.split(' ').first ?? ''} 👋',
            subtitle: t.farmerHeaderSubtitle,
          ),
          const SizedBox(height: 20),
          listingsAsync.when(
            loading: () => Row(
              children: const [
                Expanded(child: SkeletonBox(height: 76, radius: 16)),
                SizedBox(width: 12),
                Expanded(child: SkeletonBox(height: 76, radius: 16)),
              ],
            ),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(myListingsProvider),
              compact: true,
            ),
            data: (listings) => Row(
              children: [
                Expanded(
                  child: StatTile(
                    label: t.statLiveListings,
                    value: '${listings.where((l) => l.status == 'active').length}',
                    icon: Icons.sell_rounded,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: StatTile(
                    label: t.statTotalListings,
                    value: '${listings.length}',
                    icon: Icons.list_rounded,
                    accent: AppColors.fresh,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          // Big entry button for the voice listing flow.
          SizedBox(
            height: 56,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.harvest,
                foregroundColor: Colors.white,
                // Inherit the brand font from the theme — an overriding bare
                // TextStyle would drop the Inter family entirely.
                textStyle: Theme.of(context)
                    .textTheme
                    .labelLarge
                    ?.copyWith(fontSize: 16.5, fontWeight: FontWeight.w800),
              ),
              onPressed: () => context.push('/farmer/voice'),
              icon: const Icon(Icons.mic_rounded, size: 26),
              label: Text(t.voiceEntryButton),
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => context.push('/farmer/listing/new'),
            icon: const Icon(Icons.add_rounded, size: 22),
            label: Text(t.createListing),
          ),
          const SizedBox(height: 24),
          SectionHeader(t.recentOrders),
          const SizedBox(height: 12),
          ordersAsync.when(
            loading: () => const SkeletonList(itemCount: 3, itemHeight: 92),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(farmerOrdersProvider),
              compact: true,
            ),
            data: (page) {
              if (page.items.isEmpty) {
                return EmptyState(
                  icon: Icons.receipt_long_rounded,
                  title: t.noOrdersTitle,
                  message: t.farmerNoOrders,
                );
              }
              return Column(
                children: [
                  for (final order in page.items.take(3))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: OrderCard(order: order, showFarmerResponse: true),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          const OpenDemandSection(),
        ],
      ),
    );
  }
}
