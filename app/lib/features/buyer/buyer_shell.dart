import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../auth/controllers/auth_controller.dart';
import '../market/screens/market_screen.dart';
import '../rfq/screens/business_rfq_tab.dart';
import '../shared/profile_tab.dart';
import 'screens/cart_tab.dart';
import 'screens/my_orders_tab.dart';
import 'screens/shop_tab.dart';

/// Buyer shell: Shop / Cart / Orders / Market / Profile — business-role
/// users additionally get the Demand (RFQ) tab.
class BuyerShell extends ConsumerWidget {
  const BuyerShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(currentUserProvider);
    final isBusiness = user?.roles.contains('business') ?? false;

    return RoleShell(
      tabs: [
        ShellTab(
          icon: Icons.storefront_outlined,
          selectedIcon: Icons.storefront_rounded,
          label: t.navShop,
          body: const ShopTab(),
        ),
        ShellTab(
          icon: Icons.shopping_cart_outlined,
          selectedIcon: Icons.shopping_cart_rounded,
          label: t.navCart,
          body: const CartTab(),
        ),
        ShellTab(
          icon: Icons.receipt_long_outlined,
          selectedIcon: Icons.receipt_long_rounded,
          label: t.navOrders,
          body: const MyOrdersTab(),
        ),
        ShellTab(
          icon: Icons.query_stats_outlined,
          selectedIcon: Icons.query_stats_rounded,
          label: t.navMarket,
          body: const MarketScreen(),
        ),
        if (isBusiness)
          ShellTab(
            icon: Icons.request_quote_outlined,
            selectedIcon: Icons.request_quote_rounded,
            label: t.navDemand,
            body: const BusinessRfqTab(),
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
