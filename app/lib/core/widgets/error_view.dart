import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Error state with a retry button — every data surface uses this so a
/// failed request is always recoverable, never a dead end.
class ErrorView extends StatelessWidget {
  const ErrorView({
    super.key,
    required this.message,
    required this.onRetry,
    this.compact = false,
  });

  final String message;
  final VoidCallback onRetry;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final body = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: compact ? 56 : 72,
          height: compact ? 56 : 72,
          decoration: const BoxDecoration(
            color: Color(0xFFFDECEA),
            shape: BoxShape.circle,
          ),
          child: Icon(
            Icons.wifi_off_rounded,
            color: AppColors.danger,
            size: compact ? 24 : 32,
          ),
        ),
        SizedBox(height: compact ? 12 : 20),
        Text(
          'Something went wrong',
          textAlign: TextAlign.center,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 6),
        Text(
          message,
          textAlign: TextAlign.center,
          style: Theme.of(context)
              .textTheme
              .bodyMedium
              ?.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_rounded, size: 20),
          label: const Text('Retry'),
        ),
      ],
    );

    if (compact) {
      return Padding(padding: const EdgeInsets.all(16), child: body);
    }
    return Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: body,
    ));
  }
}
