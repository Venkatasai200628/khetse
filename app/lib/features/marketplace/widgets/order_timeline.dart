import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../data/order_model.dart';

/// Vertical status timeline built from `status_events` — every transition
/// with actor and timestamp, exactly as recorded by the backend.
class OrderTimeline extends StatelessWidget {
  const OrderTimeline({super.key, required this.events});

  final List<OrderStatusEvent> events;

  static const _labels = {
    'CREATED': 'Order created',
    'AWAITING_FARMER_CONFIRMATION': 'Sent to farmer',
    'ACCEPTED': 'Farmer accepted',
    'PAYMENT_PENDING': 'Awaiting payment',
    'CONFIRMED': 'Payment confirmed',
    'PICKUP_SCHEDULED': 'Pickup scheduled',
    'PICKED_UP': 'Picked up',
    'OUT_FOR_DELIVERY': 'Out for delivery',
    'DELIVERED': 'Delivered',
    'COMPLETED': 'Completed',
    'REJECTED': 'Rejected by farmer',
    'CANCELLED': 'Cancelled',
    'PAYMENT_FAILED': 'Payment failed',
    'REFUND_PENDING': 'Refund pending',
    'REFUNDED': 'Refunded',
    'DELIVERY_FAILED': 'Delivery failed',
    'DISPUTED': 'Disputed',
  };

  static const _badStatuses = {
    'REJECTED',
    'CANCELLED',
    'PAYMENT_FAILED',
    'DELIVERY_FAILED',
    'DISPUTED',
  };

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return const SizedBox.shrink();
    }
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
          Text(
            'Timeline',
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 14),
          for (var i = 0; i < events.length; i++)
            _TimelineRow(
              event: events[i],
              isFirst: i == 0,
              isLast: i == events.length - 1,
            ),
        ],
      ),
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.event,
    required this.isFirst,
    required this.isLast,
  });

  final OrderStatusEvent event;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final bad = OrderTimeline._badStatuses.contains(event.toStatus);
    final dotColor = bad ? AppColors.danger : AppColors.primary;
    final label =
        OrderTimeline._labels[event.toStatus] ?? event.toStatus.replaceAll('_', ' ');

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 26,
            child: Column(
              children: [
                if (!isFirst)
                  Expanded(
                      child: Container(width: 2, color: AppColors.border)),
                Container(
                  width: 12,
                  height: 12,
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isFirst ? dotColor : Colors.white,
                    border: Border.all(color: dotColor, width: 2.4),
                  ),
                ),
                if (!isLast)
                  Expanded(
                      child: Container(width: 2, color: AppColors.border)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          label,
                          style: TextStyle(
                            fontSize: 14.5,
                            fontWeight:
                                isFirst ? FontWeight.w800 : FontWeight.w600,
                            color: isFirst
                                ? AppColors.textPrimary
                                : AppColors.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    event.whenLabel +
                        (event.actorRole != null && event.actorRole!.isNotEmpty
                            ? ' · by ${event.actorRole}'
                            : ''),
                    style: const TextStyle(
                        fontSize: 12.5, color: AppColors.textSecondary),
                  ),
                  if (event.reason != null && event.reason!.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      event.reason!,
                      style: const TextStyle(
                          fontSize: 12.5,
                          color: AppColors.textSecondary,
                          fontStyle: FontStyle.italic),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
