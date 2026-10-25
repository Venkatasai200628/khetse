import 'package:flutter/material.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../shared/profile_tab.dart';
import 'screens/fpo_orders_tab.dart';

/// FPO shell: Orders / Profile.
class FpoShell extends StatelessWidget {
  const FpoShell({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return RoleShell(
      tabs: [
        ShellTab(
          icon: Icons.receipt_long_outlined,
          selectedIcon: Icons.receipt_long_rounded,
          label: t.navOrders,
          body: const FpoOrdersTab(),
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
