import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// A single pulsing skeleton block.
class SkeletonBox extends StatefulWidget {
  const SkeletonBox({
    super.key,
    this.width,
    this.height = 16,
    this.radius = 8,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  State<SkeletonBox> createState() => _SkeletonBoxState();
}

class _SkeletonBoxState extends State<SkeletonBox>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.45, end: 1).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
      ),
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          color: AppColors.skeletonBase,
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}

/// Skeleton for a list of rounded cards.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.itemCount = 4, this.itemHeight = 92});

  final int itemCount;
  final double itemHeight;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        itemCount,
        (index) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: SkeletonBox(height: itemHeight, radius: 16),
        ),
      ),
    );
  }
}

/// Skeleton matching a dashboard header + stat tiles + list.
class SkeletonDashboard extends StatelessWidget {
  const SkeletonDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SkeletonBox(width: 180, height: 22),
        const SizedBox(height: 8),
        const SkeletonBox(width: 240, height: 14),
        const SizedBox(height: 20),
        Row(
          children: [
            const Expanded(child: SkeletonBox(height: 84, radius: 16)),
            const SizedBox(width: 12),
            const Expanded(child: SkeletonBox(height: 84, radius: 16)),
          ],
        ),
        const SizedBox(height: 24),
        const SkeletonBox(width: 120, height: 18),
        const SizedBox(height: 12),
        const SkeletonList(itemCount: 3, itemHeight: 88),
      ],
    );
  }
}
