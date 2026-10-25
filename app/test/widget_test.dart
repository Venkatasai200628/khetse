import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:khetse/app/app.dart';

void main() {
  testWidgets('KhetSe app boots and routes to welcome when signed out',
      (tester) async {
    // No stored token and no backend in tests.
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const ProviderScope(child: KhetSeApp()));

    // Splash shows the brand name and tagline while the session resolves.
    expect(find.text('KhetSe'), findsOneWidget);
    expect(find.text('Seedha Khet Se Ghar Tak'), findsOneWidget);

    // Burn the splash delay; the router redirect then lands on /welcome.
    await tester.pump(const Duration(milliseconds: 1600));
    await tester.pumpAndSettle();

    expect(find.text('Fresh from the farm, direct to you'), findsOneWidget);
  });
}
