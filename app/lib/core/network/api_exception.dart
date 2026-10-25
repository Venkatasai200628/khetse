import 'package:dio/dio.dart';

/// Application-level API error with a human-readable message derived from
/// the FastAPI error body (`{"error": {"code": ..., "message": ...}}`).
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.code});

  final String message;
  final int? statusCode;
  final String? code;

  factory ApiException.fromDio(DioException e) {
    final status = e.response?.statusCode;
    final data = e.response?.data;
    String message = e.message ?? 'Network error';

    if (data is Map) {
      final error = data['error'];
      if (error is Map && error['message'] is String) {
        message = error['message'] as String;
      } else if (data['detail'] is String) {
        message = data['detail'] as String;
      } else if (data['message'] is String) {
        message = data['message'] as String;
      }
    }

    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout) {
      message = 'Could not reach the KhetSe server. Is the backend running?';
    }

    return ApiException(message, statusCode: status);
  }

  bool get isAuthError => statusCode == 401;

  bool get isForbidden => statusCode == 403;

  @override
  String toString() => message;
}
