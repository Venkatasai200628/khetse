import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'user_model.dart';

/// Auth API client — endpoints from `backend/app/api/v1/auth.py`.
class AuthApi {
  AuthApi(this._dio);
  final Dio _dio;

  /// POST /auth/otp/request — in demo mode the response carries `dev_otp`
  /// because the SMS provider is a mock (never happens in production).
  Future<OtpRequestResult> requestOtp(String phone) async {
    final res = await guard<Response>(
      () => _dio.post('/auth/otp/request', data: {'phone': phone}),
    );
    throwIfError(res);
    return OtpRequestResult.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /auth/otp/verify — returns either an authenticated session or a
  /// registration token for first-time users.
  Future<OtpVerifyResult> verifyOtp(String phone, String code) async {
    final res = await guard<Response>(
      () => _dio.post('/auth/otp/verify', data: {
        'phone': phone,
        'code': code,
      }),
    );
    throwIfError(res);
    final data = res.data as Map<String, dynamic>;
    final outcome = data['outcome'] as String? ?? 'authenticated';
    if (outcome == 'registration_required') {
      return OtpRegistrationRequired(
        registrationToken: data['registration_token'] as String,
        phone: data['phone'] as String,
      );
    }
    return OtpAuthenticated(
      token: data['access_token'] as String,
      user: AppUser.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  /// POST /auth/register — completes signup after OTP for a new phone.
  Future<(String, AppUser)> register({
    required String registrationToken,
    required String fullName,
    required String role,
    required String preferredLanguage,
  }) async {
    final res = await guard<Response>(
      () => _dio.post('/auth/register', data: {
        'registration_token': registrationToken,
        'full_name': fullName,
        'role': role,
        'preferred_language': preferredLanguage,
      }),
    );
    throwIfError(res);
    final data = res.data as Map<String, dynamic>;
    return (
      data['access_token'] as String,
      AppUser.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  /// POST /auth/demo-login — one-tap login for the seeded demo accounts
  /// (`farmer1`, `buyer1`, `driver1`, `fpo1`, `admin1` — see DEMO_USERS in
  /// backend/app/db/seed.py; also served by GET /welcome).
  Future<(String, AppUser)> demoLogin(String demoCode) async {
    final res = await guard<Response>(
      () => _dio.post('/auth/demo-login', data: {'demo_code': demoCode}),
    );
    throwIfError(res);
    final data = res.data as Map<String, dynamic>;
    return (
      data['access_token'] as String,
      AppUser.fromJson(data['user'] as Map<String, dynamic>),
    );
  }

  /// GET /welcome — public landing payload. While demo mode is on it
  /// carries the seeded demo-login handles, so the login screen shows
  /// exactly the accounts the backend knows (empty when demo mode is off).
  Future<List<String>> welcomeDemoCodes() async {
    final res = await guard<Response>(() => _dio.get('/welcome'));
    throwIfError(res);
    final data = res.data as Map<String, dynamic>;
    return (data['demo_codes'] as List? ?? []).cast<String>();
  }

  /// GET /auth/me — validates the stored token and returns the profile.
  Future<AppUser> me() async {
    final res = await guard<Response>(() => _dio.get('/auth/me'));
    throwIfError(res);
    return AppUser.fromJson(res.data as Map<String, dynamic>);
  }
}



class OtpRequestResult {
  OtpRequestResult({
    required this.expiresInSeconds,
    this.devOtp,
    this.note,
  });

  final int expiresInSeconds;
  final String? devOtp;
  final String? note;

  factory OtpRequestResult.fromJson(Map<String, dynamic> json) =>
      OtpRequestResult(
        expiresInSeconds: (json['expires_in_seconds'] ?? 300) as int,
        devOtp: json['dev_otp'] as String?,
        note: json['note'] as String?,
      );
}

/// Discriminated result of OTP verification.
sealed class OtpVerifyResult {
  const OtpVerifyResult();
}

class OtpAuthenticated extends OtpVerifyResult {
  const OtpAuthenticated({required this.token, required this.user});

  final String token;
  final AppUser user;
}

class OtpRegistrationRequired extends OtpVerifyResult {
  const OtpRegistrationRequired({
    required this.registrationToken,
    required this.phone,
  });

  final String registrationToken;
  final String phone;
}
