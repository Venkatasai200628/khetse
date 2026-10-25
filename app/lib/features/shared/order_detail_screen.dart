import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../auth/controllers/auth_controller.dart';
import '../marketplace/data/order_model.dart';
import '../marketplace/data/providers.dart';
import '../marketplace/widgets/order_timeline.dart';

/// Order detail with the full status timeline, money breakdown and the
/// actions the signed-in role may perform (farmer accept/reject,
/// buyer cancel). All server-side rules apply — the UI only offers what
/// the current state allows.
class OrderDetailScreen extends ConsumerStatefulWidget {
  const OrderDetailScreen({super.key, required this.orderId});

  final String orderId;

  @override
  ConsumerState<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends ConsumerState<OrderDetailScreen> {
  bool _acting = false;

  Future<void> _farmerRespond(bool accept) async {
    setState(() => _acting = true);
    try {
      await ref.read(orderApiProvider).farmerResponse(widget.orderId, accept: accept);
      ref.invalidate(orderDetailProvider(widget.orderId));
      ref.invalidate(farmerOrdersProvider);
      ref.invalidate(buyerOrdersProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(accept ? 'Order accepted' : 'Order rejected')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _cancel() async {
    setState(() => _acting = true);
    try {
      await ref.read(orderApiProvider).cancel(widget.orderId);
      ref.invalidate(orderDetailProvider(widget.orderId));
      ref.invalidate(buyerOrdersProvider);
      ref.invalidate(farmerOrdersProvider);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Order cancelled')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(orderDetailProvider(widget.orderId));
    final user = ref.watch(currentUserProvider);
    final isFarmer = user?.roles.contains('farmer') ?? false;
    final isBuyer = user != null &&
        (user.roles.contains('buyer') || user.roles.contains('business'));

    return Scaffold(
      appBar: AppBar(title: const Text('Order')),
      body: SafeArea(
        child: switch (async) {
          AsyncLoading() => const SingleChildScrollView(
              padding: EdgeInsets.all(20), child: SkeletonList(itemCount: 5)),
          AsyncError(:final error) => ErrorView(
              message: error.toString(),
              onRetry: () => ref.invalidate(orderDetailProvider(widget.orderId)),
            ),
          AsyncData(:final value) => _Body(
              order: value,
              isFarmer: isFarmer,
              isBuyer: isBuyer,
              acting: _acting,
              onAccept: () => _farmerRespond(true),
              onReject: () => _farmerRespond(false),
              onCancel: _cancel,
            ),
          _ => ErrorView(
              message: 'Order could not be loaded.',
              onRetry: () => ref.invalidate(orderDetailProvider(widget.orderId)),
            ),
        },
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.order,
    required this.isFarmer,
    required this.isBuyer,
    required this.acting,
    required this.onAccept,
    required this.onReject,
    required this.onCancel,
  });

  final Order order;
  final bool isFarmer;
  final bool isBuyer;
  final bool acting;
  final VoidCallback onAccept;
  final VoidCallback onReject;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    // Backend enum values are lowercase — compare case-insensitively.
    final farmerPending = isFarmer &&
        order.status.toUpperCase() == 'AWAITING_FARMER_CONFIRMATION';
    final buyerCanPay =
        isBuyer && order.status.toUpperCase() == 'PAYMENT_PENDING';

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _headerCard(context),
          const SizedBox(height: 16),
          _itemsCard(context),
          const SizedBox(height: 16),
          _moneyCard(context),
          const SizedBox(height: 16),
          OrderTimeline(events: order.statusEvents),
          if (order.cancelReason != null) ...[
            const SizedBox(height: 16),
            _noteCard(
              context,
              icon: Icons.cancel_outlined,
              color: AppColors.danger,
              title: 'Cancelled',
              body: order.cancelReason!,
            ),
          ],
          if (order.isSynthetic) ...[
            const SizedBox(height: 16),
            _noteCard(
              context,
              icon: Icons.science_outlined,
              color: AppColors.harvest,
              title: 'Demo data',
              body:
                  'This record is labelled synthetic demo data by the backend — it is not a real transaction.',
            ),
          ],
          if (farmerPending) ...[
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.danger,
                      side: const BorderSide(color: AppColors.danger),
                    ),
                    onPressed: acting ? null : onReject,
                    child: const Text('Reject'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: acting ? null : onAccept,
                    icon: const Icon(Icons.check_rounded, size: 20),
                    label: const Text('Accept'),
                  ),
                ),
              ],
            ),
          ],
          if (buyerCanPay) ...[
            const SizedBox(height: 24),
            FilledButton.icon(
              // Sandbox flow: open the payment screen, which drives the
              // two-step initiate → confirm (simulated provider webhook).
              onPressed:
                  acting ? null : () => context.push('/order/${order.id}/pay'),
              icon: const Icon(Icons.payments_rounded, size: 20),
              label: Text('Pay ${formatPaise(order.totalPaise)} (sandbox)'),
            ),
          ],
          if (isBuyer && order.canBuyerCancel) ...[
            const SizedBox(height: 24),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.danger,
                side: const BorderSide(color: AppColors.danger),
              ),
              onPressed: acting ? null : onCancel,
              icon: const Icon(Icons.close_rounded, size: 20),
              label: const Text('Cancel order'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _headerCard(BuildContext context) {
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
                  'Order ${order.id.substring(0, 8)}',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              StatusChip.forOrderStatus(order.status),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.local_shipping_outlined,
                  size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                order.fulfilment == 'PICKUP' ? 'Farm pickup' : 'Home delivery',
                style: const TextStyle(
                    fontSize: 13, color: AppColors.textSecondary),
              ),
            ],
          ),
          if (order.deliveryAddress != null) ...[
            const SizedBox(height: 4),
            Text(
              [
                order.deliveryName,
                order.deliveryAddress,
                order.deliveryDistrict,
              ].whereType<String>().join(', '),
              style:
                  const TextStyle(fontSize: 13, color: AppColors.textSecondary),
            ),
          ],
        ],
      ),
    );
  }

  Widget _itemsCard(BuildContext context) {
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
          Text('Items',
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          for (final item in order.items)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${item.commodityName ?? 'Item'} · ${item.quantityLabel}',
                          style: const TextStyle(
                              fontSize: 14.5, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${formatPaise(item.unitPricePaise)}/${item.unit ?? 'unit'}'
                          '${item.qualityGrade != null && item.qualityGrade != 'ungraded' ? ' · Grade ${item.qualityGrade}' : ''}',
                          style: const TextStyle(
                              fontSize: 12.5, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  StatusChip.forFarmerResponse(item.farmerResponse),
                  const SizedBox(width: 10),
                  Text(
                    formatPaise(item.lineTotalPaise),
                    style: const TextStyle(
                        fontSize: 14.5, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _moneyCard(BuildContext context) {
    Widget row(String label, int paise, {bool strong = false}) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 14,
                    color: strong ? AppColors.textPrimary : AppColors.textSecondary,
                    fontWeight: strong ? FontWeight.w800 : FontWeight.w500,
                  ),
                ),
              ),
              Text(
                formatPaise(paise),
                style: TextStyle(
                  fontSize: strong ? 17 : 14,
                  fontWeight: strong ? FontWeight.w800 : FontWeight.w600,
                ),
              ),
            ],
          ),
        );

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
          Text('Payment',
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          row('Subtotal', order.subtotalPaise),
          row('Delivery fee', order.deliveryFeePaise),
          row('Platform fee', order.platformFeePaise),
          const Divider(height: 18),
          row('Total', order.totalPaise, strong: true),
          const SizedBox(height: 6),
          Row(
            children: [
              Text(
                'Payment status:',
                style: TextStyle(
                    fontSize: 13, color: AppColors.textSecondary),
              ),
              const SizedBox(width: 8),
              StatusChip.forPaymentStatus(order.paymentStatus),
            ],
          ),
        ],
      ),
    );
  }

  Widget _noteCard(
    BuildContext context, {
    required IconData icon,
    required Color color,
    required String title,
    required String body,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: TextStyle(
                        fontWeight: FontWeight.w700, color: color)),
                const SizedBox(height: 2),
                Text(body,
                    style: const TextStyle(
                        fontSize: 13, color: AppColors.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
