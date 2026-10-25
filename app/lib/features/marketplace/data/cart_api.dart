import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'cart_model.dart';

/// Cart endpoints — `backend/app/api/v1/cart.py`.
class CartApi {
  CartApi(this._dio);
  final Dio _dio;

  /// GET /cart
  Future<Cart> get() async {
    final res = await guard<Response>(() => _dio.get('/cart'));
    throwIfError(res);
    return Cart.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /cart/items
  Future<Cart> add(String listingId, double quantity) async {
    final res = await guard<Response>(
      () => _dio.post('/cart/items', data: {
        'listing_id': listingId,
        'quantity': quantity,
      }),
    );
    throwIfError(res);
    return Cart.fromJson(res.data as Map<String, dynamic>);
  }

  /// PATCH /cart/items/{itemId}
  Future<Cart> updateQuantity(String itemId, double quantity) async {
    final res = await guard<Response>(
      () => _dio.patch('/cart/items/$itemId', data: {'quantity': quantity}),
    );
    throwIfError(res);
    return Cart.fromJson(res.data as Map<String, dynamic>);
  }

  /// DELETE /cart/items/{itemId}
  Future<Cart> remove(String itemId) async {
    final res = await guard<Response>(() => _dio.delete('/cart/items/$itemId'));
    throwIfError(res);
    return Cart.fromJson(res.data as Map<String, dynamic>);
  }
}
