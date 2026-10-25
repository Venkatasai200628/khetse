import 'package:flutter/material.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../shared/profile_tab.dart';
import 'screens/driver_trips_tab.dart';

/// Driver shell: Trips / Profile.
class DriverShell extends StatelessWidget {
  const DriverShell({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return RoleShell(
      tabs: [
        ShellTab(
          icon: Icons.route_outlined,
          selectedIcon: Icons.route_rounded,
          label: t.navTrips,
          body: const DriverTripsTab(),
        ),
        ShellTab(
          icon: Icons.person_outline_rounded,
          selectedIcon: Icons.person_rounded,
          label: t.navProfile,
          body: const ProfileTab(),
        ),
      ],
    );
  }
}
