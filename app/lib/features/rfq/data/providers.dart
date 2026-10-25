import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import 'rfq_api.dart';
import 'rfq_model.dart';

final rfqApiProvider =
    Provider<RfqApi>((ref) => RfqApi(ref.watch(apiClientProvider)));

/// The business's requests — GET /rfq/mine.
final myRfqsProvider = FutureProvider.autoDispose<List<Rfq>>((ref) {
  final api = ref.watch(rfqApiProvider);
  return api.mine();
});

/// Open demand for farmers — GET /rfq/open.
final openRfqsProvider = FutureProvider.autoDispose<List<Rfq>>((ref) {
  final api = ref.watch(rfqApiProvider);
  return api.open();
});
