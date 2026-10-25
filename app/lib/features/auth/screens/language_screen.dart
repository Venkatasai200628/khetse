import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../controllers/locale_controller.dart';

/// Language selection: English / తెలుగు. Reachable from onboarding;
/// the profile screen offers the same switch later.
class LanguageScreen extends ConsumerWidget {
  const LanguageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final locale = ref.watch(localeControllerProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(t.chooseLanguage),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.canPop() ? context.pop() : context.go('/welcome'),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                t.languageSubtitle,
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 24),
              _LanguageOption(
                enabled: locale.languageCode == 'en',
                label: 'English',
                sublabel: 'Continue in English',
                onTap: () => ref.read(localeControllerProvider.notifier).set(const Locale('en')),
              ),
              const SizedBox(height: 14),
              _LanguageOption(
                enabled: locale.languageCode == 'te',
                label: 'తెలుగు',
                sublabel: 'తెలుగులో కొనసాగించండి',
                onTap: () => ref.read(localeControllerProvider.notifier).set(const Locale('te')),
              ),
              const Spacer(),
              FilledButton(
                onPressed: () =>
                    context.canPop() ? context.pop() : context.go('/welcome'),
                child: Text(t.continueLabel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageOption extends StatelessWidget {
  const _LanguageOption({
    required this.enabled,
    required this.label,
    required this.sublabel,
    required this.onTap,
  });

  final bool enabled;
  final String label;
  final String sublabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: enabled ? AppColors.paleGreen : Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: enabled ? AppColors.primary : AppColors.border,
          width: enabled ? 1.6 : 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(sublabel,
                        style: Theme.of(context)
                            .textTheme
                            .bodySmall
                            ?.copyWith(color: AppColors.textSecondary)),
                  ],
                ),
              ),
              Icon(
                enabled
                    ? Icons.check_circle_rounded
                    : Icons.radio_button_off_rounded,
                color: enabled ? AppColors.primary : AppColors.border,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
