import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../l10n/app_localizations.dart';
import '../../../core/theme/app_colors.dart';
import '../controllers/auth_controller.dart';
import '../controllers/locale_controller.dart';

/// Registration completion for a new phone (after OTP verification returned
/// `registration_required`). POST /auth/register with the one-time token.
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({
    super.key,
    required this.token,
    required this.phone,
    this.role,
  });

  final String token;
  final String phone;
  final String? role;

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  static const _roles = {
    'farmer': (Icons.agriculture_rounded, 'Farmer'),
    'buyer': (Icons.shopping_basket_rounded, 'Buyer'),
    'business': (Icons.storefront_rounded, 'Business buyer'),
    'driver': (Icons.local_shipping_rounded, 'Driver'),
  };

  late String _selectedRole;
  final _nameController = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _selectedRole = _roles.containsKey(widget.role) ? widget.role! : 'farmer';
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    if (name.length < 2) {
      setState(() => _error = 'Please enter your full name.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final locale = ref.read(localeControllerProvider);
      final (token, user) = await ref.read(authApiProvider).register(
            registrationToken: widget.token,
            fullName: name,
            role: _selectedRole,
            preferredLanguage: locale.languageCode,
          );
      await ref.read(authControllerProvider.notifier).adoptSession(token, user);
      if (mounted) context.go(user.primaryRole.homePath);
    } catch (e) {
      setState(() {
        _busy = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.close_rounded),
          onPressed: () => context.canPop() ? context.pop() : context.go('/welcome'),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              Text(t.registerTitle,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              Text(
                '${t.otpSentTo} ${widget.phone}',
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 28),
              TextField(
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(
                  labelText: t.fullName,
                  hintText: 'e.g. Lakshmi Devi',
                  errorText: _error,
                ),
              ),
              const SizedBox(height: 24),
              Text(t.iAmA,
                  style: Theme.of(context)
                      .textTheme
                      .titleSmall
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              ..._roles.entries.map((entry) {
                final selected = _selectedRole == entry.key;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Material(
                    color: selected ? AppColors.paleGreen : Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                      side: BorderSide(
                        color: selected ? AppColors.primary : AppColors.border,
                        width: selected ? 1.6 : 1,
                      ),
                    ),
                    child: InkWell(
                      onTap: () => setState(() => _selectedRole = entry.key),
                      borderRadius: BorderRadius.circular(14),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                        child: Row(
                          children: [
                            Icon(entry.value.$1,
                                size: 22,
                                color: selected
                                    ? AppColors.primary
                                    : AppColors.textSecondary),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                entry.value.$2,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600),
                              ),
                            ),
                            Icon(
                              selected
                                  ? Icons.check_circle_rounded
                                  : Icons.radio_button_off_rounded,
                              color: selected
                                  ? AppColors.primary
                                  : AppColors.border,
                              size: 22,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }),
              const SizedBox(height: 26),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.4, color: Colors.white),
                      )
                    : Text(t.createAccount),
              ),
              const SizedBox(height: 12),
              Text(
                t.registerNote,
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
