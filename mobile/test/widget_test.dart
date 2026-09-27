import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:agro_meteo_panchayat/main.dart';
import 'package:agro_meteo_panchayat/providers/app_state.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Initial launch shows RoleSelectionScreen and allows selecting Farmer role',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(500, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final appState = AppState();
    await appState.loadFromPrefs(fetchBackend: false);

    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: appState,
        child: const AgroMeteoApp(),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    // Verify RoleSelectionScreen is displayed
    expect(find.text('AgroMeteo Panchayat'), findsOneWidget);
    expect(find.text('Farmer / Citizen'), findsOneWidget);
    expect(find.text('Government Official'), findsOneWidget);
    expect(find.text('Continue as Farmer'), findsOneWidget);

    // Tap "Continue as Farmer"
    await tester.tap(find.text('Continue as Farmer'));
    await tester.pumpAndSettle();

    // Verify Farmer shell is rendered
    expect(find.text('Maya Bazar Panchayat'), findsOneWidget);
    expect(find.text('Today\'s Advisories'), findsOneWidget);
  });

  testWidgets('Selecting Official role shows Official Operations Shell',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(500, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final appState = AppState();
    await appState.loadFromPrefs(fetchBackend: false);

    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: appState,
        child: const AgroMeteoApp(),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    // Scroll to and tap "Continue as Official"
    final officialBtn = find.text('Continue as Official');
    expect(officialBtn, findsOneWidget);
    await tester.scrollUntilVisible(officialBtn, 150);
    await tester.pumpAndSettle();
    await tester.tap(officialBtn);
    await tester.pumpAndSettle();

    // Verify Official shell is rendered
    expect(find.text('Operations Dashboard'), findsOneWidget);
    expect(find.text('High-Intervention Panchayats'), findsOneWidget);
  });

  testWidgets('Bidirectional role switching between Farmer and Official',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(500, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final appState = AppState();
    await appState.loadFromPrefs(fetchBackend: false);

    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: appState,
        child: const AgroMeteoApp(),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    // 1. Start as Farmer
    await tester.tap(find.text('Continue as Farmer'));
    await tester.pumpAndSettle();
    expect(find.text('Maya Bazar Panchayat'), findsOneWidget);

    // 2. Navigate to Farmer Profile (tab index 3)
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();

    // 3. Scroll down to show "Switch to Official Dashboard" cleanly above the nav bar
    await tester.drag(find.byType(ListView), const Offset(0, -350));
    await tester.pumpAndSettle();

    final switchButton = find.text('Switch to Official Dashboard');
    expect(switchButton, findsOneWidget);
    await tester.tap(switchButton);
    await tester.pumpAndSettle();

    // 4. Verify now on Official Shell
    expect(find.text('Operations Dashboard'), findsOneWidget);

    // 5. Navigate to Official Profile (tab index 5)
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();

    // 6. Scroll down to show "Switch to Farmer Experience"
    await tester.drag(find.byType(ListView), const Offset(0, -350));
    await tester.pumpAndSettle();

    final switchBack = find.text('Switch to Farmer Experience');
    expect(switchBack, findsOneWidget);
    await tester.tap(switchBack);
    await tester.pumpAndSettle();

    // 7. Verify back on Farmer Shell
    expect(find.text('Maya Bazar Panchayat'), findsOneWidget);
  });
}
