/// Cart — mirrors `CartPublic`/`CartItemPublic` in `backend/app/schemas/cart.py`.
class Cart {
  Cart({required this.id, required this.items, required this.subtotalPaise});

  final String id;
  final List<CartItem> items;
  final int subtotalPaise;

  factory Cart.fromJson(Map<String, dynamic> json) => Cart(
        id: json['id'] as String,
        items: (json['items'] as List? ?? [])
            .map((e) => CartItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        subtotalPaise: (json['subtotal_paise'] ?? 0) as int,
      );

  bool get isEmpty => items.isEmpty;
}

class CartItem {
  CartItem({
    required this.id,
    required this.listingId,
    required this.quantity,
    required this.unitPricePaise,
    required this.lineTotalPaise,
    required this.commodityName,
    required this.farmerDistrict,
    required this.listingStatus,
  });

  final String id;
  final String listingId;
  final double quantity;
  final int unitPricePaise;
  final int lineTotalPaise;
  final String? commodityName;
  final String? farmerDistrict;
  final String? listingStatus;

  factory CartItem.fromJson(Map<String, dynamic> json) => CartItem(
        id: json['id'] as String,
        listingId: json['listing_id'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        unitPricePaise: (json['unit_price_paise'] ?? 0) as int,
        lineTotalPaise: (json['line_total_paise'] ?? 0) as int,
        commodityName: json['commodity_name'] as String?,
        farmerDistrict: json['farmer_district'] as String?,
        listingStatus: json['listing_status'] as String?,
      );

  String get title => commodityName ?? 'Produce';
}
