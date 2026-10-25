import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../../l10n/app_localizations.dart';
import '../../marketplace/data/listing_model.dart';
import '../../marketplace/data/providers.dart';
import '../data/providers.dart';
import '../data/rfq_model.dart';

const _units = ['kg', 'quintal', 'tonne', 'dozen', 'piece', 'litre', 'bunch'];

/// Business demand (RFQ) — post what you need and quote against the
/// offers farmers send back. Accepting an offer creates the order and
/// jumps straight into its existing payment flow.
class BusinessRfqTab extends ConsumerStatefulWidget {
  const BusinessRfqTab({super.key});

  @override
  ConsumerState<BusinessRfqTab> createState() => _BusinessRfqTabState();
}

class _BusinessRfqTabState extends ConsumerState<BusinessRfqTab> {
  final _formKey = GlobalKey<FormState>();
  final _quantityController = TextEditingController();
  final _maxPriceController = TextEditingController();

  Commodity? _commodity;
  String _unit = 'kg';
  DateTime? _neededBy;
  bool _posting = false;
  String _acceptingOfferId = '';

  @override
  void dispose() {
    _quantityController.dispose();
    _maxPriceController.dispose();
    super.dispose();
  }

  Future<void> _pickNeededBy() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _neededBy ?? now.add(const Duration(days: 3)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 180)),
    );
    if (picked != null) setState(() => _neededBy = picked);
  }

  Future<void> _post() async {
    final validated = _formKey.currentState?.validate() ?? false;
    if (!validated || _commodity == null) return;
    final maxRupees = double.tryParse(_maxPriceController.text.trim());
    final quantity = double.tryParse(_quantityController.text.trim());
    if (maxRupees == null || quantity == null) return;

    setState(() => _posting = true);
    try {
      await ref.read(rfqApiProvider).create(
            commodityId: _commodity!.id,
            quantity: quantity,
            unit: _unit,
            maxPricePaise: rupeesToPaise(maxRupees),
            neededBy: _neededBy,
          );
      ref.invalidate(myRfqsProvider);
      if (mounted) {
        setState(() {
          _quantityController.clear();
          _maxPriceController.clear();
          _neededBy = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context).rfqPosted)));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _posting = false);
    }
  }

  Future<void> _accept(RfqOffer offer) async {
    setState(() => _acceptingOfferId = offer.id);
    try {
      final orderId = await ref.read(rfqApiProvider).acceptOffer(offer.id);
      ref.invalidate(myRfqsProvider);
      if (mounted) {
        // Straight into the existing payment flow for the new order.
        context.push('/order/$orderId/pay');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _acceptingOfferId = '');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final rfqsAsync = ref.watch(myRfqsProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            t.rfqTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.rfqSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          _createForm(context),
          const SizedBox(height: 24),
          Text(
            t.rfqMyRequests,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 12),
          rfqsAsync.when(
            loading: () => const SkeletonList(itemCount: 3, itemHeight: 120),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(myRfqsProvider),
              compact: true,
            ),
            data: (rfqs) {
              if (rfqs.isEmpty) {
                return SizedBox(
                  height: 300,
                  child: EmptyState(
                    icon: Icons.request_quote_rounded,
                    title: t.rfqNoRequestsTitle,
                    message: t.rfqNoRequestsMessage,
                  ),
                );
              }
              return Column(
                children: [
                  for (final rfq in rfqs)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _RfqCard(
                        rfq: rfq,
                        acceptingOfferId: _acceptingOfferId,
                        onAccept: _accept,
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _createForm(BuildContext context) {
    final t = AppLocalizations.of(context);
    final commoditiesAsync = ref.watch(commoditiesProvider);

    return Form(
      key: _formKey,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              t.rfqCreateTitle,
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 14),
            commoditiesAsync.when(
              loading: () => const SkeletonBox(height: 56, radius: 12),
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
                    onChanged: (c) => setState(() => _commodity = c),
                    decoration: InputDecoration(labelText: t.marketCommodity),
                  ),
                );
              },
            ),
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    controller: _quantityController,
                    keyboardType: const TextInputType.numberWithOptions(
                        decimal: true),
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
            const SizedBox(height: 14),
            TextFormField(
              controller: _maxPriceController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: t.rfqMaxPriceLabel(_unit),
                hintText: 'e.g. 24',
              ),
              validator: (v) {
                final n = double.tryParse(v?.trim() ?? '');
                if (n == null || n <= 0) return t.rfqEnterMaxPrice;
                return null;
              },
            ),
            const SizedBox(height: 14),
            InkWell(
              onTap: _pickNeededBy,
              borderRadius: BorderRadius.circular(12),
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: t.rfqNeededBy,
                  suffixIcon: const Icon(Icons.calendar_month_rounded,
                      size: 20),
                ),
                child: Text(
                  _neededBy == null
                      ? t.rfqNeededByEmpty
                      : '${_neededBy!.day}/${_neededBy!.month}/${_neededBy!.year}',
                ),
              ),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: _posting ? null : _post,
              icon: _posting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.2, color: Colors.white),
                    )
                  : const Icon(Icons.campaign_rounded, size: 20),
              label: Text(t.rfqSubmit),
            ),
          ],
        ),
      ),
    );
  }
}

class _RfqCard extends StatelessWidget {
  const _RfqCard({
    required this.rfq,
    required this.acceptingOfferId,
    required this.onAccept,
  });

  final Rfq rfq;
  final String acceptingOfferId;
  final void Function(RfqOffer offer) onAccept;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${rfq.title} · ${rfq.quantityLabel}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w700),
                ),
              ),
              StatusChip(label: rfq.status, tone: _rfqTone(rfq.status)),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${rfq.maxPriceLabel} · ${t.rfqNeededBy}: ${rfq.neededByLabel}',
            style: const TextStyle(
                fontSize: 12.5, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 10),
          Text(
            t.rfqOffersCount(rfq.offers.length),
            style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: AppColors.textSecondary),
          ),
          const SizedBox(height: 6),
          if (rfq.offers.isEmpty)
            Text(
              t.rfqNoOffers,
              style: const TextStyle(
                  fontSize: 13, color: AppColors.textSecondary),
            )
          else
            for (final offer in rfq.offers)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _OfferRow(
                  offer: offer,
                  busy: acceptingOfferId == offer.id,
                  onAccept: () => onAccept(offer),
                ),
              ),
        ],
      ),
    );
  }
}

class _OfferRow extends StatelessWidget {
  const _OfferRow({
    required this.offer,
    required this.busy,
    required this.onAccept,
  });

  final RfqOffer offer;
  final bool busy;
  final VoidCallback onAccept;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.cream,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  // Privacy-safe farmer label from the API, shown as-is.
                  offer.farmerLabel ?? 'Farmer',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 13.5, fontWeight: FontWeight.w700),
                ),
                Text(
                  offer.priceLabel,
                  style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primary),
                ),
              ],
            ),
          ),
          if (offer.isAccepted)
            const StatusChip(label: 'Accepted', tone: StatusTone.success)
          else if (offer.isPending)
            busy
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2.2),
                  )
                : FilledButton.tonal(
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      // Bounded minimum: the theme's full-width minimum would
                      // be unbounded inside this Row (no Expanded here).
                      minimumSize: const Size(0, 44),
                    ),
                    onPressed: onAccept,
                    child: Text(t.rfqAccept),
                  )
          else
            StatusChip(label: offer.status, tone: StatusTone.neutral),
        ],
      ),
    );
  }
}

StatusTone _rfqTone(String status) {
  switch (status.toLowerCase()) {
    case 'open':
      return StatusTone.success;
    case 'fulfilled':
      return StatusTone.info;
    case 'closed':
      return StatusTone.neutral;
    default:
      return StatusTone.warning;
  }
}
