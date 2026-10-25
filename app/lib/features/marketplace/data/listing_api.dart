import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'listing_model.dart';

/// Listing + commodity endpoints — `backend/app/api/v1/listings.py`
/// and `backend/app/api/v1/commodities.py`.
class ListingApi {
  ListingApi(this._dio);
  final Dio _dio;

  /// GET /listings — buyer browse with optional filters.
  Future<ListingPage> browse({
    String? search,
    String? category,
    String? district,
    int page = 1,
    int pageSize = 20,
  }) async {
    final res = await guard<Response>(() => _dio.get('/listings', queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          if (category != null && category.isNotEmpty) 'category': category,
          if (district != null && district.isNotEmpty) 'district': district,
          'page': page,
          'page_size': pageSize,
        }));
    throwIfError(res);
    return ListingPage.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /listings/{id}
  Future<Listing> get(String id) async {
    final res = await guard<Response>(() => _dio.get('/listings/$id'));
    throwIfError(res);
    return Listing.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /listings/mine — the farmer's own listings.
  Future<List<Listing>> mine() async {
    final res = await guard<Response>(() => _dio.get('/listings/mine'));
    throwIfError(res);
    return (res.data as List? ?? [])
        .map((e) => Listing.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// POST /listings — create a listing (money in integer paise).
  Future<Listing> create({
    required String commodityId,
    required double quantityTotal,
    required String unit,
    required int minPricePaise,
    required int listedPricePaise,
    String qualityGrade = 'ungraded',
    String? description,
    DateTime? harvestDate,
    DateTime? availableFrom,
  }) async {
    String formatdate(DateTime d) =>
        '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    final res = await guard<Response>(
      () => _dio.post('/listings', data: {
        'commodity_id': commodityId,
        'quantity_total': quantityTotal,
        'unit': unit,
        'min_price_paise': minPricePaise,
        'listed_price_paise': listedPricePaise,
        'quality_grade': qualityGrade,
        if (description != null && description.isNotEmpty)
          'description': description,
        if (harvestDate != null) 'harvest_date': formatdate(harvestDate),
        if (availableFrom != null) 'available_from': formatdate(availableFrom),
      }),
    );
    throwIfError(res);
    return Listing.fromJson(res.data as Map<String, dynamic>);
  }

  /// PATCH /listings/{id}/status — pause / activate / withdraw.
  Future<Listing> setStatus(String id, String status) async {
    final res = await guard<Response>(
      () => _dio.patch('/listings/$id/status', data: {'status': status}),
    );
    throwIfError(res);
    return Listing.fromJson(res.data as Map<String, dynamic>);
  }

  /// GET /commodities — catalogue used by the create-listing form.
  Future<List<Commodity>> commodities() async {
    final res = await guard<Response>(() => _dio.get('/commodities'));
    throwIfError(res);
    return (res.data as List? ?? [])
        .map((e) => Commodity.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
