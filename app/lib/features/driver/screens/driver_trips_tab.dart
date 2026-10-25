import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/role_shell.dart';
import '../../auth/controllers/auth_controller.dart';

/// Driver dashboard. The backend does not expose shipment/dispatch
/// endpoints yet (Phase 4 in ANALYSIS.md §9), so this screen shows the
/// driver's real profile + verification status from GET /auth/me and an
/// honest empty state for trips — no invented assignments or fake stats.
class DriverTripsTab extends ConsumerWidget {
  const DriverTripsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(currentUserProvider);

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
                  value: user?.status == 'active' ? t.verified : (user?.status ?? '—'),
                  icon: Icons.verified_rounded,
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          SectionHeader(t.upcomingTrips),
          SizedBox(
            height: 420,
            child: EmptyState(
              icon: Icons.route_rounded,
              title: t.noTripsTitle,
              message: t.noTripsMessage,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.paleGreen,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_outline_rounded,
                    color: AppColors.deep, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    t.driverPhaseNote,
                    style: const TextStyle(
                        fontSize: 13,
                        height: 1.4,
                        color: AppColors.deep,
                        fontWeight: FontWeight.w500),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
