import 'package:flutter_test/flutter_test.dart';

import 'package:khetse/core/utils/money.dart';
import 'package:khetse/features/market/data/market_model.dart';
import 'package:khetse/features/rfq/data/rfq_model.dart';
import 'package:khetse/features/shipments/data/shipment_model.dart';
import 'package:khetse/features/voice/data/voice_model.dart';

void main() {
  group('money helpers', () {
    test('formatPaise uses Indian grouping and drops .00', () {
      expect(formatPaise(5000), '₹50');
      expect(formatPaise(123456), '₹1,234.56');
      expect(formatPaise(12345678), '₹1,23,456.78');
      expect(formatPaise(220000, withSymbol: false), '2,200');
    });

    test('rupeesToPaise rounds safely', () {
      expect(rupeesToPaise(20), 2000);
      expect(rupeesToPaise(19.99), 1999);
    });
  });

  group('PriceRecommendation', () {
    test('parses the market API contract incl. quintal unit', () {
      final rec = PriceRecommendation.fromJson({
        'id': 'rec1',
        'commodity_id': 'c1',
        'commodity_name': 'Tomato',
        'district': 'Rangareddy',
        'recommended_min_paise': 100000,
        'recommended_modal_paise': 220000,
        'recommended_max_paise': 300000,
        'recommended_modal_per_kg_paise': 2200,
        'unit': 'quintal',
        'benchmark_market': 'Bowenpally Market',
        'benchmark_observed_on': '2026-10-20',
        'benchmark_source': 'agmarknet',
        'confidence': 'high',
        'explanation': 'Based on 12 recent observations.',
        'model_run': {
          'id': 'run1',
          'model_type': 'price_recommendation',
          'model_version': 'median-v1',
          'ran_at': '2026-10-24T06:30:00',
        },
      });

      expect(rec.commodityName, 'Tomato');
      expect(rec.isQuintal, isTrue);
      expect(rec.rangeLabel, '1,000 – 2,200 – 3,000');
      expect(rec.confidence, 'high');
      expect(rec.provenanceLabel, contains('median-v1'));
      expect(rec.provenanceLabel, contains('ran'));
      expect(rec.modelRun.ranAt.year, 2026);
      expect(rec.benchmarkMarket, 'Bowenpally Market');
    });

    test('tolerates missing optional range fields', () {
      final rec = PriceRecommendation.fromJson({
        'id': 'rec2',
        'commodity_id': 'c1',
        'commodity_name': 'Tomato',
        'recommended_modal_paise': 4000,
        'confidence': 'low',
        'model_run': {'id': 'run2', 'model_version': 'median-v1'},
      });

      expect(rec.recommendedMinPaise, isNull);
      expect(rec.rangeLabel, '— – 40 – —');
      expect(rec.isQuintal, isFalse);
      expect(rec.benchmarkMarket, isNull);
    });
  });

  group('VoiceDraft', () {
    test('parses transcript, extraction and confirmation fields', () {
      final draft = VoiceDraft.fromJson({
        'transcript': '5 క్వింటాల్ టమాటా రూ 2000',
        'provider': 'simulated',
        'simulated': true,
        'fields_needing_confirmation': ['quantity', 'price'],
        'extracted': {
          'commodity': 'tomato',
          'quantity': 5,
          'unit': 'quintal',
          'price_paise': 200000,
        },
      });

      expect(draft.transcript, contains('టమాటా'));
      expect(draft.providerLabel(), 'Simulated (demo)');
      expect(draft.needsConfirmation('quantity'), isTrue);
      expect(draft.needsConfirmation('PRICE'), isTrue);
      expect(draft.needsConfirmation('unit'), isFalse);
      expect(draft.extracted.quantity, 5.0);
      expect(draft.extracted.pricePaise, 200000);
    });

    test('labels the real provider honestly', () {
      final draft = VoiceDraft.fromJson({
        'transcript': '10 kg tomato at 20 rupees per kg',
        'provider': 'bhashini',
        'simulated': false,
        'fields_needing_confirmation': [],
        'extracted': {'commodity': 'tomato', 'quantity': 10, 'unit': 'kg'},
      });

      expect(draft.providerLabel(), 'Bhashini');
      expect(draft.needsConfirmation('commodity'), isFalse);
    });
  });

  group('Shipment', () {
    test('parses stops and orders them by sequence', () {
      final shipment = Shipment.fromJson({
        'id': 's1',
        'status': 'ready',
        'distance_km': 42.5,
        'origin_label': 'Collection centre',
        'destination_label': 'Buyer drop point',
        'stops': [
          {
            'id': 'st2',
            'sequence': 2,
            'kind': 'delivery',
            'label': 'Order #1023 — A. Reddy',
            'status': 'pending',
          },
          {
            'id': 'st1',
            'sequence': 1,
            'kind': 'pickup',
            'label': 'FPO collection centre',
            'status': 'completed',
          },
        ],
        'crates': [
          {'code': 'CR-1001'},
          {'code': 'CR-1002', 'order_id': 'o1'},
        ],
        'created_at': '2026-10-24T09:00:00',
      });

      expect(shipment.stopCount, 2);
      expect(shipment.stops.first.id, 'st1');
      expect(shipment.stops.first.isPickup, isTrue);
      expect(shipment.stops.last.isPickup, isFalse);
      expect(shipment.pendingStopCount, 1);
      expect(shipment.distanceLabel, '42.5 km');
      expect(shipment.routeLabel, 'Collection centre → Buyer drop point');
      expect(shipment.canStart, isTrue);
      expect(shipment.crates.map((c) => c.code), ['CR-1001', 'CR-1002']);
    });

    test('in-transit runs cannot be started', () {
      final shipment = Shipment.fromJson({
        'id': 's2',
        'status': 'in_transit',
        'stops': [],
      });
      expect(shipment.canStart, isFalse);
      expect(shipment.routeLabel, 'Delivery run');
    });
  });

  group('DriverOption', () {
    test('falls back to a truncated id when the name is missing', () {
      final named = DriverOption.fromJson(
          {'id': 'd1', 'full_name': 'Ramesh K', 'phone': '9999999999'});
      expect(named.label, 'Ramesh K');

      final unnamed = DriverOption.fromJson(
          {'id': '12345678-90ab-cdef', 'full_name': null});
      expect(unnamed.label, startsWith('Driver …'));
    });
  });

  group('Rfq', () {
    test('parses an RFQ with its offers', () {
      final rfq = Rfq.fromJson({
        'id': 'r1',
        'buyer_id': 'b1',
        'buyer_label': 'Hotel Green Leaf',
        'commodity_id': 'c1',
        'commodity_name': 'Tomato',
        'quantity': 200,
        'unit': 'kg',
        'needed_by': '2026-11-01',
        'max_price_paise': 2200,
        'status': 'open',
        'created_at': '2026-10-24T10:00:00',
        'offers': [
          {
            'id': 'of1',
            'rfq_id': 'r1',
            'farmer_label': 'Farmer #12',
            'price_paise': 2050,
            'quantity': 200,
            'unit': 'kg',
            'status': 'pending',
          },
        ],
      });

      expect(rfq.title, 'Tomato');
      expect(rfq.quantityLabel, '200 kg');
      expect(rfq.maxPriceLabel, 'up to ₹22/kg');
      expect(rfq.isOpen, isTrue);
      expect(rfq.offers, hasLength(1));
      expect(rfq.offers.first.priceLabel, '₹20.50/kg');
      expect(rfq.offers.first.isPending, isTrue);
      expect(rfq.neededByLabel, '1 Nov 2026');
    });

    test('offer acceptance flag maps from status', () {
      final offer = RfqOffer.fromJson(
          {'id': 'of2', 'price_paise': 2000, 'status': 'accepted'});
      expect(offer.isAccepted, isTrue);
      expect(offer.isPending, isFalse);
    });
  });

  // Regression coverage for the GUI-testing round (2026-10-25): the backend
  // payload keys differ from what the models originally read.
  group('shipment payload regressions', () {
    test('DriverOption accepts the user_id key /drivers actually sends', () {
      final driver = DriverOption.fromJson({
        'user_id': 'ef546cc0-8c86-42cc',
        'full_name': 'Suresh Yadav',
        'is_available': true,
        'vehicle': null,
      });
      expect(driver.id, 'ef546cc0-8c86-42cc');
      expect(driver.label, 'Suresh Yadav');
    });

  test('ShipmentStop reads stop_type (pickup stays pickup)', () {
    final stop = ShipmentStop.fromJson({
      'id': 's1',
      'stop_type': 'pickup',
      'sequence': 1,
      'status': 'pending',
      'label': 'Kothur, Ranga Reddy',
      'order_id': null,
    });
    expect(stop.isPickup, isTrue);
    final drop = ShipmentStop.fromJson({
      'id': 's2',
      'stop_type': 'delivery',
      'sequence': 2,
      'status': 'pending',
      'label': 'Buyer · Ranga Reddy',
    });
    expect(drop.isPickup, isFalse);
  });

  test('Shipment reads route_distance_km and canStart covers assigned', () {
    final run = Shipment.fromJson({
      'id': 'sh1',
      'status': 'assigned',
      'route_distance_km': 12.5,
      'stops': [
        {
          'id': 's1',
          'stop_type': 'pickup',
          'sequence': 1,
          'status': 'pending',
          'label': 'Farm',
        }
      ],
    });
    expect(run.distanceLabel, '12.5 km');
    expect(run.canStart, isTrue);
    expect(run.stops.first.isPickup, isTrue);
  });
});
}
