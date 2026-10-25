import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin/admin_shell.dart';
import '../../features/auth/controllers/auth_controller.dart';
import '../../features/auth/screens/language_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/auth/screens/splash_screen.dart';
import '../../features/auth/screens/welcome_screen.dart';
import '../../features/buyer/buyer_shell.dart';
import '../../features/buyer/screens/checkout_screen.dart';
import '../../features/buyer/screens/listing_detail_screen.dart';
import '../../features/driver/driver_shell.dart';
import '../../features/farmer/farmer_shell.dart';
import '../../features/farmer/screens/create_listing_screen.dart';
import '../../features/fpo/fpo_shell.dart';
import '../../features/payments/screens/payment_screen.dart';
import '../../features/shared/order_detail_screen.dart';

const _publicRoutes = {'/welcome', '/login', '/language', '/register'};

/// Bridges Riverpod state changes into GoRouter's refreshListenable.
class _AuthListenable extends ChangeNotifier {
  _AuthListenable(Ref ref) {
    ref.listen<AuthState>(authControllerProvider, (_, _) => notifyListeners());
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: _AuthListenable(ref),
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      final location = state.uri.path;
      final isPublic = _publicRoutes.contains(location);

      if (auth is AuthInitial) {
        // Stay on splash while the session is being validated.
        return location == '/' ? null : '/';
      }
      if (auth is AuthUnauthenticated) {
        return isPublic || location == '/' ? null : '/welcome';
      }
      // Authenticated.
      if (location == '/' || isPublic) {
        return (auth as AuthAuthenticated).user.primaryRole.homePath;
      }
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/welcome', builder: (_, _) => const WelcomeScreen()),
      GoRoute(path: '/language', builder: (_, _) => const LanguageScreen()),
      GoRoute(
        path: '/login',
        builder: (_, state) => LoginScreen(
          role: state.uri.queryParameters['role'],
        ),
      ),
      GoRoute(
        path: '/register',
        builder: (_, state) {
          final params = state.uri.queryParameters;
          return RegisterScreen(
            token: params['token'] ?? '',
            phone: params['phone'] ?? '',
            role: params['role'],
          );
        },
      ),
      GoRoute(
        path: '/farmer',
        builder: (_, _) => const FarmerShell(),
        routes: [
          GoRoute(
            path: 'listing/new',
            builder: (_, _) => const CreateListingScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/buyer',
        builder: (_, _) => const BuyerShell(),
      ),
      GoRoute(
        path: '/driver',
        builder: (_, _) => const DriverShell(),
      ),
      GoRoute(
        path: '/fpo',
        builder: (_, _) => const FpoShell(),
      ),
      GoRoute(
        path: '/admin',
        builder: (_, _) => const AdminShell(),
      ),
      // Cross-role detail routes (pushed above the shells).
      GoRoute(
        path: '/listing/:id',
        builder: (_, state) =>
            ListingDetailScreen(listingId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/order/:id',
        builder: (_, state) =>
            OrderDetailScreen(orderId: state.pathParameters['id']!),
        routes: [
          GoRoute(
            path: 'pay',
            builder: (_, state) =>
                PaymentScreen(orderId: state.pathParameters['id']!),
          ),
        ],
      ),
      GoRoute(
        path: '/checkout',
        builder: (_, _) => const CheckoutScreen(),
      ),
    ],
  );
});
