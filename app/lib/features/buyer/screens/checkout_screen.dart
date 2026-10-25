import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../auth/controllers/auth_controller.dart';
import '../../marketplace/data/providers.dart';

/// Checkout — collects the delivery address and POSTs /orders/checkout.
/// Fees are computed server-side; this screen only shows the cart subtotal
/// plus a note, never an invented total.
class CheckoutScreen extends ConsumerStatefulWidget {
  const CheckoutScreen({super.key});

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  final _districtController = TextEditingController();
  final _notesController = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final user = ref.read(currentUserProvider);
    _nameController.text = user?.displayName ?? '';
    _phoneController.text = user?.phone.replaceFirst('+91', '') ?? '';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    _districtController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _placeOrder() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final order = await ref.read(orderApiProvider).checkout(
            deliveryName: _nameController.text.trim(),
            deliveryPhone: '+91${_phoneController.text.trim().replaceAll(RegExp(r'\D'), '')}',
            deliveryAddress: _addressController.text.trim(),
            deliveryDistrict: _districtController.text.trim(),
            notes: _notesController.text.trim(),
          );
      ref.invalidate(cartProvider);
      ref.invalidate(buyerOrdersProvider);
      if (mounted) {
        context.pop();
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Order placed — awaiting farmer confirmation')));
        context.push('/order/${order.id}');
      }
    } catch (e) {
      setState(() {
        _busy = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final cartAsync = ref.watch(cartProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.checkout)),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                cartAsync.when(
                  loading: () => const SkeletonBox(height: 70, radius: 16),
                  error: (e, _) => ErrorView(
                    message: e.toString(),
                    onRetry: () => ref.invalidate(cartProvider),
                    compact: true,
                  ),
                  data: (cart) => Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${cart.items.length} ${cart.items.length == 1 ? 'item' : 'items'} · ${t.subtotal}',
                            style: const TextStyle(
                                fontSize: 14.5, fontWeight: FontWeight.w600),
                          ),
                        ),
                        Text(
                          formatPaise(cart.subtotalPaise),
                          style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primary),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  t.deliveryFeesNote,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 18),
                TextFormField(
                  controller: _nameController,
                  decoration: InputDecoration(labelText: t.fullName),
                  validator: (v) =>
                      (v?.trim().length ?? 0) < 2 ? t.enterName : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  maxLength: 10,
                  decoration: InputDecoration(
                    labelText: t.phoneNumber,
                    prefixText: '+91 ',
                    counterText: '',
                  ),
                  validator: (v) => (v?.trim().length ?? 0) < 10
                      ? t.enterPhone
                      : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _addressController,
                  maxLines: 2,
                  decoration: InputDecoration(
                    labelText: t.address,
                    alignLabelWithHint: true,
                  ),
                  validator: (v) =>
                      (v?.trim().length ?? 0) < 6 ? t.enterAddress : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _districtController,
                  decoration: InputDecoration(labelText: t.district),
                  validator: (v) =>
                      (v?.trim().length ?? 0) < 2 ? t.enterDistrict : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _notesController,
                  maxLines: 2,
                  decoration: InputDecoration(
                    labelText: t.notesOptional,
                    alignLabelWithHint: true,
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 18),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFDECEA),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(_error!,
                        style: const TextStyle(
                            color: AppColors.danger,
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600)),
                  ),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _busy ? null : _placeOrder,
                  child: _busy
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.4, color: Colors.white),
                        )
                      : Text(t.placeOrder),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
