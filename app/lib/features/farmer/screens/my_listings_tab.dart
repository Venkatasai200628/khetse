import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../marketplace/data/providers.dart';

/// Farmer's listings with pause / resume / withdraw actions
/// (PATCH /listings/{id}/status).
class MyListingsTab extends ConsumerStatefulWidget {
  const MyListingsTab({super.key});

  @override
  ConsumerState<MyListingsTab> createState() => _MyListingsTabState();
}

class _MyListingsTabState extends ConsumerState<MyListingsTab> {
  String _busyListingId = '';

  Future<void> _setStatus(String id, String status) async {
    setState(() => _busyListingId = id);
    try {
      await ref.read(listingApiProvider).setStatus(id, status);
      ref.invalidate(myListingsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _busyListingId = '');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(myListingsProvider);

    return TabBody(
      bottomPadding: 96,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.myListings,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              FilledButton.tonal(
                style: FilledButton.styleFrom(
                  minimumSize: const Size(48, 48),
                  backgroundColor: AppColors.paleGreen,
                  foregroundColor: AppColors.deep,
                ),
                onPressed: () => context.push('/farmer/listing/new'),
                child: const Icon(Icons.add_rounded),
              ),
            ],
          ),
          const SizedBox(height: 18),
          async.when(
            loading: () => const SkeletonList(itemCount: 4, itemHeight: 96),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(myListingsProvider),
              compact: true,
            ),
            data: (listings) {
              if (listings.isEmpty) {
                return SizedBox(
                  height: 420,
                  child: EmptyState(
                    icon: Icons.sell_rounded,
                    title: t.noListingsTitle,
                    message: t.noListingsMessage,
                    actionLabel: t.createListing,
                    onAction: () => context.push('/farmer/listing/new'),
                  ),
                );
              }
              return Column(
                children: [
                  for (final listing in listings)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _OwnerListingCard(
                        listingId: listing.id,
                        title: listing.title,
                        quantity: listing.availableLabel,
                        price: listing.listedLabel,
                        status: listing.status,
                        isSynthetic: listing.isSynthetic,
                        busy: _busyListingId == listing.id,
                        onSetStatus: (status) => _setStatus(listing.id, status),
                      ),
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

class _OwnerListingCard extends StatelessWidget {
  const _OwnerListingCard({
    required this.listingId,
    required this.title,
    required this.quantity,
    required this.price,
    required this.status,
    required this.isSynthetic,
    required this.busy,
    required this.onSetStatus,
  });

  final String listingId;
  final String title;
  final String quantity;
  final String price;
  final String status;
  final bool isSynthetic;
  final bool busy;
  final void Function(String status) onSetStatus;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
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
                child: Text(title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w700)),
              ),
              if (isSynthetic)
                const Padding(
                  padding: EdgeInsets.only(right: 6),
                  child: Tooltip(
                    message: 'Demo data',
                    child: Icon(Icons.science_outlined,
                        size: 16, color: AppColors.harvest),
                  ),
                ),
              StatusChip.forListingStatus(status),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(price,
                  style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: AppColors.primary)),
              const SizedBox(width: 10),
              Text(quantity,
                  style: const TextStyle(
                      fontSize: 12.5, color: AppColors.textSecondary)),
            ],
          ),
          if (!busy)
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (status == 'active')
                  TextButton(
                    onPressed: () => onSetStatus('paused'),
                    child: const Text('Pause'),
                  )
                else if (status == 'paused')
                  TextButton(
                    onPressed: () => onSetStatus('active'),
                    child: const Text('Resume'),
                  ),
                if (status != 'withdrawn')
                  TextButton(
                    style: TextButton.styleFrom(foregroundColor: AppColors.danger),
                    onPressed: () => _confirmWithdraw(context),
                    child: const Text('Withdraw'),
                  ),
              ],
            )
          else
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 10),
              child: Align(
                alignment: Alignment.centerRight,
                child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2.2)),
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _confirmWithdraw(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Withdraw listing?'),
        content: const Text(
            'The listing will no longer be visible to buyers. This cannot be undone from the app.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Keep')),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Withdraw')),
        ],
      ),
    );
    if (confirmed == true) onSetStatus('withdrawn');
  }
}
