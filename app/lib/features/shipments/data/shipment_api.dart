import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'shipment_model.dart';

/// Shipment + driver endpoints — `backend/app/api/v1/shipments.py` and
/// `drivers.py`. Used by both the driver flow and the FPO dispatch flow.
class ShipmentApi {
  ShipmentApi(this._dio);
  final Dio _dio;

  List<Shipment> _parseList(Object? data) {
    final raw = data is List ? data : (data is Map ? data['items'] as List? : null);
    return (raw ?? [])
        .map((e) => Shipment.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }

  /// GET /shipments/mine — the signed-in driver's runs.
  Future<List<Shipment>> mine() async {
    final res = await guard<Response>(() => _dio.get('/shipments/mine'));
    throwIfError(res);
    return _parseList(res.data);
  }

  /// GET /shipments/{id} — full run with ordered stops + crate manifest.
  Future<Shipment> get(String id) async {
    final res = await guard<Response>(() => _dio.get('/shipments/$id'));
    throwIfError(res);
    return Shipment.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /shipments — FPO creates a run from confirmed member orders.
  Future<Shipment> create({
    required List<String> orderIds,
    String? driverId,
  }) async {
    final res = await guard<Response>(
      () => _dio.post('/shipments', data: {
        'order_ids': orderIds,
        if (driverId != null && driverId.isNotEmpty) 'driver_id': driverId,
      }),
    );
    throwIfError(res);
    return Shipment.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /shipments/{id}/start — driver begins the run.
  Future<Shipment> start(String id) async {
    final res = await guard<Response>(() => _dio.post('/shipments/$id/start'));
    throwIfError(res);
    return Shipment.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /shipments/stops/{id}/complete — QR token or manual crate code.
  /// `method` is 'qr' or 'code'; returns the updated run, but the UI
  /// re-fetches anyway so partial responses stay safe.
  Future<void> completeStop({
    required String stopId,
    required String method,
    required String code,
  }) async {
    final res = await guard<Response>(
      () => _dio.post('/shipments/stops/$stopId/complete', data: {
        'method': method,
        'code': code,
      }),
    );
    throwIfError(res);
  }

  /// POST /shipments/stops/{id}/fail — report a problem with a reason.
  Future<void> failStop({required String stopId, required String reason}) async {
    final res = await guard<Response>(
      () => _dio.post('/shipments/stops/$stopId/fail', data: {
        'reason': reason,
      }),
    );
    throwIfError(res);
  }

  /// GET /drivers — driver roster for the FPO dispatch form.
  Future<List<DriverOption>> drivers() async {
    final res = await guard<Response>(() => _dio.get('/drivers'));
    throwIfError(res);
    final raw = res.data is List
        ? res.data as List
        : ((res.data as Map?)?['items'] as List?);
    return (raw ?? [])
        .map((e) => DriverOption.fromJson((e as Map).cast<String, dynamic>()))
        .toList();
  }
}
