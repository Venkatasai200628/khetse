import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import 'cart_api.dart';
import 'cart_model.dart';
import 'listing_api.dart';
import 'listing_model.dart';
import 'order_api.dart';
import 'order_model.dart';

final listingApiProvider =
    Provider<ListingApi>((ref) => ListingApi(ref.watch(apiClientProvider)));

final orderApiProvider =
    Provider<OrderApi>((ref) => OrderApi(ref.watch(apiClientProvider)));

final cartApiProvider =
    Provider<CartApi>((ref) => CartApi(ref.watch(apiClientProvider)));

/// Farmer's own listings — GET /listings/mine.
final myListingsProvider =
    FutureProvider.autoDispose<List<Listing>>((ref) {
  final api = ref.watch(listingApiProvider);
  return api.mine();
});

/// Buyer browse — GET /listings?search=...
final browseListingsProvider =
    FutureProvider.autoDispose.family<ListingPage, String?>((ref, search) {
  final api = ref.watch(listingApiProvider);
  return api.browse(search: search, pageSize: 50);
});

/// Commodity catalogue — GET /commodities.
final commoditiesProvider =
    FutureProvider.autoDispose<List<Commodity>>((ref) {
  final api = ref.watch(listingApiProvider);
  return api.commodities();
});

/// Orders for the signed-in farmer / FPO — GET /orders/farmer.
final farmerOrdersProvider =
    FutureProvider.autoDispose<OrderPage>((ref) {
  final api = ref.watch(orderApiProvider);
  return api.farmerOrders(pageSize: 50);
});

/// Buyer orders — GET /orders/mine.
final buyerOrdersProvider = FutureProvider.autoDispose<OrderPage>((ref) {
  final api = ref.watch(orderApiProvider);
  return api.mine(pageSize: 50);
});

/// Single order — GET /orders/{id}.
final orderDetailProvider =
    FutureProvider.autoDispose.family<Order, String>((ref, id) {
  final api = ref.watch(orderApiProvider);
  return api.get(id);
});

/// Single listing — GET /listings/{id}.
final listingDetailProvider =
    FutureProvider.autoDispose.family<Listing, String>((ref, id) {
  final api = ref.watch(listingApiProvider);
  return api.get(id);
});

/// Cart — GET /cart.
final cartProvider = FutureProvider.autoDispose<Cart>((ref) {
  final api = ref.watch(cartApiProvider);
  return api.get();
});

/// Marketplace overview for the admin dashboard — GET /listings (page 1,
/// up to 100 rows); counts are computed from real rows, nothing invented.
final adminMarketplaceProvider =
    FutureProvider.autoDispose<ListingPage>((ref) {
  final api = ref.watch(listingApiProvider);
  return api.browse(pageSize: 100);
});
