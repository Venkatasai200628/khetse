// UI golden previews — renders the app's REAL screens (real theme, real
// widgets, real navigation shells) with representative seeded demo data
// (tomato ₹18/kg etc.) and writes one PNG per screen.
//
//   flutter test --update-goldens test/ui_goldens_test.dart
//
// PNGs land in <app>/goldens/*.png — the '../goldens/…' golden paths below
// resolve against this test file's directory (app/test/).
//
// Riverpod providers are overridden with fixed fake data built from the
// app's own model classes; the few API clients that are actually called
// during rendering (auth demo codes, voice draft, market recommendation)
// are stubbed with the same interface. No network, no backend.
//
// Note: Telugu strings render with the bundled NotoSansTelugu font; if the
// test environment ever lacks it the glyphs would render as boxes, which is
// acceptable for previews.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show FontLoader, rootBundle;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:khetse/app/app.dart';
import 'package:khetse/core/config/app_config.dart';
import 'package:khetse/core/theme/app_theme.dart';
import 'package:khetse/features/auth/controllers/auth_controller.dart';
import 'package:khetse/features/auth/data/auth_api.dart';
import 'package:khetse/features/auth/data/user_model.dart';
import 'package:khetse/features/auth/screens/welcome_screen.dart';
import 'package:khetse/features/driver/screens/driver_trips_tab.dart'
    show ShipmentCard;
import 'package:khetse/features/market/data/market_api.dart';
import 'package:khetse/features/market/data/market_model.dart';
import 'package:khetse/features/market/data/providers.dart' as market;
import 'package:khetse/features/market/screens/market_screen.dart';
import 'package:khetse/features/marketplace/data/cart_model.dart';
import 'package:khetse/features/marketplace/data/listing_model.dart';
import 'package:khetse/features/marketplace/data/order_model.dart';
import 'package:khetse/features/marketplace/data/providers.dart'
    as marketplace;
import 'package:khetse/features/payments/data/payment_api.dart';
import 'package:khetse/features/payments/screens/payment_screen.dart';
import 'package:khetse/features/rfq/data/providers.dart' as rfq;
import 'package:khetse/features/rfq/data/rfq_model.dart';
import 'package:khetse/features/shipments/data/providers.dart' as shipments;
import 'package:khetse/features/shipments/data/shipment_model.dart';
import 'package:khetse/features/voice/data/providers.dart' as voice;
import 'package:khetse/features/voice/data/voice_api.dart';
import 'package:khetse/features/voice/data/voice_model.dart';
import 'package:khetse/features/voice/screens/voice_listing_screen.dart';
import 'package:khetse/l10n/app_localizations.dart';

/// 430x932 logical at DPR 3 → crisp 1290x2796 physical PNGs.
void _usePhoneSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(430 * 3, 932 * 3);
  tester.view.devicePixelRatio = 3.0;
  addTearDown(tester.view.reset);
}

const _captureKey = ValueKey('ui-golden-capture');

const _phonePhrase = '5 క్వింటాల్ టమాటా రూ 2000';

/// Wraps [child] in the capture RepaintBoundary + a ProviderScope carrying
/// the provider [overrides].
Future<void> _pump(
  WidgetTester tester,
  Widget child, {
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    RepaintBoundary(
      key: _captureKey,
      child: ProviderScope(overrides: overrides, child: child),
    ),
  );
}

/// The real app root (real theme + real GoRouter): the router redirect lands
/// the fake-authenticated user on their role shell, bottom nav included.
Future<void> _pumpKhetSeApp(
  WidgetTester tester,
  List<Override> overrides,
) async {
  await _pump(tester, const KhetSeApp(), overrides: overrides);
  // Burn the splash delay; the redirect then lands on the role shell.
  await tester.pump(const Duration(milliseconds: 1600));
  await tester.pumpAndSettle();
}

/// Switches the role shell to the given bottom-nav tab.
Future<void> _openTab(WidgetTester tester, String label) async {
  await tester.tap(
    find.descendant(of: find.byType(NavigationBar), matching: find.text(label)),
  );
  await tester.pumpAndSettle();
}

/// Standalone screen host with the app's real theme + localizations.
class _PlainApp extends StatelessWidget {
  const _PlainApp({required this.home});

  final Widget home;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      locale: const Locale('en'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: home,
    );
  }
}

Future<void> _capture(WidgetTester tester, String name) async {
  await expectLater(
    find.byKey(_captureKey),
    matchesGoldenFile('../goldens/$name'),
  );
}

// ---------------------------------------------------------------------------
// Seeded demo data (the app's own model classes — no HTTP mocks).
// ---------------------------------------------------------------------------

final _farmer = AppUser(
  id: 'u-farmer',
  phone: '+919876543210',
  fullName: 'Ramesh Reddy',
  preferredLanguage: 'te',
  status: 'active',
  roles: const ['farmer'],
  createdAt: DateTime(2025, 11, 2),
);

final _buyer = AppUser(
  id: 'u-buyer',
  phone: '+919876543222',
  fullName: 'Megha Traders',
  preferredLanguage: 'en',
  status: 'active',
  roles: const ['buyer'],
  createdAt: DateTime(2025, 8, 15),
);

final _business = AppUser(
  id: 'u-buyer',
  phone: '+919876543222',
  fullName: 'Megha Traders',
  preferredLanguage: 'en',
  status: 'active',
  roles: const ['buyer', 'business'],
  createdAt: DateTime(2025, 8, 15),
);

final _driver = AppUser(
  id: 'u-driver',
  phone: '+919876543233',
  fullName: 'Suresh Yadav',
  preferredLanguage: 'te',
  status: 'active',
  roles: const ['driver'],
  createdAt: DateTime(2025, 9, 20),
);

final _fpoOperator = AppUser(
  id: 'u-fpo',
  phone: '+919876543244',
  fullName: 'Lakshmi Narayana',
  preferredLanguage: 'en',
  status: 'active',
  roles: const ['fpo_operator'],
  createdAt: DateTime(2025, 7, 4),
);

final _tomatoCommodity = Commodity(
  id: 'c-tomato',
  nameEn: 'Tomato',
  nameTe: 'టమాటా',
  nameHi: 'टमाटर',
  category: 'vegetables',
  defaultUnit: 'kg',
);

final _onionCommodity = Commodity(
  id: 'c-onion',
  nameEn: 'Onion',
  nameTe: 'ఉల్లి',
  nameHi: 'प्याज़',
  category: 'vegetables',
  defaultUnit: 'kg',
);

final _commodities = [_tomatoCommodity, _onionCommodity];

final _tomatoListing = Listing(
  id: 'lst-tomato-1',
  farmerId: 'u-farmer',
  commodityId: 'c-tomato',
  commodityName: 'Tomato',
  commodityNameTe: 'టమాటా',
  commodityCategory: 'vegetables',
  description: 'Fresh vine-ripened tomatoes, hand-picked at dawn.',
  quantityTotal: 500,
  quantityAvailable: 480,
  unit: 'kg',
  qualityGrade: 'A',
  harvestDate: DateTime(2026, 10, 24),
  availableFrom: DateTime(2026, 10, 25),
  minPricePaise: 1600,
  listedPricePaise: 1800, // ₹18/kg
  status: 'active',
  isSynthetic: false,
  farmerDistrict: 'Rangareddy',
  farmerVillage: 'Shadnagar',
  createdAt: DateTime(2026, 10, 24, 9, 15),
);

final _onionListing = Listing(
  id: 'lst-onion-1',
  farmerId: 'u-farmer',
  commodityId: 'c-onion',
  commodityName: 'Onion',
  commodityNameTe: 'ఉల్లి',
  commodityCategory: 'vegetables',
  description: 'Well-cured red onions.',
  quantityTotal: 800,
  quantityAvailable: 800,
  unit: 'kg',
  qualityGrade: 'A',
  harvestDate: DateTime(2026, 10, 18),
  availableFrom: DateTime(2026, 10, 20),
  minPricePaise: 2000,
  listedPricePaise: 2200, // ₹22/kg
  status: 'active',
  isSynthetic: false,
  farmerDistrict: 'Kurnool',
  farmerVillage: 'Kallur',
  createdAt: DateTime(2026, 10, 20, 7, 40),
);

final _riceListing = Listing(
  id: 'lst-rice-1',
  farmerId: 'u-farmer',
  commodityId: 'c-rice',
  commodityName: 'Rice (Sona Masoori)',
  commodityNameTe: 'వరి బియ్యం',
  commodityCategory: 'grains',
  description: 'New-crop Sona Masoori, single-polished.',
  quantityTotal: 40,
  quantityAvailable: 35,
  unit: 'quintal',
  qualityGrade: 'A',
  harvestDate: DateTime(2026, 10, 12),
  availableFrom: DateTime(2026, 10, 14),
  minPricePaise: 260000,
  listedPricePaise: 280000, // ₹2,800/quintal
  status: 'paused',
  isSynthetic: false,
  farmerDistrict: 'Nizamabad',
  farmerVillage: 'Bodhan',
  createdAt: DateTime(2026, 10, 14, 11, 5),
);

final _listings = [_tomatoListing, _onionListing, _riceListing];

OrderItem _orderItem(String id, String commodity, double qty, int unitPaise) =>
    OrderItem(
      id: id,
      listingId: 'lst-$commodity-1',
      farmerId: 'u-farmer',
      quantity: qty,
      unit: 'kg',
      unitPricePaise: unitPaise,
      lineTotalPaise: (qty * unitPaise).round(),
      qualityGrade: 'A',
      farmerResponse: 'ACCEPTED',
      commodityName: commodity,
    );

Order _order({
  required String id,
  required String district,
  required List<OrderItem> items,
  DateTime? placedAt,
}) {
  final subtotal =
      items.fold<int>(0, (sum, item) => sum + item.lineTotalPaise);
  const deliveryFee = 4000;
  final platformFee = (subtotal * 0.02).round();
  final placed = placedAt ?? DateTime(2026, 10, 23, 10, 30);
  return Order(
    id: id,
    buyerId: 'u-buyer',
    status: 'confirmed',
    paymentStatus: 'PENDING',
    fulfilment: 'DELIVERY',
    deliveryName: 'Megha Traders',
    deliveryAddress: '12-4-90, Begum Bazar',
    deliveryDistrict: district,
    subtotalPaise: subtotal,
    deliveryFeePaise: deliveryFee,
    platformFeePaise: platformFee,
    totalPaise: subtotal + deliveryFee + platformFee,
    currency: 'INR',
    notes: null,
    cancelReason: null,
    placedAt: placed,
    deliveredAt: null,
    isSynthetic: false,
    createdAt: placed,
    items: items,
    statusEvents: [
      OrderStatusEvent(
        id: 'se-$id',
        fromStatus: 'awaiting_farmer_confirmation',
        toStatus: 'confirmed',
        actorRole: 'farmer',
        reason: null,
        createdAt: DateTime(2026, 10, 23, 14, 5),
      ),
    ],
  );
}

final _tomatoOrder = _order(
  id: 'ord-1001',
  district: 'Hyderabad',
  items: [_orderItem('oi-1', 'Tomato', 25, 1800)], // 25 kg @ ₹18/kg
);

final _onionOrder = _order(
  id: 'ord-1002',
  district: 'Secunderabad',
  items: [_orderItem('oi-2', 'Onion', 10, 2200)], // 10 kg @ ₹22/kg
  placedAt: DateTime(2026, 10, 24, 9, 5),
);

final _farmerOrderPage =
    OrderPage(items: [_tomatoOrder, _onionOrder], total: 2);

/// Same two orders as [farmerOrdersProvider] but from the confirmed-only
/// query (GET /orders/farmer?status=confirmed) — FPO dispatch input.
final _confirmedOrderPage =
    OrderPage(items: [_tomatoOrder, _onionOrder], total: 2);

final _cart = Cart(
  id: 'cart-1',
  items: [
    CartItem(
      id: 'ci-1',
      listingId: 'lst-tomato-1',
      quantity: 25,
      unitPricePaise: 1800,
      lineTotalPaise: 45000,
      commodityName: 'Tomato',
      farmerDistrict: 'Rangareddy',
      listingStatus: 'active',
    ),
    CartItem(
      id: 'ci-2',
      listingId: 'lst-onion-1',
      quantity: 10,
      unitPricePaise: 2200,
      lineTotalPaise: 22000,
      commodityName: 'Onion',
      farmerDistrict: 'Kurnool',
      listingStatus: 'active',
    ),
  ],
  subtotalPaise: 67000, // ₹670
);

final _openDemandRfq = Rfq(
  id: 'rfq-100',
  buyerId: 'u-buyer',
  buyerLabel: 'Megha Traders',
  commodityId: 'c-tomato',
  commodityName: 'Tomato',
  quantity: 200,
  unit: 'kg',
  neededBy: DateTime(2026, 10, 30),
  maxPricePaise: 1800, // up to ₹18/kg
  status: 'open',
  createdAt: DateTime(2026, 10, 24, 8, 0),
  offers: const [],
);

final _myRfq = Rfq(
  id: 'rfq-200',
  buyerId: 'u-buyer',
  buyerLabel: 'Megha Traders',
  commodityId: 'c-tomato',
  commodityName: 'Tomato',
  quantity: 100,
  unit: 'kg',
  neededBy: DateTime(2026, 11, 2),
  maxPricePaise: 2000,
  status: 'open',
  createdAt: DateTime(2026, 10, 23, 16, 45),
  offers: [
    RfqOffer(
      id: 'off-1',
      rfqId: 'rfq-200',
      farmerLabel: 'Ramesh Reddy',
      quantity: 100,
      unit: 'kg',
      pricePaise: 1800, // ₹18/kg
      status: 'pending',
      createdAt: DateTime(2026, 10, 24, 7, 30),
    ),
  ],
);

final _shipment = Shipment(
  id: 'shp-1',
  status: 'in_transit',
  distanceKm: 42.5,
  originLabel: 'Siddipet Collection Centre',
  destinationLabel: 'Hyderabad',
  driverId: 'u-driver',
  stops: [
    ShipmentStop(
      id: 'st-1',
      sequence: 1,
      kind: 'pickup',
      label: 'Ramesh Reddy',
      status: 'completed',
      address: 'Collection Centre, Siddipet',
      orderId: 'ord-2001',
    ),
    ShipmentStop(
      id: 'st-2',
      sequence: 2,
      kind: 'pickup',
      label: 'FPO Collection Centre',
      status: 'pending',
      address: 'Siddipet Mandi Yard',
      orderId: 'ord-2002',
    ),
    ShipmentStop(
      id: 'st-3',
      sequence: 3,
      kind: 'delivery',
      label: 'Megha Traders',
      status: 'pending',
      address: '12-4-90, Begum Bazar, Hyderabad',
      orderId: 'ord-2001',
    ),
  ],
  crates: [
    ShipmentCrate(code: 'KS-CRATE-0001', orderId: 'ord-2001', status: 'ready'),
    ShipmentCrate(code: 'KS-CRATE-0002', orderId: 'ord-2002', status: 'ready'),
  ],
  createdAt: DateTime(2026, 10, 25, 8, 0),
);

final _drivers = [
  DriverOption(
    id: 'u-driver',
    name: 'Suresh Yadav',
    phone: '+919876543233',
    status: 'active',
  ),
  DriverOption(
    id: 'u-driver-2',
    name: 'Mohan Rao',
    phone: '+919876543255',
    status: 'active',
  ),
];

final _orderPayment = OrderPayment(
  orderId: 'ord-1001',
  orderStatus: 'confirmed',
  paymentStatus: 'PENDING',
  subtotalPaise: 45000,
  deliveryFeePaise: 4000,
  platformFeePaise: 900,
  totalPaise: 49900, // ₹499
  currency: 'INR',
  transactions: const [],
  ledgerEntries: const [],
);

final _marketRecommendation = PriceRecommendation(
  id: 'rec-1',
  commodityId: 'c-tomato',
  commodityName: 'Tomato',
  district: 'Rangareddy',
  recommendedMinPaise: 1800,
  recommendedModalPaise: 2000,
  recommendedMaxPaise: 2400,
  recommendedModalPerKgPaise: null,
  unit: 'kg',
  benchmarkMarket: 'Warangal',
  benchmarkObservedOn: DateTime(2026, 10, 20),
  benchmarkSource: 'agmarknet',
  confidence: 'high',
  explanation: 'Median of 12 recent wholesale observations near Warangal.',
  modelRun: ModelRun(
    id: 'run-1',
    modelType: 'price_recommendation',
    modelVersion: 'median-v1',
    ranAt: DateTime(2026, 10, 24, 6, 30),
    notes: null,
  ),
);

// ---------------------------------------------------------------------------
// Stubs for the API clients that are really called while rendering.
// ---------------------------------------------------------------------------

class _AuthApiStub implements AuthApi {
  @override
  Future<List<String>> welcomeDemoCodes() async => AppConfig.demoCodes;

  @override
  Future<OtpRequestResult> requestOtp(String phone) => _unimplemented();

  @override
  Future<OtpVerifyResult> verifyOtp(String phone, String code) =>
      _unimplemented();

  @override
  Future<(String, AppUser)> register({
    required String registrationToken,
    required String fullName,
    required String role,
    required String preferredLanguage,
  }) =>
      _unimplemented();

  @override
  Future<(String, AppUser)> demoLogin(String demoCode) => _unimplemented();

  @override
  Future<AppUser> me() => _unimplemented();

  Never _unimplemented() => throw UnimplementedError('Not used in goldens.');
}

class _VoiceApiStub implements VoiceApi {
  @override
  Future<VoiceStatus> status() async => VoiceStatus(
        simulated: true,
        provider: 'simulated',
        samplePhrases: const [_phonePhrase],
      );

  @override
  Future<VoiceDraft> draft({required String text, required String language}) =>
      Future.value(
        VoiceDraft(
          transcript: text,
          provider: 'simulated',
          simulated: true,
          // quantity / unit / price get the orange "please check" borders;
          // the commodity matched the catalogue, so it is not flagged.
          fieldsNeedingConfirmation: const ['quantity', 'unit', 'price'],
          extracted: VoiceExtracted(
            commodity: 'టమాటా',
            quantity: 5,
            unit: 'quintal',
            pricePaise: 200000, // ₹2,000 per quintal
            availableFrom: null,
          ),
        ),
      );
}

class _MarketApiStub implements MarketApi {
  @override
  Future<PriceRecommendation> recommendation({
    required String commodityId,
    String? district,
  }) =>
      Future.value(_marketRecommendation);
}

/// Session stub: pretends the given user is signed in (or nobody).
class _FixedAuthController extends AuthController {
  _FixedAuthController(this._user);

  final AppUser? _user;

  @override
  AuthState build() => _user == null
      ? const AuthUnauthenticated()
      : AuthAuthenticated(_user);
}

// ---------------------------------------------------------------------------
// Provider override bundles — every provider any tab of a shell watches is
// resolved to data so no skeleton animation keeps pumpAndSettle spinning.
// ---------------------------------------------------------------------------

List<Override> _farmerData() => [
      marketplace.myListingsProvider.overrideWith((ref) async => _listings),
      marketplace.farmerOrdersProvider
          .overrideWith((ref) async => _farmerOrderPage),
      rfq.openRfqsProvider.overrideWith((ref) async => [_openDemandRfq]),
      marketplace.commoditiesProvider
          .overrideWith((ref) async => _commodities),
    ];

List<Override> _buyerData() => [
      marketplace.browseListingsProvider
          .overrideWith((ref, search) async => ListingPage(
                items: _listings.where((l) => l.status == 'active').toList(),
                total: 2,
              )),
      marketplace.cartProvider.overrideWith((ref) async => _cart),
      marketplace.buyerOrdersProvider
          .overrideWith((ref) async => OrderPage(items: [], total: 0)),
      marketplace.commoditiesProvider
          .overrideWith((ref) async => _commodities),
    ];

List<Override> _fpoData() => [
      marketplace.farmerOrdersProvider
          .overrideWith((ref) async => _farmerOrderPage),
      marketplace.confirmedFarmerOrdersProvider
          .overrideWith((ref) async => _confirmedOrderPage),
      shipments.driversProvider.overrideWith((ref) async => _drivers),
      marketplace.commoditiesProvider
          .overrideWith((ref) async => _commodities),
    ];

// ---------------------------------------------------------------------------
// Goldens.
// ---------------------------------------------------------------------------

void main() {
  // The locale controller reads SharedPreferences on boot; mock it like
  // widget_test.dart does.
  SharedPreferences.setMockInitialValues({});

  // Widget tests do not preload pubspec fonts — without this every label is
  // laid out with the box-shaped test font, which overflows the real layouts.
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    await TestWidgetsFlutterBinding.instance.runAsync(() async {
      const fonts = {
        'Inter': 'assets/fonts/Inter.ttf',
        'NotoSans': 'assets/fonts/NotoSans.ttf',
        'NotoSansTelugu': 'assets/fonts/NotoSansTelugu.ttf',
      };
      for (final entry in fonts.entries) {
        final bytes = await rootBundle.load(entry.value);
        final loader = FontLoader(entry.key)..addFont(Future.value(bytes));
        await loader.load();
      }
      // The framework icon font ships in the test asset bundle; without it
      // every Material icon renders as a tofu box.
      try {
        final icons = await rootBundle.load('fonts/MaterialIcons-Regular.otf');
        final loader = FontLoader('MaterialIcons')
          ..addFont(Future.value(icons));
        await loader.load();
      } catch (_) {
        // Icons stay as boxes if the framework font is unavailable.
      }
    });
  });

  testWidgets('01-welcome — login entry with the demo-code buttons',
      (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider
          .overrideWith(() => _FixedAuthController(null)), // signed out
      authApiProvider.overrideWithValue(_AuthApiStub()),
    ]);

    // Real navigation: welcome screen → farmer login, which hosts the
    // one-tap demo-code buttons (farmer1…admin1).
    await tester.tap(find.byIcon(Icons.agriculture_rounded).first);
    await tester.pumpAndSettle();

    expect(find.byType(WelcomeScreen), findsNothing);
    expect(find.text('Sign in as Farmer'), findsOneWidget);

    await _capture(tester, '01-welcome.png');
  });

  testWidgets('02-farmer-dashboard — stats, Speak to Sell, open demand',
      (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider.overrideWith(() => _FixedAuthController(_farmer)),
      ..._farmerData(),
    ]);

    expect(find.text('Speak to Sell'), findsOneWidget);
    expect(find.textContaining('up to ₹18/kg'), findsOneWidget);

    await _capture(tester, '02-farmer-dashboard.png');
  });

  testWidgets('03-voice-listing — demo banner, chips, confirmation form',
      (tester) async {
    _usePhoneSurface(tester);
    await _pump(
      tester,
      const _PlainApp(home: VoiceListingScreen()),
      overrides: [
        voice.voiceStatusProvider.overrideWith((ref) async => VoiceStatus(
              simulated: true,
              provider: 'simulated',
              samplePhrases: const [_phonePhrase],
            )),
        marketplace.commoditiesProvider
            .overrideWith((ref) async => _commodities),
        voice.voiceApiProvider.overrideWithValue(_VoiceApiStub()),
      ],
    );
    await tester.pumpAndSettle();

    // Speak (type) the demo phrase and draft the listing — the real flow.
    // The first draft cannot resolve the crop from the catalogue yet (the
    // autoDispose commodities provider only becomes active once the
    // confirmation form watches it), so draft a second time — as a real
    // user tapping the button again would — to fill the crop too.
    await tester.enterText(find.byType(TextField).first, _phonePhrase);
    await tester.tap(find.text('Draft my listing'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Draft my listing'));
    await tester.pumpAndSettle();

    expect(find.text('Simulated (demo)'), findsOneWidget);
    expect(find.textContaining('please check'), findsWidgets);
    expect(find.textContaining('Tomato'), findsWidgets);

    await _capture(tester, '03-voice-listing.png');
  });

  testWidgets('04-market-prices — recommendation card for tomato',
      (tester) async {
    _usePhoneSurface(tester);
    await _pump(
      tester,
      _PlainApp(
        home: Builder(
          builder: (context) => Scaffold(
            appBar:
                AppBar(title: Text(AppLocalizations.of(context).marketTitle)),
            body: const MarketScreen(),
          ),
        ),
      ),
      overrides: [
        marketplace.commoditiesProvider
            .overrideWith((ref) async => _commodities),
        market.marketApiProvider.overrideWithValue(_MarketApiStub()),
      ],
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, 'Warangal');
    await tester.tap(find.text('Get price'));
    await tester.pumpAndSettle();

    expect(find.text('₹18 – 20 – 24'), findsOneWidget);
    expect(find.text('high'), findsOneWidget);
    expect(find.textContaining('median-v1'), findsOneWidget);

    await _capture(tester, '04-market-prices.png');
  });

  testWidgets('05-buyer-home — shop with produce cards', (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider.overrideWith(() => _FixedAuthController(_buyer)),
      ..._buyerData(),
    ]);

    expect(find.text('Tomato'), findsWidgets);
    expect(find.text('₹18/kg'), findsOneWidget);

    await _capture(tester, '05-buyer-home.png');
  });

  testWidgets('06-cart — two items, totals, checkout', (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider.overrideWith(() => _FixedAuthController(_buyer)),
      ..._buyerData(),
    ]);

    await _openTab(tester, 'Cart');

    expect(find.text('₹670'), findsOneWidget);
    expect(find.text('Checkout'), findsOneWidget);

    await _capture(tester, '06-cart.png');
  });

  testWidgets('07-payment — sandbox breakdown and actions', (tester) async {
    _usePhoneSurface(tester);
    await _pump(
      tester,
      const _PlainApp(home: PaymentScreen(orderId: 'ord-1001')),
      overrides: [
        orderPaymentProvider
            .overrideWith((ref, orderId) async => _orderPayment),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('SANDBOX — no real money moves'), findsOneWidget);
    expect(find.text('Total'), findsOneWidget);
    expect(find.text('Initiate'), findsOneWidget);

    await _capture(tester, '07-payment.png');
  });

  testWidgets('08-driver-shipments — run card with ordered stops',
      (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider.overrideWith(() => _FixedAuthController(_driver)),
      shipments.myShipmentsProvider.overrideWith((ref) async => [_shipment]),
      shipments.shipmentDetailProvider
          .overrideWith((ref, id) async => _shipment),
    ]);

    // Real navigation: trips tab → tap the run card → ordered stops view.
    await tester.tap(find.byType(ShipmentCard).first);
    await tester.pumpAndSettle();

    expect(find.text('PICKUP'), findsWidgets);
    expect(find.text('DELIVERY'), findsOneWidget);

    await _capture(tester, '08-driver-shipments.png');
  });

  testWidgets('09-fpo-dispatch — two confirmed orders selected, driver set',
      (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider
          .overrideWith(() => _FixedAuthController(_fpoOperator)),
      ..._fpoData(),
    ]);

    await _openTab(tester, 'Dispatch');

    // Select both confirmed orders, as an operator would before a run.
    await tester.tap(find.byType(Checkbox).at(0));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(Checkbox).at(1));
    await tester.pumpAndSettle();

    // Pick the driver from the real dropdown.
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Suresh Yadav').last);
    await tester.pumpAndSettle();

    expect(find.textContaining('Suresh Yadav'), findsOneWidget);

    await _capture(tester, '09-fpo-dispatch.png');
  });

  testWidgets('10-business-rfq — create form plus an offer to accept',
      (tester) async {
    _usePhoneSurface(tester);
    await _pumpKhetSeApp(tester, [
      authControllerProvider
          .overrideWith(() => _FixedAuthController(_business)),
      ..._buyerData(),
      rfq.myRfqsProvider.overrideWith((ref) async => [_myRfq]),
    ]);

    await _openTab(tester, 'Demand');

    expect(find.text('Ramesh Reddy'), findsOneWidget);
    expect(find.textContaining('₹18'), findsWidgets);

    await _capture(tester, '10-business-rfq.png');
  });
}
