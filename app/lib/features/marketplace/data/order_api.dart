import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'order_model.dart';

/// Order endpoints — `backend/app/api/v1/orders.py`.
class OrderApi {
  OrderApi(this._dio);
  final Dio _dio;

  /// POST /orders/checkout — creates an order from the cart. An
  /// idempotency key guards against double submissions.
  Future<Order> checkout({
    required String deliveryName,
    required String deliveryPhone,
    required String deliveryAddress,
    required String deliveryDistrict,
    String? notes,
  }) async {
    final res = await guard<Response>(
      () => _dio.post('/orders/checkout', data: {
        'idempotency_key': 'app-${DateTime.now().millisecondsSinceEpoch}',
        // Backend FulfilmentType enum is lowercase (backend/app/models/enums.py).
        'fulfilment': 'delivery',
        'delivery_name': deliveryName,
        'delivery_phone': deliveryPhone,
        'delivery_address': deliveryAddress,
        'delivery_district': deliveryDistrict,
        if (notes != null && notes.isNotEmpty) 'notes': notes,
      }),
    );
    throwIfError(res);
    return Order.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /orders/mine — buyer's orders.
  Future<OrderPage> mine({String? status, int pageSize = 20}) async {
    final res = await guard<Response>(
      () => _dio.get('/orders/mine', queryParameters: {
        if (status != null && status.isNotEmpty) 'status': status,
        'page_size': pageSize,
      }),
    );
    throwIfError(res);
    return OrderPage.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /orders/farmer — orders containing this farmer's (or FPO members')
  /// listings.
  Future<OrderPage> farmerOrders({int pageSize = 20}) async {
    final res = await guard<Response>(
      () => _dio.get('/orders/farmer', queryParameters: {'page_size': pageSize}),
    );
    throwIfError(res);
    return OrderPage.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /orders/{id}
  Future<Order> get(String id) async {
    final res = await guard<Response>(() => _dio.get('/orders/$id'));
    throwIfError(res);
    return Order.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /orders/{id}/farmer-response — accept or reject.
  Future<Order> farmerResponse(String id, {required bool accept, String? reason}) async {
    final res = await guard<Response>(
      () => _dio.post('/orders/$id/farmer-response', data: {
        'accept': accept,
        if (!accept && reason != null && reason.isNotEmpty) 'reason': reason,
      }),
    );
    throwIfError(res);
    return Order.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /orders/{id}/pay — buyer's one-tap mock payment capture
  /// (backend endpoint exists only while demo mode is on; a real provider
  /// would capture through its signed webhook instead).
  Future<Order> pay(String id) async {
    final res = await guard<Response>(() => _dio.post('/orders/$id/pay'));
    throwIfError(res);
    return Order.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /orders/{id}/cancel — buyer cancellation.
  Future<Order> cancel(String id, {String? reason}) async {
    final res = await guard<Response>(
      () => _dio.post('/orders/$id/cancel', data: {
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      }),
    );
    throwIfError(res);
    return Order.fromJson(res.data as Map<String, dynamic>);
  }
}
