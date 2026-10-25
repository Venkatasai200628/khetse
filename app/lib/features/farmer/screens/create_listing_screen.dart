import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/listing_model.dart';
import '../../marketplace/data/providers.dart';

const _units = ['kg', 'quintal', 'tonne', 'dozen', 'piece', 'litre', 'bunch'];
const _grades = ['ungraded', 'A', 'B', 'C'];

/// New listing form — POST /listings with integer-paise prices.
class CreateListingScreen extends ConsumerStatefulWidget {
  const CreateListingScreen({super.key});

  @override
  ConsumerState<CreateListingScreen> createState() =>
      _CreateListingScreenState();
}

class _CreateListingScreenState extends ConsumerState<CreateListingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();
  final _descriptionController = TextEditingController();

  String? _commodityError;
  Commodity? _commodity;
  String _unit = 'kg';
  String _grade = 'ungraded';
  DateTime? _harvestDate;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _quantityController.dispose();
    _priceController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _pickHarvestDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: now.subtract(const Duration(days: 30)),
      lastDate: now,
    );
    if (picked != null) setState(() => _harvestDate = picked);
  }

  Future<void> _submit() async {
    final quantity = double.tryParse(_quantityController.text.trim());
    final priceRupees = double.tryParse(_priceController.text.trim());

    String? quantityError;
    String? priceError;
    if (_commodity == null) {
      setState(() => _commodityError =
          'Choose a crop (load the catalogue with Retry if it failed).');
      return;
    }
    if (quantity == null || quantity <= 0) quantityError = 'Enter the quantity you have.';
    if (priceRupees == null || priceRupees <= 0) {
      priceError = 'Enter your price per $_unit.';
    }

    final validated = _formKey.currentState?.validate() ?? false;
    if (!validated || quantityError != null || priceError != null) {
      setState(() {
        _error = quantityError ?? priceError;
      });
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });

    // Min price floor: 90% of the listed price — the farmer can refine it
    // later; the backend requires min <= listed.
    final listedPaise = rupeesToPaise(priceRupees!);
    final minPaise = (listedPaise * 0.9).round();

    try {
      await ref.read(listingApiProvider).create(
            commodityId: _commodity!.id,
            quantityTotal: quantity!,
            unit: _unit,
            minPricePaise: minPaise,
            listedPricePaise: listedPaise,
            qualityGrade: _grade,
            description: _descriptionController.text.trim(),
            harvestDate: _harvestDate,
          );
      ref.invalidate(myListingsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Listing published')));
        context.pop();
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
    final commoditiesAsync = ref.watch(commoditiesProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.createListing)),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  t.createListingSubtitle,
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 22),
                commoditiesAsync.when(
                  loading: () =>
                      const SkeletonBox(height: 60, radius: 14),
                  error: (e, _) => ErrorView(
                    message: '${t.commodityLoadFailed}: $e',
                    onRetry: () => ref.invalidate(commoditiesProvider),
                    compact: true,
                  ),
                  data: (items) {
                    _commodity ??= items.isNotEmpty ? items.first : null;
                    return DropdownButtonHideUnderline(
                      child: DropdownButtonFormField<Commodity>(
                        initialValue: _commodity,
                        items: [
                          for (final c in items)
                            DropdownMenuItem(
                              value: c,
                              child: Text(c.nameEn +
                                  (c.nameTe != null ? ' · ${c.nameTe}' : '')),
                            ),
                        ],
                        onChanged: (c) =>
                            setState(() => _commodity = c),
                        decoration: InputDecoration(
                          labelText: t.crop,
                          errorText: _commodityError,
                        ),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 16),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextFormField(
                        controller: _quantityController,
                        keyboardType:
                            const TextInputType.numberWithOptions(decimal: true),
                        decoration: InputDecoration(labelText: t.quantity),
                        validator: (v) {
                          final n = double.tryParse(v?.trim() ?? '');
                          if (n == null || n <= 0) return t.enterQuantity;
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: DropdownButtonHideUnderline(
                        child: DropdownButtonFormField<String>(
                          initialValue: _unit,
                          items: [
                            for (final u in _units)
                              DropdownMenuItem(value: u, child: Text(u)),
                          ],
                          onChanged: (u) => setState(() => _unit = u ?? 'kg'),
                          decoration: InputDecoration(labelText: t.unitLabel),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _priceController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: '${t.pricePer} $_unit (₹)',
                    hintText: 'e.g. 24',
                    helperText: t.priceHelper,
                  ),
                  validator: (v) {
                    final n = double.tryParse(v?.trim() ?? '');
                    if (n == null || n <= 0) return t.enterPrice;
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonHideUnderline(
                  child: DropdownButtonFormField<String>(
                    initialValue: _grade,
                    items: [
                      for (final g in _grades)
                        DropdownMenuItem(value: g, child: Text(g)),
                    ],
                    onChanged: (g) => setState(() => _grade = g ?? 'ungraded'),
                    decoration: InputDecoration(labelText: t.qualityGrade),
                  ),
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: _pickHarvestDate,
                  borderRadius: BorderRadius.circular(14),
                  child: InputDecorator(
                    decoration: InputDecoration(
                      labelText: t.harvestDate,
                      suffixIcon: const Icon(Icons.calendar_month_rounded,
                          size: 20),
                    ),
                    child: Text(
                      _harvestDate == null
                          ? t.today
                          : '${_harvestDate!.day}/${_harvestDate!.month}/${_harvestDate!.year}',
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _descriptionController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: t.descriptionOptional,
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
                const SizedBox(height: 26),
                FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: _busy
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.4, color: Colors.white),
                        )
                      : Text(t.publish),
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
