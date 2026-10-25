import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../marketplace/data/providers.dart';
import '../../marketplace/widgets/listing_card.dart';

/// Listing detail + add-to-cart (POST /cart/items).
class ListingDetailScreen extends ConsumerStatefulWidget {
  const ListingDetailScreen({super.key, required this.listingId});

  final String listingId;

  @override
  ConsumerState<ListingDetailScreen> createState() =>
      _ListingDetailScreenState();
}

class _ListingDetailScreenState extends ConsumerState<ListingDetailScreen> {
  final _quantityController = TextEditingController(text: '1');
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  Future<void> _addToCart(double maxQuantity, String unit) async {
    final quantity = double.tryParse(_quantityController.text.trim());
    if (quantity == null || quantity <= 0) {
      setState(() => _error = 'Enter a quantity greater than zero.');
      return;
    }
    if (quantity > maxQuantity) {
      setState(() => _error = 'Only $maxQuantity $unit available.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(cartApiProvider)
          .add(widget.listingId, quantity);
      ref.invalidate(cartProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context).addedToCart)));
        context.pop();
      }
    } catch (e) {
      setState(() {
        _busy = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    // Detail route fetches its own row via the single-listing endpoint.
    final detail = ref.watch(listingDetailProvider(widget.listingId));

    return Scaffold(
      appBar: AppBar(title: Text(t.listingDetail)),
      body: SafeArea(
        child: detail.when(
          loading: () =>
              const SingleChildScrollView(
                  padding: EdgeInsets.all(20),
                  child: SkeletonList(itemCount: 4, itemHeight: 84)),
          error: (e, _) => ErrorView(
            message: e.toString(),
            onRetry: () =>
                ref.invalidate(listingDetailProvider(widget.listingId)),
          ),
          data: (listing) {
            final available = listing.quantityAvailable;
            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    height: 170,
                    decoration: BoxDecoration(
                      color: AppColors.paleGreen,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Icon(
                      ListingCard.categoryIcon(listing.commodityCategory),
                      size: 64,
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          listing.title,
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      StatusChip.forListingStatus(listing.status),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${listing.originLabel}'
                    '${listing.commodityCategory != null ? ' · ${listing.commodityCategory}' : ''}',
                    style: const TextStyle(
                        fontSize: 13.5, color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Text(
                        formatPaise(listing.listedPricePaise),
                        style: const TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w800,
                          color: AppColors.primary,
                        ),
                      ),
                      Text(
                        '/${listing.unit}',
                        style: const TextStyle(
                            fontSize: 15, color: AppColors.textSecondary),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _InfoTile(
                    icon: Icons.inventory_2_outlined,
                    label: '${t.available}: ${listing.availableLabel}',
                  ),
                  const SizedBox(height: 8),
                  if (listing.qualityGrade != 'ungraded')
                    _InfoTile(
                      icon: Icons.workspace_premium_outlined,
                      label: '${t.grade}: ${listing.qualityGrade}',
                    ),
                  if (listing.harvestedLabel != null) ...[
                    const SizedBox(height: 8),
                    _InfoTile(
                      icon: Icons.agriculture_rounded,
                      label: '${t.harvested}: ${listing.harvestedLabel}',
                    ),
                  ],
                  if (listing.isSynthetic) ...[
                    const SizedBox(height: 8),
                    _InfoTile(
                      icon: Icons.science_outlined,
                      label: t.demoDataLabel,
                      accent: AppColors.harvest,
                    ),
                  ],
                  if (listing.description != null &&
                      listing.description!.isNotEmpty) ...[
                    const SizedBox(height: 18),
                    Text(listing.description!,
                        style: const TextStyle(
                            fontSize: 14.5, height: 1.45)),
                  ],
                  const SizedBox(height: 24),
                  if (listing.status == 'active' && available > 0) ...[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _quantityController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: InputDecoration(
                              labelText: '${t.quantity} (${listing.unit})',
                              errorText: _error,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          flex: 2,
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(
                                minimumSize: const Size.fromHeight(56)),
                            onPressed: _busy
                                ? null
                                : () => _addToCart(available, listing.unit),
                            icon: _busy
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2.2, color: Colors.white))
                                : const Icon(Icons.add_shopping_cart_rounded,
                                    size: 20),
                            label: Text(t.addToCart),
                          ),
                        ),
                      ],
                    ),
                  ] else ...[
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.cream,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Text(
                        listing.status == 'active'
                            ? t.soldOut
                            : t.listingNotAvailable,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textSecondary),
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.icon,
    required this.label,
    this.accent,
  });

  final IconData icon;
  final String label;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final color = accent ?? AppColors.textSecondary;
    return Row(
      children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 8),
        Text(label,
            style: TextStyle(
                fontSize: 13.5, color: color, fontWeight: FontWeight.w600)),
      ],
    );
  }
}
