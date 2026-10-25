import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/status_chip.dart';
import '../data/order_model.dart';

/// Compact order card used in buyer / farmer / FPO order lists.
class OrderCard extends StatelessWidget {
  const OrderCard({super.key, required this.order, this.showFarmerResponse = false});

  final Order order;
  final bool showFarmerResponse;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        onTap: () => context.push('/order/${order.id}'),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      order.itemSummary,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                  ),
                  StatusChip.forOrderStatus(order.status),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    formatPaise(order.totalPaise),
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  StatusChip.forPaymentStatus(order.paymentStatus),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.schedule_rounded,
                      size: 14, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Text(
                    order.placedLabel,
                    style: const TextStyle(
                        fontSize: 12.5, color: AppColors.textSecondary),
                  ),
                  if (showFarmerResponse && order.awaitingFarmer) ...[
                    const Spacer(),
                    StatusChip.forFarmerResponse('PENDING'),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
