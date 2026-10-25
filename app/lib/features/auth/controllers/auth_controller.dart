import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/token_store.dart';
import '../data/auth_api.dart';
import '../data/user_model.dart';

final authApiProvider = Provider<AuthApi>((ref) => AuthApi(ref.watch(apiClientProvider)));

/// Session lifecycle for the whole app.
sealed class AuthState {
  const AuthState();
}

/// Still checking the stored token against GET /auth/me.
class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.user);

  final AppUser user;
}

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() {
    bootstrap();
    return const AuthInitial();
  }

  Future<void> bootstrap() async {
    final token = await TokenStore.read();
    if (token == null || token.isEmpty) {
      state = const AuthUnauthenticated();
      return;
    }
    try {
      final user = await ref.read(authApiProvider).me();
      state = AuthAuthenticated(user);
    } on ApiException catch (e) {
      // Expired/invalid token → clear and fall back to welcome.
      if (e.isAuthError || e.isForbidden) {
        await TokenStore.clear();
      }
      state = const AuthUnauthenticated();
    }
  }

  /// Called after OTP verify / register / demo-login succeed.
  Future<void> adoptSession(String token, AppUser user) async {
    await TokenStore.write(token);
    ref.invalidate(apiClientProvider); // not strictly needed; interceptor reads store
    state = AuthAuthenticated(user);
  }

  Future<void> logout() async {
    await TokenStore.clear();
    state = const AuthUnauthenticated();
  }
}

final authControllerProvider =
    NotifierProvider<AuthController, AuthState>(AuthController.new);

/// Convenience: current user or null.
final currentUserProvider = Provider<AppUser?>((ref) {
  final state = ref.watch(authControllerProvider);
  return state is AuthAuthenticated ? state.user : null;
});
