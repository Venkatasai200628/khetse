import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../data/listing_model.dart';

/// Buyer-facing listing card: commodity, price/unit, quantity, origin.
class ListingCard extends StatelessWidget {
  const ListingCard({super.key, required this.listing});

  final Listing listing;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        onTap: () => context.push('/listing/${listing.id}'),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: AppColors.paleGreen,
                  borderRadius: BorderRadius.circular(14),
                ),
              child: Icon(
                categoryIcon(listing.commodityCategory),
                color: AppColors.primary,
                size: 26,
              ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            listing.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w700),
                          ),
                        ),
                        if (listing.isSynthetic)
                          Tooltip(
                            message: 'Demo data',
                            child: Icon(Icons.science_outlined,
                                size: 16, color: AppColors.harvest),
                          ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      listing.originLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 12.5, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 7),
                    Row(
                      children: [
                        Text(
                          listing.listedLabel,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: AppColors.primary,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          listing.availableLabel,
                          style: const TextStyle(
                              fontSize: 12, color: AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded,
                  color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }

  /// Public so the listing-detail hero can reuse the same icon mapping.
  static IconData categoryIcon(String? category) {
    switch (category) {
      case 'vegetables':
        return Icons.eco_rounded;
      case 'fruits':
        return Icons.local_florist_rounded;
      case 'grains':
        return Icons.grass_rounded;
      case 'pulses':
        return Icons.grain_rounded;
      case 'dairy':
        return Icons.water_drop_rounded;
      default:
        return Icons.spa_rounded;
    }
  }
}
