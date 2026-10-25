import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../market/screens/market_screen.dart';
import '../shared/profile_tab.dart';
import 'screens/farmer_home_tab.dart';
import 'screens/farmer_orders_tab.dart';
import 'screens/my_listings_tab.dart';

/// Selected tab of the farmer shell, controlled from outside so flows can
/// land the farmer on a specific tab (the voice flow lands on Listings).
final farmerShellTabProvider = StateProvider<int>((_) => 0);

/// Farmer shell: Home / Listings / Orders / Market / Profile.
class FarmerShell extends ConsumerWidget {
  const FarmerShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final index = ref.watch(farmerShellTabProvider);
    return RoleShell(
      currentIndex: index,
      onTabChanged: (i) =>
          ref.read(farmerShellTabProvider.notifier).state = i,
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
          icon: Icons.query_stats_outlined,
          selectedIcon: Icons.query_stats_rounded,
          label: t.navMarket,
          body: const MarketScreen(),
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
