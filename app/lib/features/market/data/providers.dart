import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import 'market_api.dart';

final marketApiProvider =
    Provider<MarketApi>((ref) => MarketApi(ref.watch(apiClientProvider)));
