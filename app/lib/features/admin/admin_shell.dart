import 'package:flutter/material.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../shared/profile_tab.dart';
import 'screens/admin_overview_tab.dart';

/// Admin shell: Overview / Profile.
class AdminShell extends StatelessWidget {
  const AdminShell({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return RoleShell(
      tabs: [
        ShellTab(
          icon: Icons.dashboard_outlined,
          selectedIcon: Icons.dashboard_rounded,
          label: t.navOverview,
          body: const AdminOverviewTab(),
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
