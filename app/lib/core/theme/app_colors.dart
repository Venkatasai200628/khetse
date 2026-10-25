import 'package:flutter/material.dart';

/// KhetSe design tokens — from ANALYSIS.md §4 (design system).
///
/// Agricultural green dominant, harvest orange accents, cream/white surfaces.
class AppColors {
  AppColors._();

  // Brand greens
  static const Color primary = Color(0xFF138A4B);
  static const Color deep = Color(0xFF075B37);
  static const Color fresh = Color(0xFF22A66A);

  // Accent
  static const Color harvest = Color(0xFFF58A24);

  // Surfaces
  static const Color cream = Color(0xFFF8F8F2);
  static const Color paleGreen = Color(0xFFE8F5EC);
  static const Color white = Colors.white;

  // Text
  static const Color textPrimary = Color(0xFF18251D);
  static const Color textSecondary = Color(0xFF647067);

  // Lines
  static const Color border = Color(0xFFE1E8E1);

  // Status
  static const Color success = Color(0xFF138A4B);
  static const Color warning = Color(0xFFB45309);
  static const Color danger = Color(0xFFB3261E);
  static const Color info = Color(0xFF1D4ED8);

  // Skeleton
  static const Color skeletonBase = Color(0xFFE7EDE7);
  static const Color skeletonHighlight = Color(0xFFF3F7F3);
}
