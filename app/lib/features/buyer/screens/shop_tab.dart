import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/error_view.dart';
import '../../../core/widgets/role_shell.dart';
import '../../../core/widgets/skeleton.dart';
import '../../marketplace/data/providers.dart';
import '../../marketplace/widgets/listing_card.dart';

/// Buyer marketplace — GET /listings with live search (debounced).
class ShopTab extends ConsumerStatefulWidget {
  const ShopTab({super.key});

  @override
  ConsumerState<ShopTab> createState() => _ShopTabState();
}

class _ShopTabState extends ConsumerState<ShopTab> {
  final _searchController = TextEditingController();
  String? _search;
  Timer? _debounce;

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      setState(() => _search = value.trim().isEmpty ? null : value.trim());
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final async = ref.watch(browseListingsProvider(_search));

    return TabBody(
      bottomPadding: 32,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 4),
          Text(
            t.shopTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            t.shopSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _searchController,
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: t.searchHint,
              prefixIcon: const Icon(Icons.search_rounded, size: 22),
              suffixIcon: _searchController.text.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.close_rounded, size: 20),
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _search = null);
                      },
                    ),
            ),
          ),
          const SizedBox(height: 18),
          async.when(
            loading: () => const SkeletonList(itemCount: 5, itemHeight: 92),
            error: (e, _) => ErrorView(
              message: e.toString(),
              onRetry: () =>
                  ref.invalidate(browseListingsProvider(_search)),
              compact: true,
            ),
            data: (page) {
              if (page.items.isEmpty) {
                return SizedBox(
                  height: 420,
                  child: EmptyState(
                    icon: Icons.grass_rounded,
                    title: t.noListingsFoundTitle,
                    message: _search == null
                        ? t.shopEmptyMessage
                        : t.searchEmptyMessage,
                    actionLabel: _search == null ? null : t.clearSearch,
                    onAction: _search == null
                        ? null
                        : () {
                            _searchController.clear();
                            setState(() => _search = null);
                          },
                  ),
                );
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      '${page.total} ${page.total == 1 ? 'listing' : 'listings'}',
                      style: Theme.of(context)
                          .textTheme
                          .labelMedium
                          ?.copyWith(color: AppColors.textSecondary),
                    ),
                  ),
                  for (final listing in page.items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: ListingCard(listing: listing),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
