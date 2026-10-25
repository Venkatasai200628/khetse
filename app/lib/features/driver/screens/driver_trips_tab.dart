import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../auth/controllers/auth_controller.dart';
import '../../shipments/data/providers.dart';
import '../../shipments/data/shipment_model.dart';

/// Driver dashboard — the driver's real runs from GET /shipments/mine plus
/// the profile verification status from GET /auth/me. Nothing is invented.
class DriverTripsTab extends ConsumerWidget {
  const DriverTripsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(currentUserProvider);
    final shipmentsAsync = ref.watch(myShipmentsProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DashboardHeader(
            greeting: '${t.hello}, ${user?.displayName.split(' ').first ?? ''} 👋',
            subtitle: t.driverHeaderSubtitle,
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: t.verificationStatus,
                  value:
                      user?.status == 'active' ? t.verified : (user?.status ?? '—'),
                  icon: Icons.verified_rounded,
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          SectionHeader(t.upcomingTrips),
          const SizedBox(height: 12),
          shipmentsAsync.when(
            loading: () => const SkeletonList(itemCount: 3, itemHeight: 110),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(myShipmentsProvider),
              compact: true,
            ),
            data: (shipments) {
              if (shipments.isEmpty) {
                return SizedBox(
                  height: 420,
                  child: EmptyState(
                    icon: Icons.route_rounded,
                    title: t.noTripsTitle,
                    message: t.noTripsMessage,
                  ),
                );
              }
              return Column(
                children: [
                  for (final shipment in shipments)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: ShipmentCard(shipment: shipment),
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

/// Compact run card — status, route, distance and stop count from the API.
class ShipmentCard extends StatelessWidget {
  const ShipmentCard({super.key, required this.shipment});

  final Shipment shipment;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        onTap: () => context.push('/shipment/${shipment.id}'),
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
                      shipment.routeLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                  ),
                  StatusChip.forShipmentStatus(shipment.status),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.route_rounded,
                      size: 15, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Text(
                    shipment.distanceLabel,
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 14),
                  const Icon(Icons.linear_scale_rounded,
                      size: 15, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Text(
                    t.shipmentStopCount(shipment.stopCount),
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                  if (shipment.pendingStopCount > 0) ...[
                    const SizedBox(width: 14),
                    StatusChip(
                      label: t.shipmentPendingCount(shipment.pendingStopCount),
                      tone: StatusTone.warning,
                    ),
                  ],
                  const Spacer(),
                  const Icon(Icons.chevron_right_rounded,
                      size: 20, color: AppColors.textSecondary),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
