import 'package:dio/dio.dart';

import 'api_exception.dart';

/// Throws a friendly [ApiException] when the response carries an HTTP error
/// status (Dio is configured to hand us 4xx instead of throwing).
void throwIfError(Response res) {
  final status = res.statusCode;
  if (status != null && status >= 400) {
    throw ApiException(
      extractMessage(res.data) ?? 'Request failed ($status)',
      statusCode: status,
    );
  }
}

/// Pulls a human-readable message out of the FastAPI error body
/// (`{"error": {"code", "message"}}`, `detail`, or `message`).
String? extractMessage(Object? data) {
  if (data is Map) {
    final error = data['error'];
    if (error is Map && error['message'] is String) {
      return error['message'] as String;
    }
    if (data['detail'] is String) return data['detail'] as String;
    if (data['message'] is String) return data['message'] as String;
  }
  return null;
}
