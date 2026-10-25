import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Coloured pill for order / listing / payment statuses, mapped from the
/// backend enum values (backend/app/models/enums.py).
class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.label, required this.tone});

  factory StatusChip.forOrderStatus(String status) {
    // Backend serialises enums lowercase ("payment_pending"); match case-insensitively.
    switch (status.toUpperCase()) {
      case 'CREATED':
      case 'AWAITING_FARMER_CONFIRMATION':
      case 'PAYMENT_PENDING':
        return const StatusChip(label: 'Awaiting', tone: StatusTone.warning);
      case 'ACCEPTED':
      case 'CONFIRMED':
      case 'PICKUP_SCHEDULED':
      case 'PICKED_UP':
      case 'OUT_FOR_DELIVERY':
        return const StatusChip(label: 'In progress', tone: StatusTone.info);
      case 'DELIVERED':
      case 'COMPLETED':
        return const StatusChip(label: 'Delivered', tone: StatusTone.success);
      case 'REJECTED':
      case 'CANCELLED':
      case 'PAYMENT_FAILED':
      case 'DELIVERY_FAILED':
        return const StatusChip(label: 'Closed', tone: StatusTone.danger);
      case 'REFUND_PENDING':
      case 'REFUNDED':
      case 'DISPUTED':
        return const StatusChip(label: 'Refund / dispute', tone: StatusTone.warning);
      default:
        return StatusChip(label: status, tone: StatusTone.neutral);
    }
  }

  factory StatusChip.forPaymentStatus(String status) {
    switch (status.toUpperCase()) {
      case 'PAID':
      case 'SETTLED':
        return const StatusChip(label: 'Paid', tone: StatusTone.success);
      case 'PENDING':
        return const StatusChip(label: 'Unpaid', tone: StatusTone.warning);
      case 'FAILED':
        return const StatusChip(label: 'Failed', tone: StatusTone.danger);
      default:
        return StatusChip(label: status, tone: StatusTone.neutral);
    }
  }

  factory StatusChip.forListingStatus(String status) {
    switch (status) {
      case 'active':
        return const StatusChip(label: 'Live', tone: StatusTone.success);
      case 'paused':
        return const StatusChip(label: 'Paused', tone: StatusTone.warning);
      case 'withdrawn':
      case 'sold_out':
        return const StatusChip(label: 'Closed', tone: StatusTone.neutral);
      default:
        return StatusChip(label: status, tone: StatusTone.neutral);
    }
  }

  factory StatusChip.forFarmerResponse(String status) {
    switch (status) {
      case 'accepted':
        return const StatusChip(label: 'Accepted', tone: StatusTone.success);
      case 'rejected':
        return const StatusChip(label: 'Rejected', tone: StatusTone.danger);
      default:
        return const StatusChip(label: 'Pending', tone: StatusTone.warning);
    }
  }

  final String label;
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      StatusTone.success => (AppColors.paleGreen, AppColors.deep),
      StatusTone.warning => (const Color(0xFFFFF3E0), const Color(0xFF8A4B00)),
      StatusTone.danger => (const Color(0xFFFDECEA), AppColors.danger),
      StatusTone.info => (const Color(0xFFE8EFFD), const Color(0xFF1D4ED8)),
      StatusTone.neutral => (AppColors.cream, AppColors.textSecondary),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w700,
          color: fg,
          letterSpacing: 0.1,
        ),
      ),
    );
  }
}

enum StatusTone { success, warning, danger, info, neutral }
