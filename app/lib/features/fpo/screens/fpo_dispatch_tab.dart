import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/money.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../../core/widgets/status_chip.dart';
import '../../marketplace/data/order_model.dart';
import '../../marketplace/data/providers.dart';
import '../../shipments/data/providers.dart';
import '../../shipments/data/shipment_model.dart';

/// FPO dispatch — group CONFIRMED member orders into a shared delivery
/// run: GET /orders/farmer?status=confirmed, optional driver from
/// GET /drivers, then POST /shipments. The created run opens read-only.
class FpoDispatchTab extends ConsumerStatefulWidget {
  const FpoDispatchTab({super.key});

  @override
  ConsumerState<FpoDispatchTab> createState() => _FpoDispatchTabState();
}

class _FpoDispatchTabState extends ConsumerState<FpoDispatchTab> {
  final Set<String> _selectedOrderIds = {};
  String? _driverId;
  bool _creating = false;

  void _toggle(String orderId) {
    setState(() {
      if (_selectedOrderIds.contains(orderId)) {
        _selectedOrderIds.remove(orderId);
      } else {
        _selectedOrderIds.add(orderId);
      }
    });
  }

  Future<void> _createRun() async {
    if (_selectedOrderIds.isEmpty) return;
    setState(() => _creating = true);
    try {
      final shipment = await ref.read(shipmentApiProvider).create(
            orderIds: _selectedOrderIds.toList(),
            driverId: _driverId,
          );
      ref.invalidate(myShipmentsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context).fpoRunCreated)));
        context.push('/shipment/${shipment.id}?readonly=1');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final ordersAsync = ref.watch(confirmedFarmerOrdersProvider);
    final driversAsync = ref.watch(driversProvider);

    return TabBody(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            t.fpoDispatchTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            t.fpoDispatchSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 18),
          Text(
            t.fpoSelectOrders,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          ordersAsync.when(
            loading: () => const SkeletonList(itemCount: 3, itemHeight: 88),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () => ref.invalidate(confirmedFarmerOrdersProvider),
              compact: true,
            ),
            data: (page) {
              if (page.items.isEmpty) {
                return SizedBox(
                  height: 320,
                  child: EmptyState(
                    icon: Icons.inventory_rounded,
                    title: t.noOrdersTitle,
                    message: t.fpoNoConfirmedOrders,
                  ),
                );
              }
              return Column(
                children: [
                  for (final order in page.items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _SelectableOrderTile(
                        order: order,
                        selected: _selectedOrderIds.contains(order.id),
                        onToggle: () => _toggle(order.id),
                      ),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 18),
          _driverPicker(context, driversAsync),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed:
                _creating || _selectedOrderIds.isEmpty ? null : _createRun,
            icon: _creating
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2.2, color: Colors.white),
                  )
                : const Icon(Icons.local_shipping_rounded, size: 20),
            label: Text(
              _selectedOrderIds.isEmpty
                  ? t.fpoCreateRun
                  : t.fpoCreateRunSelected(_selectedOrderIds.length),
            ),
          ),
        ],
      ),
    );
  }

  Widget _driverPicker(
    BuildContext context,
    AsyncValue<List<DriverOption>> driversAsync,
  ) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: driversAsync.when(
        loading: () => const SkeletonBox(height: 52, radius: 12),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(driversProvider),
          compact: true,
        ),
        data: (drivers) => DropdownButtonHideUnderline(
          child: DropdownButtonFormField<String>(
            initialValue: _driverId,
            items: [
              DropdownMenuItem<String>(
                value: null,
                child: Text(t.fpoDriverUnassigned,
                    style: const TextStyle(color: AppColors.textSecondary)),
              ),
              for (final d in drivers)
                DropdownMenuItem(
                  value: d.id,
                  child: Text(d.label + (d.phone != null ? ' · ${d.phone}' : '')),
                ),
            ],
            onChanged: (id) => setState(() => _driverId = id),
            decoration: InputDecoration(
              labelText: t.fpoDriverOptional,
              border: InputBorder.none,
            ),
          ),
        ),
      ),
    );
  }
}

class _SelectableOrderTile extends StatelessWidget {
  const _SelectableOrderTile({
    required this.order,
    required this.selected,
    required this.onToggle,
  });

  final Order order;
  final bool selected;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppColors.paleGreen : Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: selected ? AppColors.primary : AppColors.border,
          width: selected ? 1.4 : 1,
        ),
      ),
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            children: [
              Checkbox(
                value: selected,
                onChanged: (_) => onToggle(),
                activeColor: AppColors.primary,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      order.itemSummary,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 14.5, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Text(
                          '…${order.id.length > 6 ? order.id.substring(order.id.length - 6) : order.id}',
                          style: const TextStyle(
                              fontSize: 12, color: AppColors.textSecondary),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          order.deliveryDistrict ?? '',
                          style: const TextStyle(
                              fontSize: 12, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(
                formatPaise(order.totalPaise),
                style: const TextStyle(
                    fontSize: 14.5, fontWeight: FontWeight.w800),
              ),
              const SizedBox(width: 8),
              StatusChip.forOrderStatus(order.status),
            ],
          ),
        ),
      ),
    );
  }
}
