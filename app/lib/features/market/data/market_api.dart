import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'market_model.dart';

/// Market-data endpoints — `backend/app/api/v1/market.py`.
class MarketApi {
  MarketApi(this._dio);
  final Dio _dio;

  /// GET /market-prices/recommendation — transparent median-based price
  /// guidance. A 404 means "no data for this selection yet" (the backend
  /// raises NotFoundError when it has no recent observations), which the
  /// UI presents as an honest empty state, not a crash.
  Future<PriceRecommendation> recommendation({
    required String commodityId,
    String? district,
  }) async {
    final res = await guard<Response>(
      () => _dio.get('/market-prices/recommendation', queryParameters: {
        'commodity_id': commodityId,
        if (district != null && district.trim().isNotEmpty)
          'district': district.trim(),
      }),
    );
    throwIfError(res);
    return PriceRecommendation.fromJson(res.data as Map<String, dynamic>);
  }
}
