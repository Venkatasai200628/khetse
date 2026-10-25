import 'package:flutter/material.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../shared/profile_tab.dart';
import 'screens/farmer_home_tab.dart';
import 'screens/farmer_orders_tab.dart';
import 'screens/my_listings_tab.dart';

/// Farmer shell: Home / Listings / Orders / Profile.
class FarmerShell extends StatelessWidget {
  const FarmerShell({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return RoleShell(
      tabs: [
        ShellTab(
          icon: Icons.home_outlined,
          selectedIcon: Icons.home_rounded,
          label: t.navHome,
          body: const FarmerHomeTab(),
        ),
        ShellTab(
          icon: Icons.sell_outlined,
          selectedIcon: Icons.sell_rounded,
          label: t.navListings,
          body: const MyListingsTab(),
        ),
        ShellTab(
          icon: Icons.receipt_long_outlined,
          selectedIcon: Icons.receipt_long_rounded,
          label: t.navOrders,
          body: const FarmerOrdersTab(),
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
