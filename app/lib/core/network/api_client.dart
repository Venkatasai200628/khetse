import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import 'api_exception.dart';
import 'token_store.dart';

/// The single configured Dio client for the whole app.
///
/// - Base URL comes from [AppConfig.apiBaseUrl] (one config file).
/// - Attaches the bearer token when present.
/// - Maps every failure to [ApiException] with a friendly message.
final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
      headers: {'Accept': 'application/json'},
      validateStatus: (status) => status != null && status < 500,
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await TokenStore.read();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ),
  );

  return dio;
});

/// Runs [action] and converts any [DioException] into [ApiException].
Future<T> guard<T>(Future<T> Function() action) async {
  try {
    return await action();
  } on DioException catch (e) {
    throw ApiException.fromDio(e);
  }
}
