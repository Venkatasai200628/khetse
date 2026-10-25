import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/misc.dart';
import '../controllers/auth_controller.dart';

/// Splash: brand mark + tagline while the stored session is validated
/// against GET /auth/me. The router redirect takes over once the auth
/// state resolves.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  bool _minDelayDone = false;

  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 1400), () {
      if (mounted) setState(() => _minDelayDone = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final resolved = auth is! AuthInitial;
    if (resolved && _minDelayDone) {
      // Defer so navigation doesn't happen during build.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        if (auth is AuthAuthenticated) {
          context.go(auth.user.primaryRole.homePath);
        } else {
          context.go('/welcome');
        }
      });
    }

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0B6B41), AppColors.primary],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: const KhetSeLogo(size: 96),
                ),
                const SizedBox(height: 28),
                const Text(
                  'KhetSe',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 44,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  AppConfig.tagline,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.92),
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 44),
                SizedBox(
                  width: 26,
                  height: 26,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.6,
                    valueColor:
                        AlwaysStoppedAnimation(Colors.white.withValues(alpha: 0.85)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
