import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/misc.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../../l10n/app_localizations.dart';
import '../data/providers.dart';
import '../data/rfq_model.dart';

/// "Open demand" section for the farmer dashboard — GET /rfq/open. Farmers
/// quote against a business request with POST /rfq/{id}/offers.
class OpenDemandSection extends ConsumerStatefulWidget {
  const OpenDemandSection({super.key});

  @override
  ConsumerState<OpenDemandSection> createState() => _OpenDemandSectionState();
}

class _OpenDemandSectionState extends ConsumerState<OpenDemandSection> {
  String _quotingRfqId = '';

  Future<void> _quote(Rfq rfq) async {
    final pricePaise = await showDialog<int>(
      context: context,
      builder: (ctx) => _QuoteDialog(rfq: rfq),
    );
    if (pricePaise == null) return;
    setState(() => _quotingRfqId = rfq.id);
    try {
      await ref.read(rfqApiProvider).offer(
            rfqId: rfq.id,
            pricePaise: pricePaise,
          );
      ref.invalidate(openRfqsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context).rfqQuoted)));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _quotingRfqId = '');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(openRfqsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(t.rfqOpenDemand),
        const SizedBox(height: 2),
        Text(
          t.rfqOpenDemandSubtitle,
          style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 12),
        async.when(
          loading: () => const SkeletonList(itemCount: 2, itemHeight: 96),
          error: (e, _) => ErrorView(
            message: e.toString(),
            onRetry: () => ref.invalidate(openRfqsProvider),
            compact: true,
          ),
          data: (rfqs) {
            final open = rfqs.where((r) => r.isOpen).toList();
            if (open.isEmpty) {
              return EmptyState(
                icon: Icons.request_quote_rounded,
                title: t.rfqNoOpenDemandTitle,
                message: t.rfqNoOpenDemandMessage,
              );
            }
            return Column(
              children: [
                for (final rfq in open.take(3))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _OpenDemandCard(
                      rfq: rfq,
                      busy: _quotingRfqId == rfq.id,
                      onQuote: () => _quote(rfq),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _OpenDemandCard extends StatelessWidget {
  const _OpenDemandCard({
    required this.rfq,
    required this.busy,
    required this.onQuote,
  });

  final Rfq rfq;
  final bool busy;
  final VoidCallback onQuote;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
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
                      fontSize: 14.5, fontWeight: FontWeight.w700),
                ),
              ),
              StatusChip(label: rfq.status, tone: StatusTone.success),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${rfq.maxPriceLabel} · ${t.rfqNeededBy}: ${rfq.neededByLabel}',
            style: const TextStyle(
                fontSize: 12.5, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerRight,
            child: busy
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2.2),
                  )
                : FilledButton.tonal(
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.paleGreen,
                      foregroundColor: AppColors.deep,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                    ),
                    onPressed: onQuote,
                    child: Text(t.rfqQuote),
                  ),
          ),
        ],
      ),
    );
  }
}

/// Quote dialog — price in ₹ for the requested unit, converted to paise.
class _QuoteDialog extends StatefulWidget {
  const _QuoteDialog({required this.rfq});

  final Rfq rfq;

  @override
  State<_QuoteDialog> createState() => _QuoteDialogState();
}

class _QuoteDialogState extends State<_QuoteDialog> {
  final _priceController = TextEditingController();

  @override
  void dispose() {
    _priceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(t.rfqQuoteTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${widget.rfq.title} · ${widget.rfq.quantityLabel} · ${widget.rfq.maxPriceLabel}',
            style: const TextStyle(
                fontSize: 13, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _priceController,
            autofocus: true,
            keyboardType:
                const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: t.rfqYourPriceLabel(widget.rfq.unit),
              hintText: 'e.g. 22',
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t.cancelLabel),
        ),
        FilledButton(
          onPressed: () {
            final rupees = double.tryParse(_priceController.text.trim());
            if (rupees == null || rupees <= 0) return;
            Navigator.pop(context, rupeesToPaise(rupees));
          },
          child: Text(t.rfqSubmitQuote),
        ),
      ],
    );
  }
}
