import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/providers.dart';

/// Cart — GET /cart, PATCH /cart/items/{id}, DELETE /cart/items/{id}.
class CartTab extends ConsumerStatefulWidget {
  const CartTab({super.key});

  @override
  ConsumerState<CartTab> createState() => _CartTabState();
}

class _CartTabState extends ConsumerState<CartTab> {
  String? _busyItemId;

  Future<void> _updateQuantity(String itemId, double current, double delta) async {
    final next = current + delta;
    setState(() => _busyItemId = itemId);
    try {
      if (next <= 0) {
        await ref.read(cartApiProvider).remove(itemId);
      } else {
        await ref.read(cartApiProvider).updateQuantity(itemId, next);
      }
      ref.invalidate(cartProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _busyItemId = null);
    }
  }

  Future<void> _remove(String itemId) async {
    setState(() => _busyItemId = itemId);
    try {
      await ref.read(cartApiProvider).remove(itemId);
      ref.invalidate(cartProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _busyItemId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(cartProvider);

    return TabBody(
      bottomPadding: 32,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 4),
          Text(
            t.navCart,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 18),
          async.when(
            loading: () => const SkeletonList(itemCount: 3, itemHeight: 88),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(cartProvider),
              compact: true,
            ),
            data: (cart) {
              if (cart.isEmpty) {
                return SizedBox(
                  height: 440,
                  child: EmptyState(
                    icon: Icons.shopping_cart_outlined,
                    title: t.cartEmptyTitle,
                    message: t.cartEmptyMessage,
                    actionLabel: t.browseProduce,
                    onAction: () => context.go('/buyer'),
                  ),
                );
              }
              return Column(
                children: [
                  for (final item in cart.items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _CartRow(
                        title: item.title,
                        district: item.farmerDistrict,
                        quantity: item.quantity,
                        unitPrice: formatPaise(item.unitPricePaise),
                        lineTotal: formatPaise(item.lineTotalPaise),
                        listingStatus: item.listingStatus,
                        busy: _busyItemId == item.id,
                        onMinus: () => _updateQuantity(
                            item.id, item.quantity, -_stepFor(item.quantity)),
                        onPlus: () => _updateQuantity(
                            item.id, item.quantity, _stepFor(item.quantity)),
                        onRemove: () => _remove(item.id),
                      ),
                    ),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            t.subtotal,
                            style: const TextStyle(
                                fontSize: 15, fontWeight: FontWeight.w700),
                          ),
                        ),
                        Text(
                          formatPaise(cart.subtotalPaise),
                          style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primary),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    t.feesAtCheckout,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: () => context.push('/checkout'),
                    icon: const Icon(Icons.arrow_forward_rounded, size: 20),
                    label: Text(t.checkout),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  // Step 1 for whole-number quantities, 0.5 for fractional (e.g. 0.5 kg).
  double _stepFor(double quantity) =>
      quantity == quantity.roundToDouble() ? 1 : 0.5;
}

class _CartRow extends StatelessWidget {
  const _CartRow({
    required this.title,
    required this.district,
    required this.quantity,
    required this.unitPrice,
    required this.lineTotal,
    required this.listingStatus,
    required this.busy,
    required this.onMinus,
    required this.onPlus,
    required this.onRemove,
  });

  final String title;
  final String? district;
  final double quantity;
  final String unitPrice;
  final String lineTotal;
  final String? listingStatus;
  final bool busy;
  final VoidCallback onMinus;
  final VoidCallback onPlus;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final unavailable = listingStatus != null && listingStatus != 'active';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: unavailable ? AppColors.harvest : AppColors.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 15.5, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(
                      [
                        ?district,
                        unitPrice,
                      ].join(' · '),
                      style: const TextStyle(
                          fontSize: 12.5, color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              Text(lineTotal,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _RoundIcon(
                  icon: Icons.remove_rounded,
                  onTap: busy || quantity <= 1 ? null : onMinus),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child:
                            CircularProgressIndicator(strokeWidth: 2.2))
                    : Text(
                        quantity == quantity.roundToDouble()
                            ? quantity.round().toString()
                            : quantity.toStringAsFixed(1),
                        style: const TextStyle(
                            fontSize: 15.5, fontWeight: FontWeight.w700),
                      ),
              ),
              _RoundIcon(icon: Icons.add_rounded, onTap: busy ? null : onPlus),
              const Spacer(),
              if (busy)
                IconButton(
                  onPressed: null,
                  icon: _RoundIcon(
                    icon: Icons.delete_outline_rounded,
                    onTap: null,
                    color: AppColors.danger,
                  ),
                )
              else
                IconButton(
                  tooltip: 'Remove',
                  onPressed: onRemove,
                  icon: Icon(Icons.delete_outline_rounded,
                      color: AppColors.danger),
                ),
            ],
          ),
          if (unavailable)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded,
                      size: 15, color: AppColors.harvest),
                  const SizedBox(width: 6),
                  Text(
                    'This listing is no longer live — remove it to continue.',
                    style: TextStyle(
                        fontSize: 12, color: AppColors.harvest),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _RoundIcon extends StatelessWidget {
  const _RoundIcon({
    required this.icon,
    required this.onTap,
    this.color,
  });

  final IconData icon;
  final VoidCallback? onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 48,
      height: 48,
      child: IconButton(
        onPressed: onTap,
        icon: Icon(icon, color: color ?? AppColors.primary, size: 20),
      ),
    );
  }
}
