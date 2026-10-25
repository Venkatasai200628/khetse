import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// One tab of a role shell.
class ShellTab {
  const ShellTab({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.body,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Widget body;
}

/// Role dashboard chrome: a bottom NavigationBar with a persistent
/// IndexedStack so each tab keeps its scroll position and state.
class RoleShell extends StatefulWidget {
  const RoleShell({super.key, required this.tabs});

  final List<ShellTab> tabs;

  @override
  State<RoleShell> createState() => _RoleShellState();
}

class _RoleShellState extends State<RoleShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [for (final tab in widget.tabs) tab.body],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final tab in widget.tabs)
            NavigationDestination(
              icon: Icon(tab.icon),
              selectedIcon: Icon(tab.selectedIcon),
              label: tab.label,
            ),
        ],
      ),
    );
  }
}

/// Standard scrollable body padding used by every dashboard tab.
class TabBody extends StatelessWidget {
  const TabBody({super.key, required this.child, this.bottomPadding = 24});

  final Widget child;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: EdgeInsets.fromLTRB(20, 12, 20, bottomPadding),
        child: child,
      ),
    );
  }
}

/// Green gradient hero header used at the top of role dashboards.
class DashboardHeader extends StatelessWidget {
  const DashboardHeader({
    super.key,
    required this.greeting,
    required this.subtitle,
  });

  final String greeting;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, AppColors.deep],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  greeting,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 19,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.88),
                    fontSize: 13.5,
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
