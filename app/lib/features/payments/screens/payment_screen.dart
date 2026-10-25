import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../marketplace/data/providers.dart';
import '../data/payment_api.dart';

final paymentApiProvider =
    Provider<PaymentApi>((ref) => PaymentApi(ref.watch(apiClientProvider)));

/// Payment view for one order — GET /payments/orders/{id}
/// (owner or admin only; everyone else gets a 403 from the backend).
final orderPaymentProvider =
    FutureProvider.autoDispose.family<OrderPayment, String>((ref, orderId) {
  return ref.watch(paymentApiProvider).forOrder(orderId);
});

/// Sandbox payment for one order: shows the exact paise breakdown under a
/// SANDBOX banner, then drives the two-step flow — Initiate opens the mock
/// transaction, Confirm is the simulated provider webhook. The order only
/// becomes CONFIRMED after the backend's confirm call; nothing happens
/// "because a button was clicked" client-side.
class PaymentScreen extends ConsumerStatefulWidget {
  const PaymentScreen({super.key, required this.orderId});

  final String orderId;

  @override
  ConsumerState<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends ConsumerState<PaymentScreen> {
  PaymentTransaction? _openTransaction;
  bool _acting = false;

  Future<void> _initiate() async {
    setState(() => _acting = true);
    try {
      final txn =
          await ref.read(paymentApiProvider).initiate(widget.orderId);
      setState(() => _openTransaction = txn);
    } catch (e) {
      if (mounted) {
        // "Not awaiting payment" usually means it was paid meanwhile — reload.
        ref.invalidate(orderPaymentProvider(widget.orderId));
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _confirm() async {
    final txn = _openTransaction;
    if (txn == null) return;
    setState(() => _acting = true);
    try {
      final result = await ref.read(paymentApiProvider).confirm(txn.id);
      ref.invalidate(orderPaymentProvider(widget.orderId));
      ref.invalidate(orderDetailProvider(widget.orderId));
      ref.invalidate(buyerOrdersProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result.alreadyConfirmed
                  ? 'Payment was already confirmed'
                  : 'Payment confirmed — order confirmed',
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ref.invalidate(orderPaymentProvider(widget.orderId));
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(orderPaymentProvider(widget.orderId));

    return Scaffold(
      appBar: AppBar(title: const Text('Payment')),
      body: SafeArea(
        child: switch (async) {
          AsyncLoading() => const SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: SkeletonList(itemCount: 4),
            ),
          AsyncError(:final error) => ErrorView(
              message: error.toString(),
              onRetry: () =>
                  ref.invalidate(orderPaymentProvider(widget.orderId)),
            ),
          AsyncData(:final value) => _Body(
              payment: value,
              openTransaction: _openTransaction,
              acting: _acting,
              onInitiate: _initiate,
              onConfirm: _confirm,
            ),
          _ => ErrorView(
              message: 'Payment could not be loaded.',
              onRetry: () =>
                  ref.invalidate(orderPaymentProvider(widget.orderId)),
            ),
        },
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.payment,
    required this.openTransaction,
    required this.acting,
    required this.onInitiate,
    required this.onConfirm,
  });

  final OrderPayment payment;
  final PaymentTransaction? openTransaction;
  final bool acting;
  final VoidCallback onInitiate;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _sandboxBanner(),
          const SizedBox(height: 16),
          if (payment.isPaid) ...[
            _successCard(context),
            const SizedBox(height: 16),
          ],
          _breakdownCard(context),
          if (payment.ledgerEntries.isNotEmpty) ...[
            const SizedBox(height: 16),
            _ledgerCard(context),
          ],
          if (!payment.isPaid) ...[
            const SizedBox(height: 24),
            _actionArea(context),
          ],
        ],
      ),
    );
  }

  Widget _sandboxBanner() => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.warning.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.warning.withValues(alpha: 0.4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.science_outlined, color: AppColors.warning, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'SANDBOX — no real money moves',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      color: AppColors.warning,
                    ),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'Mock provider, clearly labelled end-to-end. '
                    'Every transaction is flagged is_sandbox.',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _successCard(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.paleGreen,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.success.withValues(alpha: 0.4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle_rounded,
                color: AppColors.success, size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Paid ${formatPaise(payment.totalPaise)}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      color: AppColors.success,
                      fontSize: 16,
                    ),
                  ),
                  const Text(
                    'Payment already confirmed for this order.',
                    style: TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            StatusChip.forPaymentStatus(payment.paymentStatus),
          ],
        ),
      );

  Widget _breakdownCard(BuildContext context) {
    Widget row(String label, int paise, {bool strong = false}) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 14,
                    color:
                        strong ? AppColors.textPrimary : AppColors.textSecondary,
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
          Text('Order breakdown',
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          row('Subtotal', payment.subtotalPaise),
          row('Delivery fee', payment.deliveryFeePaise),
          row('Platform fee', payment.platformFeePaise),
          const Divider(height: 18),
          row('Total', payment.totalPaise, strong: true),
          const SizedBox(height: 6),
          Row(
            children: [
              const Text('Payment status:',
                  style: TextStyle(
                      fontSize: 13, color: AppColors.textSecondary)),
              const SizedBox(width: 8),
              StatusChip.forPaymentStatus(payment.paymentStatus),
            ],
          ),
        ],
      ),
    );
  }

  Widget _ledgerCard(BuildContext context) {
    String label(String entryType) => switch (entryType) {
          'payment_in' => 'Payment received',
          'farmer_proceeds' => 'Farmer proceeds',
          'platform_fee' => 'Platform fee',
          'delivery_fee_in' => 'Delivery fee',
          _ => entryType,
        };

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
          Text('Ledger',
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          for (final line in payment.ledgerEntries)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label(line.entryType),
                      style: const TextStyle(
                          fontSize: 14, color: AppColors.textSecondary),
                    ),
                  ),
                  Text(
                    formatPaise(line.amountPaise),
                    style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _actionArea(BuildContext context) {
    final txn = openTransaction;
    final initiated = txn != null && !txn.isSuccessful;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (txn != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(
              'Sandbox transaction opened · '
              '…${txn.id.substring(txn.id.length - 8)} · '
              '${formatPaise(txn.amountPaise)}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  fontSize: 13, color: AppColors.textSecondary),
            ),
          ),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: acting ? null : onInitiate,
                icon: const Icon(Icons.play_arrow_rounded, size: 20),
                label: const Text('Initiate'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                onPressed: (acting || !initiated) ? null : onConfirm,
                icon: const Icon(Icons.verified_rounded, size: 20),
                label: const Text('Confirm'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Initiate opens the mock transaction; Confirm simulates the '
          'provider webhook that settles it.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
      ],
    );
  }
}
