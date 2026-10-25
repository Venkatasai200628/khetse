import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../l10n/app_localizations.dart';
import '../../../core/config/app_config.dart';
import '../../../core/network/response_utils.dart';
import '../../../core/theme/app_colors.dart';
import '../controllers/auth_controller.dart';
import '../data/auth_api.dart';

/// Phone + OTP login.
///
/// Flow: POST /auth/otp/request → (demo mode returns `dev_otp`, shown in a
/// banner) → POST /auth/otp/verify → either a session (redirect to the role
/// shell) or `registration_required` → continue to /register.
/// POST /auth/demo-login powers the one-tap demo accounts.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.role});

  final String? role;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phoneController = TextEditingController();
  final _otpController = TextEditingController();
  bool _otpSent = false;
  bool _busy = false;
  OtpRequestResult? _otpResult;
  String? _phoneError;
  String? _otpError;
  // Live handles from GET /welcome when reachable; static fallback otherwise.
  List<String> _demoCodes = AppConfig.demoCodes;

  @override
  void initState() {
    super.initState();
    _loadDemoCodes();
  }

  Future<void> _loadDemoCodes() async {
    try {
      final codes = await ref.read(authApiProvider).welcomeDemoCodes();
      if (codes.isNotEmpty && mounted) setState(() => _demoCodes = codes);
    } catch (_) {
      // Backend unreachable or demo mode off — keep the fallback list.
    }
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    super.dispose();
  }

  String get _normalisedPhone {
    var raw = _phoneController.text.trim();
    raw = raw.replaceAll(RegExp(r'[\s\-]'), '');
    if (!raw.startsWith('+')) {
      if (raw.startsWith('00')) raw = '+${raw.substring(2)}';
      if (!raw.startsWith('+')) raw = '+91$raw'; // backend normalises too
    }
    return raw;
  }

  Future<void> _requestOtp() async {
    final digits = _phoneController.text.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 10) {
      setState(() => _phoneError = 'Enter a valid 10-digit mobile number.');
      return;
    }
    setState(() {
      _phoneError = null;
      _busy = true;
    });
    try {
      final result =
          await ref.read(authApiProvider).requestOtp(_normalisedPhone);
      setState(() {
        _otpResult = result;
        _otpSent = true;
        _busy = false;
      });
    } catch (e) {
      setState(() {
        _busy = false;
        _phoneError = e.toString();
      });
    }
  }

  Future<void> _verifyOtp() async {
    final code = _otpController.text.trim();
    if (code.length < 4) {
      setState(() => _otpError = 'Enter the OTP you received.');
      return;
    }
    setState(() {
      _otpError = null;
      _busy = true;
    });
    try {
      final result =
          await ref.read(authApiProvider).verifyOtp(_normalisedPhone, code);
      if (!mounted) return;
      switch (result) {
        case OtpAuthenticated(:final token, :final user):
          await ref.read(authControllerProvider.notifier).adoptSession(token, user);
          if (mounted) context.go(user.primaryRole.homePath);
        case OtpRegistrationRequired(:final registrationToken, :final phone):
          context.push('/register'
              '?token=$registrationToken&phone=$phone&role=${widget.role ?? 'farmer'}');
      }
    } catch (e) {
      setState(() {
        _busy = false;
        _otpError = e.toString();
      });
    }
  }

  Future<void> _demoLogin(String code) async {
    setState(() => _busy = true);
    try {
      final (token, user) = await ref.read(authApiProvider).demoLogin(code);
      await ref.read(authControllerProvider.notifier).adoptSession(token, user);
      if (mounted) context.go(user.primaryRole.homePath);
    } catch (e) {
      setState(() => _busy = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(extractMessage(e) ?? e.toString())),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.canPop() ? context.pop() : context.go('/welcome'),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: _otpSent ? _buildOtpStep(t) : _buildPhoneStep(t),
        ),
      ),
    );
  }

  Widget _buildPhoneStep(AppLocalizations t) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        Text(t.loginTitle,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Text(t.loginSubtitle,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: AppColors.textSecondary)),
        const SizedBox(height: 28),
        TextField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          maxLength: 13,
          decoration: InputDecoration(
            labelText: t.phoneNumber,
            hintText: '98765 43210',
            counterText: '',
            prefixText: '+91 ',
            errorText: _phoneError,
          ),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _busy ? null : _requestOtp,
          child: _busy
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                )
              : Text(t.sendOtp),
        ),
        const SizedBox(height: 36),
        _DemoLoginSection(
          codes: _demoCodes,
          busy: _busy,
          onSelected: _demoLogin,
        ),
      ],
    );
  }

  Widget _buildOtpStep(AppLocalizations t) {
    final devOtp = _otpResult?.devOtp;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 8),
        Text(t.enterOtp,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Text(
          '${t.otpSentTo} $_normalisedPhone',
          style: Theme.of(context)
              .textTheme
              .bodyMedium
              ?.copyWith(color: AppColors.textSecondary),
        ),
        if (devOtp != null) ...[
          const SizedBox(height: 18),
          Material(
            color: const Color(0xFFFFF6E8),
            borderRadius: BorderRadius.circular(14),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () => _otpController.text = devOtp,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    const Icon(Icons.info_rounded, color: AppColors.harvest, size: 22),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '${t.demoOtpPrefix} $devOtp — ${t.tapToFill}',
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, color: Color(0xFF7A4A00)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
        const SizedBox(height: 22),
        TextField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          maxLength: 8,
          textAlign: TextAlign.center,
          style: const TextStyle(
              fontSize: 24, letterSpacing: 10, fontWeight: FontWeight.w700),
          decoration: InputDecoration(
            labelText: t.otpLabel,
            counterText: '',
            errorText: _otpError,
          ),
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: _busy ? null : _verifyOtp,
          child: _busy
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                )
              : Text(t.verify),
        ),
        const SizedBox(height: 10),
        TextButton(
          onPressed: _busy
              ? null
              : () => setState(() {
                    _otpSent = false;
                    _otpController.clear();
                    _otpError = null;
                  }),
          child: Text(t.changeNumber),
        ),
      ],
    );
  }
}

class _DemoLoginSection extends StatelessWidget {
  const _DemoLoginSection({
    required this.codes,
    required this.busy,
    required this.onSelected,
  });

  final List<String> codes;
  final bool busy;
  final void Function(String code) onSelected;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(children: [
          const Expanded(child: Divider()),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(t.demoDivider,
                style: Theme.of(context)
                    .textTheme
                    .labelMedium
                    ?.copyWith(color: AppColors.textSecondary)),
          ),
          const Expanded(child: Divider()),
        ]),
        const SizedBox(height: 18),
        ...codes.map(
          (code) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: OutlinedButton.icon(
              onPressed: busy ? null : () => onSelected(code),
              icon: _iconFor(code),
              label: Text('${t.demoLoginAs} ${AppConfig.demoLabel(code)}'),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          t.demoNote,
          textAlign: TextAlign.center,
          style: Theme.of(context)
              .textTheme
              .bodySmall
              ?.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }

  Icon _iconFor(String code) {
    final role = code.replaceAll(RegExp(r'\d+$'), '');
    switch (role) {
      case 'farmer':
        return const Icon(Icons.agriculture_rounded, size: 20);
      case 'buyer':
        return const Icon(Icons.shopping_basket_rounded, size: 20);
      case 'driver':
        return const Icon(Icons.local_shipping_rounded, size: 20);
      case 'fpo':
        return const Icon(Icons.groups_rounded, size: 20);
      default:
        return const Icon(Icons.admin_panel_settings_outlined, size: 20);
    }
  }
}
