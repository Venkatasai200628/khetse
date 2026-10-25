import 'package:flutter/material.dart';

import '../../core/widgets/role_shell.dart';
import '../../l10n/app_localizations.dart';
import '../shared/profile_tab.dart';
import 'screens/cart_tab.dart';
import 'screens/my_orders_tab.dart';
import 'screens/shop_tab.dart';

/// Buyer shell: Shop / Cart / Orders / Profile.
class BuyerShell extends StatelessWidget {
  const BuyerShell({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
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
          icon: Icons.person_outline_rounded,
          selectedIcon: Icons.person_rounded,
          label: t.navProfile,
          body: const ProfileTab(),
        ),
      ],
    );
  }
}
