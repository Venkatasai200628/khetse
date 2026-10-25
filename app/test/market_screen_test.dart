import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:khetse/features/market/data/market_api.dart';
import 'package:khetse/features/market/data/providers.dart';
import 'package:khetse/features/market/screens/market_screen.dart';
import 'package:khetse/features/marketplace/data/listing_model.dart';
import 'package:khetse/features/marketplace/data/providers.dart';
import 'package:khetse/l10n/app_localizations.dart';

/// Serves canned JSON per path — no network, no backend needed.
class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.responder);

  final Response<Object?> Function(RequestOptions options) responder;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final res = responder(options);
    return ResponseBody.fromString(
      jsonEncode(res.data),
      res.statusCode ?? 200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

const _commodities = [
  {
    'id': 'c-tomato',
    'name_en': 'Tomato',
    'name_te': 'టమాటా',
    'name_hi': 'टमाटर',
    'category': 'vegetables',
    'default_unit': 'kg',
  },
];

const _recommendation = {
  'id': 'rec1',
  'commodity_id': 'c-tomato',
  'commodity_name': 'Tomato',
  'district': 'Rangareddy',
  'recommended_min_paise': 1800,
  'recommended_modal_paise': 2000,
  'recommended_max_paise': 2400,
  'recommended_modal_per_kg_paise': null,
  'unit': 'kg',
  'benchmark_market': 'Bowenpally Market',
  'benchmark_observed_on': '2026-10-20',
  'benchmark_source': 'agmarknet',
  'confidence': 'high',
  'explanation': 'Median of 12 recent wholesale observations.',
  'model_run': {
    'id': 'run1',
    'model_type': 'price_recommendation',
    'model_version': 'median-v1',
    'ran_at': '2026-10-24T06:30:00',
  },
};

Future<void> _pumpMarket(WidgetTester tester, Dio dio) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        marketApiProvider.overrideWithValue(MarketApi(dio)),
        commoditiesProvider.overrideWith((ref) async => [
              Commodity.fromJson(_commodities.first.cast<String, dynamic>()),
            ]),
      ],
      child: MaterialApp(
        locale: const Locale('en'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        home: const Scaffold(body: MarketScreen()),
      ),
    ),
  );
}

void main() {
  testWidgets('market screen shows the recommendation card on success',
      (tester) async {
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8000/api/v1'))
      ..httpClientAdapter = _FakeAdapter((options) {
        if (options.path.contains('/commodities')) {
          return Response<Object?>(
              requestOptions: options, data: _commodities);
        }
        if (options.path.contains('/market-prices/recommendation')) {
          expect(options.queryParameters['commodity_id'], 'c-tomato');
          return Response<Object?>(
              requestOptions: options, data: _recommendation);
        }
        fail('unexpected path: ${options.path}');
      });

    await _pumpMarket(tester, dio);
    await tester.pump(); // commodities resolve
    await tester.pump();

    // Nothing queried yet → honest prompt.
    expect(find.text('Pick a commodity'), findsOneWidget);

    await tester.tap(find.text('Get price'));
    await tester.pump(); // request starts
    await tester.pump(const Duration(milliseconds: 50)); // data lands

    // Paise → ₹ with the unit respected.
    expect(find.text('₹18 – 20 – 24'), findsOneWidget);
    expect(find.text('per kg'), findsOneWidget);
    expect(find.text('high'), findsOneWidget); // confidence chip
    expect(find.text('Bowenpally Market'), findsOneWidget);
    expect(find.textContaining('median-v1'), findsOneWidget);
    expect(find.textContaining('Median of 12'), findsOneWidget);
  });

  testWidgets('a 404 is shown honestly as no-data, not as a crash',
      (tester) async {
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8000/api/v1'))
      ..httpClientAdapter = _FakeAdapter((options) {
        if (options.path.contains('/commodities')) {
          return Response<Object?>(
              requestOptions: options, data: _commodities);
        }
        return Response<Object?>(
          requestOptions: options,
          statusCode: 404,
          data: {
            'error': {
              'code': 'not_found',
              'message': 'no recent observations for this selection',
            }
          },
        );
      });

    await _pumpMarket(tester, dio);
    await tester.pump();
    await tester.pump();

    await tester.tap(find.text('Get price'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('No data for this selection yet'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });
}
