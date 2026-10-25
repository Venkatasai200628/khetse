/// Single source of truth for environment configuration.
///
/// Override the API base URL at build/run time with:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
class AppConfig {
  AppConfig._();

  /// Base URL of the KhetSe FastAPI backend (v1 API).
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  /// Android emulator reaches the host machine on 10.0.2.2.
  static const String androidEmulatorBaseUrl =
      'http://10.0.2.2:8000/api/v1';

  /// The tagline shown on the splash screen.
  static const String tagline = 'Seedha Khet Se Ghar Tak';

  /// Demo login codes seeded by the backend (`backend/app/db/seed.py`,
  /// DEMO_USERS). The login screen prefers the live list from
  /// GET /meta/welcome and falls back to these when offline.
  static const List<String> demoCodes = [
    'farmer1',
    'buyer1',
    'driver1',
    'fpo1',
    'admin1',
  ];

  /// Short label for a demo code, e.g. `farmer1` → `Farmer`.
  static String demoLabel(String code) {
    final role = code.replaceAll(RegExp(r'\d+$'), '');
    switch (role) {
      case 'farmer':
        return 'Farmer';
      case 'buyer':
        return 'Buyer';
      case 'driver':
        return 'Driver';
      case 'fpo':
        return 'FPO Operator';
      case 'admin':
        return 'Admin';
      default:
        return code;
    }
  }
}
