import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import 'voice_api.dart';
import 'voice_model.dart';

final voiceApiProvider =
    Provider<VoiceApi>((ref) => VoiceApi(ref.watch(apiClientProvider)));

/// Speech pipeline status — GET /voice/status.
final voiceStatusProvider =
    FutureProvider.autoDispose<VoiceStatus>((ref) {
  final api = ref.watch(voiceApiProvider);
  return api.status();
});
