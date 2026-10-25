import 'package:dio/dio.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/response_utils.dart';
import 'voice_model.dart';

/// Voice endpoints — `backend/app/api/v1/voice.py`.
class VoiceApi {
  VoiceApi(this._dio);
  final Dio _dio;

  /// GET /voice/status — tells the app whether speech is simulated (demo
  /// mode) or running through Bhashini, plus optional server-side samples.
  Future<VoiceStatus> status() async {
    final res = await guard<Response>(() => _dio.get('/voice/status'));
    throwIfError(res);
    return VoiceStatus.fromJson(res.data as Map<String, dynamic>);
  }

  /// POST /voice/listing-draft — sends what the farmer said (or typed in
  /// the demo) and returns the transcript plus the extracted draft fields.
  Future<VoiceDraft> draft({required String text, required String language}) async {
    final res = await guard<Response>(
      () => _dio.post('/voice/listing-draft', data: {
        'text': text,
        'language': language,
      }),
    );
    throwIfError(res);
    return VoiceDraft.fromJson(res.data as Map<String, dynamic>);
  }
}
