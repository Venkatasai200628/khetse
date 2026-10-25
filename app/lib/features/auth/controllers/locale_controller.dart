import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kLocaleKey = 'khetse.locale';

/// App language: English (`en`) or Telugu (`te`) — persisted per device.
class LocaleController extends Notifier<Locale> {
  @override
  Locale build() {
    _load();
    return const Locale('en');
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_kLocaleKey);
    if (saved == 'te') {
      state = const Locale('te');
    } else if (saved == 'en') {
      state = const Locale('en');
    }
  }

  Future<void> set(Locale locale) async {
    state = locale;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLocaleKey, locale.languageCode);
  }

  Future<void> toggle() =>
      set(state.languageCode == 'te' ? const Locale('en') : const Locale('te'));
}

final localeControllerProvider =
    NotifierProvider<LocaleController, Locale>(LocaleController.new);
