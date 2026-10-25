import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Section title used across dashboards ("Active listings", "Recent orders").
class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.actionLabel, this.onAction});

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
        ),
        if (actionLabel != null)
          TextButton(
            onPressed: onAction,
            style: TextButton.styleFrom(
              foregroundColor: AppColors.primary,
              textStyle: const TextStyle(fontWeight: FontWeight.w700),
            ),
            child: Text(actionLabel!),
          ),
      ],
    );
  }
}

/// Circular avatar with the user's initials on the brand gradient.
class InitialsAvatar extends StatelessWidget {
  const InitialsAvatar({super.key, required this.name, this.size = 48});

  final String name;
  final double size;

  String get _initials {
    final parts =
        name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      return parts.first.characters.first.toUpperCase();
    }
    return (parts.first.characters.first + parts.last.characters.first)
        .toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.primary, AppColors.deep],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        _initials,
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
          fontSize: size * 0.36,
        ),
      ),
    );
  }
}

/// The KhetSe leaf mark — a simple custom-painted logo so the app needs no
/// binary asset. Original artwork per ANALYSIS.md (never reuse the SIH logo).
class KhetSeLogo extends StatelessWidget {
  const KhetSeLogo({super.key, this.size = 88});

  final double size;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size.square(size),
      painter: _LeafPainter(),
    );
  }
}

class _LeafPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;

    // Rounded-square backdrop.
    final backdropPaint = Paint()..color = AppColors.primary;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(0, 0, s, s),
        Radius.circular(s * 0.28),
      ),
      backdropPaint,
    );

    // Two leaves: light leaf tilted left, cream leaf tilted right.
    final leaf1 = Paint()..color = AppColors.fresh;
    final leaf2 = Paint()..color = AppColors.cream;

    Path leaf(double cx, double cy, double w, double h, double tilt) {
      final rect = Rect.fromCenter(
        center: Offset(cx, cy),
        width: w,
        height: h,
      );
      final path = Path()
        ..moveTo(rect.center.dx, rect.top)
        ..quadraticBezierTo(rect.right, rect.center.dy, rect.center.dx,
            rect.bottom)
        ..quadraticBezierTo(
            rect.left, rect.center.dy, rect.center.dx, rect.top)
        ..close();
      final matrix = Matrix4.identity()
        ..translateByDouble(cx, cy, 0, 1)
        ..rotateZ(tilt)
        ..translateByDouble(-cx, -cy, 0, 1);
      return path.transform(matrix.storage);
    }

    canvas.drawPath(leaf(s * 0.42, s * 0.46, s * 0.34, s * 0.5, -0.5), leaf1);
    canvas.drawPath(leaf(s * 0.62, s * 0.58, s * 0.30, s * 0.44, 0.55), leaf2);

    // Ground stroke under the leaves.
    final ground = Paint()
      ..color = AppColors.harvest
      ..style = PaintingStyle.stroke
      ..strokeWidth = s * 0.045
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(s * 0.28, s * 0.82),
      Offset(s * 0.72, s * 0.82),
      ground,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Small labeled stat tile for dashboards — always fed by real API counts.
class StatTile extends StatelessWidget {
  const StatTile({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.accent = AppColors.primary,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: accent, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
