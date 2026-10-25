import 'package:shared_preferences/shared_preferences.dart';

/// Persists the access token across restarts.
class TokenStore {
  TokenStore._();

  static const _key = 'khetse.access_token';

  static Future<String?> read() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_key);
  }

  static Future<void> write(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, token);
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
