import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../../l10n/app_localizations.dart';
import '../data/providers.dart';
import '../data/shipment_model.dart';

/// One delivery run — ordered stops, per-stop handoff actions and the
/// crate manifest. Drivers get complete / fail / start actions; FPO
/// operators open it read-only after dispatching.
class ShipmentDetailScreen extends ConsumerStatefulWidget {
  const ShipmentDetailScreen({
    super.key,
    required this.shipmentId,
    this.readOnly = false,
  });

  final String shipmentId;

  /// FPO view: dispatchers can see stops + manifest but complete stops
  /// belong to the assigned driver, so the action buttons are hidden.
  final bool readOnly;

  @override
  ConsumerState<ShipmentDetailScreen> createState() =>
      _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends ConsumerState<ShipmentDetailScreen> {
  bool _acting = false;

  Future<void> _startRun(Shipment shipment) async {
    setState(() => _acting = true);
    try {
      await ref.read(shipmentApiProvider).start(shipment.id);
      _refresh(shipment.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context).shipmentStarted)));
      }
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _completeStop(ShipmentStop stop) async {
    final result = await showDialog<({String method, String code})>(
      context: context,
      builder: (ctx) => _CompleteStopDialog(stop: stop),
    );
    if (result == null) return;
    setState(() => _acting = true);
    try {
      await ref.read(shipmentApiProvider).completeStop(
            stopId: stop.id,
            method: result.method,
            code: result.code,
          );
      _refresh(widget.shipmentId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(AppLocalizations.of(context).stopCompleted)));
      }
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _failStop(ShipmentStop stop) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => const _FailStopDialog(),
    );
    if (reason == null || reason.trim().isEmpty) return;
    setState(() => _acting = true);
    try {
      await ref
          .read(shipmentApiProvider)
          .failStop(stopId: stop.id, reason: reason.trim());
      _refresh(widget.shipmentId);
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  void _refresh(String id) {
    ref.invalidate(shipmentDetailProvider(id));
    ref.invalidate(myShipmentsProvider);
  }

  void _showError(Object e) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(shipmentDetailProvider(widget.shipmentId));

    return Scaffold(
      appBar: AppBar(title: Text(t.shipmentDetailTitle)),
      body: SafeArea(
        child: switch (async) {
          AsyncLoading() => const SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: SkeletonList(itemCount: 4, itemHeight: 96),
            ),
          AsyncError(:final error) => ErrorView(
              message: error.toString(),
              onRetry: () => _refresh(widget.shipmentId),
            ),
          AsyncData(:final value) => SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _headerCard(context, value),
                  if (!widget.readOnly && value.canStart) ...[
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _acting ? null : () => _startRun(value),
                      icon: const Icon(Icons.play_arrow_rounded, size: 22),
                      label: Text(t.shipmentStartRun),
                    ),
                  ],
                  if (widget.readOnly) ...[
                    const SizedBox(height: 12),
                    _readOnlyNote(context),
                  ],
                  const SizedBox(height: 20),
                  Text(
                    t.shipmentStopsTitle,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 10),
                  for (final stop in value.stops)
                    _StopTile(
                      stop: stop,
                      busy: _acting,
                      showActions: !widget.readOnly,
                      onComplete: () => _completeStop(stop),
                      onFail: () => _failStop(stop),
                    ),
                  const SizedBox(height: 20),
                  _manifestCard(context, value),
                ],
              ),
            ),
          _ => ErrorView(
              message: t.shipmentLoadFailed,
              onRetry: () => _refresh(widget.shipmentId),
            ),
        },
      ),
    );
  }

  Widget _headerCard(BuildContext context, Shipment shipment) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
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
                  shipment.routeLabel,
                  style: const TextStyle(
                      fontSize: 16.5, fontWeight: FontWeight.w800),
                ),
              ),
              StatusChip.forShipmentStatus(shipment.status),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.route_rounded,
                  size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 5),
              Text(
                '${t.shipmentDistance}: ${shipment.distanceLabel}',
                style: const TextStyle(
                    fontSize: 13.5, fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 16),
              const Icon(Icons.linear_scale_rounded,
                  size: 16, color: AppColors.textSecondary),
              const SizedBox(width: 5),
              Text(
                t.shipmentStopCount(shipment.stopCount),
                style: const TextStyle(
                    fontSize: 13.5, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          if (shipment.pendingStopCount > 0) ...[
            const SizedBox(height: 8),
            Text(
              t.shipmentPendingCount(shipment.pendingStopCount),
              style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.harvest),
            ),
          ],
        ],
      ),
    );
  }

  Widget _readOnlyNote(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.paleGreen,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline_rounded,
              color: AppColors.deep, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              t.shipmentReadOnlyNote,
              style: const TextStyle(
                  fontSize: 13, height: 1.4, color: AppColors.deep),
            ),
          ),
        ],
      ),
    );
  }

  Widget _manifestCard(BuildContext context, Shipment shipment) {
    final t = AppLocalizations.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
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
              const Icon(Icons.inventory_2_outlined,
                  size: 18, color: AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                t.shipmentCratesTitle,
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (shipment.crates.isEmpty)
            Text(
              t.shipmentNoCrates,
              style: const TextStyle(
                  fontSize: 13, color: AppColors.textSecondary),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final crate in shipment.crates)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.cream,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Text(
                      crate.code,
                      style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.4),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

class _StopTile extends StatelessWidget {
  const _StopTile({
    required this.stop,
    required this.busy,
    required this.showActions,
    required this.onComplete,
    required this.onFail,
  });

  final ShipmentStop stop;
  final bool busy;
  final bool showActions;
  final VoidCallback onComplete;
  final VoidCallback onFail;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: stop.isActionable && showActions
              ? AppColors.primary.withValues(alpha: 0.35)
              : AppColors.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: stop.isPickup
                      ? AppColors.paleGreen
                      : AppColors.harvest.withValues(alpha: 0.14),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  stop.isPickup
                      ? Icons.agriculture_rounded
                      : Icons.home_rounded,
                  size: 18,
                  color: stop.isPickup ? AppColors.primary : AppColors.harvest,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 20,
                          height: 20,
                          alignment: Alignment.center,
                          decoration: const BoxDecoration(
                            color: AppColors.cream,
                            shape: BoxShape.circle,
                          ),
                          child: Text(
                            '${stop.sequence}',
                            style: const TextStyle(
                                fontSize: 11, fontWeight: FontWeight.w800),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          stop.isPickup ? t.stopPickup : t.stopDelivery,
                          style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: AppColors.textSecondary,
                              letterSpacing: 0.3),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      // Privacy-safe buyer labels from the API, shown as-is.
                      stop.label,
                      style: const TextStyle(
                          fontSize: 14.5, fontWeight: FontWeight.w700),
                    ),
                    if (stop.address != null && stop.address!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          stop.address!,
                          style: const TextStyle(
                              fontSize: 12.5,
                              color: AppColors.textSecondary),
                        ),
                      ),
                  ],
                ),
              ),
              StatusChip.forStopStatus(stop.status),
            ],
          ),
          if (showActions && stop.isActionable) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: busy ? null : onComplete,
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    icon: const Icon(Icons.qr_code_scanner_rounded, size: 18),
                    label: Text(t.stopComplete),
                  ),
                ),
                const SizedBox(width: 10),
                // Expanded: the theme's full-width button minimum would
                // otherwise be laid out with unbounded width inside this Row.
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: busy ? null : onFail,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.danger,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    icon: const Icon(Icons.report_problem_rounded, size: 18),
                    label: Text(t.stopReportProblem),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// Complete-a-stop dialog. Camera-less demo: the "QR scan" method asks for
/// the scanned token as text; the manual method takes the crate code.
class _CompleteStopDialog extends StatefulWidget {
  const _CompleteStopDialog({required this.stop});

  final ShipmentStop stop;

  @override
  State<_CompleteStopDialog> createState() => _CompleteStopDialogState();
}

class _CompleteStopDialogState extends State<_CompleteStopDialog> {
  String _method = 'qr';
  final _codeController = TextEditingController();

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(t.stopCompleteTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          RadioGroup<String>(
            groupValue: _method,
            onChanged: (v) => setState(() => _method = v ?? 'qr'),
            child: Column(
              children: [
                RadioListTile<String>(
                  value: 'qr',
                  title: Text(t.stopMethodQr),
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                ),
                RadioListTile<String>(
                  value: 'code',
                  title: Text(t.stopMethodCode),
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                ),
              ],
            ),
          ),
          const SizedBox(height: 4),
          TextField(
            controller: _codeController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: _method == 'qr'
                  ? t.stopScanTokenLabel
                  : t.stopCrateCodeLabel,
              hintText:
                  _method == 'qr' ? t.stopScanTokenHint : t.stopCrateCodeHint,
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
            final code = _codeController.text.trim();
            if (code.isEmpty) return;
            Navigator.pop(context, (method: _method, code: code));
          },
          child: Text(t.stopConfirmHandoff),
        ),
      ],
    );
  }
}

class _FailStopDialog extends StatefulWidget {
  const _FailStopDialog();

  @override
  State<_FailStopDialog> createState() => _FailStopDialogState();
}

class _FailStopDialogState extends State<_FailStopDialog> {
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(t.stopFailTitle),
      content: TextField(
        controller: _reasonController,
        maxLines: 3,
        autofocus: true,
        decoration: InputDecoration(
          labelText: t.stopFailReason,
          alignLabelWithHint: true,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(t.cancelLabel),
        ),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
          onPressed: () =>
              Navigator.pop(context, _reasonController.text.trim()),
          child: Text(t.stopFailConfirm),
        ),
      ],
    );
  }
}
