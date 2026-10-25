import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/response_utils.dart';
import 'rfq_model.dart';

/// RFQ endpoints — `backend/app/api/v1/rfq.py`.
class RfqApi {
  RfqApi(this._dio);
  final Dio _dio;

  List<Rfq> _parseList(Object? data) {
    final raw =
        data is List ? data : (data is Map ? data['items'] as List? : null);
    return (raw ?? [])
        .map((e) => Rfq.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  /// POST /rfq — a business posts demand (money in integer paise).
  Future<Rfq> create({
    required String commodityId,
    required double quantity,
    required String unit,
    required int maxPricePaise,
    DateTime? neededBy,
  }) async {
    final res = await guard<Response>(
      () => _dio.post('/rfq', data: {
        'commodity_id': commodityId,
        'quantity': quantity,
        'unit': unit,
        'max_price_paise': maxPricePaise,
        if (neededBy != null)
          'needed_by':
              '${neededBy.year.toString().padLeft(4, '0')}-${neededBy.month.toString().padLeft(2, '0')}-${neededBy.day.toString().padLeft(2, '0')}',
      }),
    );
    throwIfError(res);
    return Rfq.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /rfq/mine — the business's own requests with their offers.
  Future<List<Rfq>> mine() async {
    final res = await guard<Response>(() => _dio.get('/rfq/mine'));
    throwIfError(res);
    return _parseList(res.data);
  }

  /// GET /rfq/open — open demand visible to farmers.
  Future<List<Rfq>> open() async {
    final res = await guard<Response>(() => _dio.get('/rfq/open'));
    throwIfError(res);
    return _parseList(res.data);
  }

  /// POST /rfq/{id}/offers — a farmer quotes against open demand.
  Future<RfqOffer> offer({
    required String rfqId,
    required int pricePaise,
    double? quantity,
  }) async {
    final data = <String, dynamic>{'price_paise': pricePaise};
    if (quantity != null) data['quantity'] = quantity;
    final res = await guard<Response>(
      () => _dio.post('/rfq/$rfqId/offers', data: data),
    );
    throwIfError(res);
    return RfqOffer.fromJson((res.data as Map).cast<String, dynamic>());
  }

  /// POST /rfq/offers/{id}/accept — the business accepts a quote; the
  /// backend creates the order and the app navigates to its payment.
  /// The response may carry the order object or just `order_id`.
  Future<String> acceptOffer(String offerId) async {
    final res =
        await guard<Response>(() => _dio.post('/rfq/offers/$offerId/accept'));
    throwIfError(res);
    final data = res.data;
    if (data is Map) {
      final orderId = data['order_id'] ?? data['id'];
      if (orderId is String && orderId.isNotEmpty) return orderId;
    }
    throw ApiException(
      'Accept succeeded but the response carried no order id.',
      statusCode: res.statusCode,
    );
  }
}
