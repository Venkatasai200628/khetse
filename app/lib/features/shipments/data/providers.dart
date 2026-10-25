import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import 'shipment_api.dart';
import 'shipment_model.dart';

final shipmentApiProvider =
    Provider<ShipmentApi>((ref) => ShipmentApi(ref.watch(apiClientProvider)));

/// The signed-in driver's runs — GET /shipments/mine.
final myShipmentsProvider =
    FutureProvider.autoDispose<List<Shipment>>((ref) {
  final api = ref.watch(shipmentApiProvider);
  return api.mine();
});

/// One run with ordered stops + manifest — GET /shipments/{id}.
final shipmentDetailProvider =
    FutureProvider.autoDispose.family<Shipment, String>((ref, id) {
  final api = ref.watch(shipmentApiProvider);
  return api.get(id);
});

/// Driver roster for the FPO dispatch form — GET /drivers.
final driversProvider = FutureProvider.autoDispose<List<DriverOption>>((ref) {
  final api = ref.watch(shipmentApiProvider);
  return api.drivers();
});
