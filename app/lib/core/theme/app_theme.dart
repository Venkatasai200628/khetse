import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Material 3 theme built on the KhetSe token set.
///
/// Typography uses Inter with Noto Sans / Noto Sans Telugu fallbacks so
/// Indic script renders on every platform including web.
class AppTheme {
  AppTheme._();

  static const String _latinFont = 'Inter';
  static const List<String> _fontFallback = ['NotoSans', 'NotoSansTelugu'];

  static ThemeData get light {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primary,
        onPrimary: Colors.white,
        primaryContainer: AppColors.paleGreen,
        onPrimaryContainer: AppColors.deep,
        secondary: AppColors.harvest,
        onSecondary: Colors.white,
        secondaryContainer: Color(0xFFFFF1DE),
        onSecondaryContainer: Color(0xFF7A3E00),
        surface: Colors.white,
        onSurface: AppColors.textPrimary,
        surfaceContainerHighest: AppColors.cream,
        onSurfaceVariant: AppColors.textSecondary,
        error: AppColors.danger,
        onError: Colors.white,
        outline: AppColors.border,
        outlineVariant: AppColors.border,
      ),
      scaffoldBackgroundColor: AppColors.cream,
    );

    return base.copyWith(
      textTheme: _textTheme(base.textTheme),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.cream,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        foregroundColor: AppColors.textPrimary,
        titleTextStyle: TextStyle(
          fontFamily: _latinFont,
          fontFamilyFallback: _fontFallback,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
      ),
      cardTheme: const CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          side: BorderSide(color: AppColors.border),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          textStyle: const TextStyle(
            fontFamily: _latinFont,
            fontFamilyFallback: _fontFallback,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary, width: 1.4),
          textStyle: const TextStyle(
            fontFamily: _latinFont,
            fontFamilyFallback: _fontFallback,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.6),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.danger),
        ),
        hintStyle: const TextStyle(color: AppColors.textSecondary),
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: AppColors.paleGreen,
        labelStyle: const TextStyle(
          fontFamily: _latinFont,
          fontFamilyFallback: _fontFallback,
          fontWeight: FontWeight.w600,
          color: AppColors.deep,
        ),
        side: BorderSide.none,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        indicatorColor: AppColors.paleGreen,
        height: 68,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? AppColors.primary
                : AppColors.textSecondary,
          ),
        ),
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontFamily: _latinFont,
            fontFamilyFallback: _fontFallback,
            fontSize: 12,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w700
                : FontWeight.w500,
            color: states.contains(WidgetState.selected)
                ? AppColors.primary
                : AppColors.textSecondary,
          ),
        ),
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.deep,
        contentTextStyle: TextStyle(
          fontFamily: _latinFont,
          fontFamilyFallback: _fontFallback,
          color: Colors.white,
          fontSize: 14,
        ),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.border, thickness: 1),
    );
  }

  static TextTheme _textTheme(TextTheme base) {
    TextStyle scaled(TextStyle style) => style.copyWith(
          fontFamily: _latinFont,
          fontFamilyFallback: _fontFallback,
          color: style.color ?? AppColors.textPrimary,
        );
    return base
        .apply(
          bodyColor: AppColors.textPrimary,
          displayColor: AppColors.textPrimary,
          fontFamily: _latinFont,
          fontFamilyFallback: _fontFallback,
        )
        .copyWith(
          displaySmall: scaled(base.displaySmall!)
              .copyWith(fontWeight: FontWeight.w800),
          headlineLarge: scaled(base.headlineLarge!)
              .copyWith(fontWeight: FontWeight.w800),
          headlineMedium: scaled(base.headlineMedium!)
              .copyWith(fontWeight: FontWeight.w800),
          headlineSmall: scaled(base.headlineSmall!)
              .copyWith(fontWeight: FontWeight.w700),
          titleLarge: scaled(base.titleLarge!).copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
          titleMedium: scaled(base.titleMedium!).copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
          ),
          titleSmall: scaled(base.titleSmall!).copyWith(
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
          bodyLarge: scaled(base.bodyLarge!),
          bodyMedium: scaled(base.bodyMedium!),
          bodySmall:
              scaled(base.bodySmall!).copyWith(color: AppColors.textSecondary),
          labelLarge: scaled(base.labelLarge!)
              .copyWith(fontWeight: FontWeight.w600),
          labelMedium: scaled(base.labelMedium!),
          labelSmall: scaled(base.labelSmall!)
              .copyWith(color: AppColors.textSecondary),
        );
  }
}
