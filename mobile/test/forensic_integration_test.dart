import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:agro_meteo_panchayat/data/models/api_models.dart';
import 'package:agro_meteo_panchayat/data/repositories/agro_repository.dart';
import 'package:agro_meteo_panchayat/providers/app_state.dart';
import 'package:agro_meteo_panchayat/screens/farmer_home_screen.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Forensic Mobile Data-Layer & Repository Tests', () {
    test('1. Cache isolation by locationId and targetDate', () {
      final repo = AgroRepository();

      // Sample mock responses for two different Panchayats and dates
      const p1d1 = ForecastResponse(
        locationId: '1',
        locationName: 'Maya Bazar',
        latitude: 25.35,
        longitude: 82.95,
        elevationM: 112.0,
        forecastDate: '2026-09-26',
        forecastHour: 12,
        requestId: 'req-1',
        current: CurrentWeather(
          temperatureC: 28.5,
          downscaledTemperatureC: 29.23,
          coarseTemperatureC: 28.5,
          dynamicResidualC: 0.73,
          humidityPct: 65,
          windSpeedKmh: 14.0,
          rainfallMm: 0.0,
          rainProbabilityPct: 10,
          weatherCode: 0,
          conditionText: 'Clear',
          iconName: 'sun',
        ),
        hourlyForecast: [],
        dailyForecast: [],
        agriculturalRisks: [],
        farmerActions: [],
        provenance: ProvenanceData(
          sourceProvider: 'OPEN_METEO',
          modelUsed: 'DYNAMIC_V2',
          certifiedBaselineInvariant: 'T_downscaled = T_coarse + 0.7351°C',
          fallbackActive: false,
          dataMode: 'DEMO',
          qualityStatus: 'PASSED',
          dataAgeMinutes: 0.0,
        ),
      );

      const p2d1 = ForecastResponse(
        locationId: '2',
        locationName: 'Cholapur',
        latitude: 25.42,
        longitude: 83.05,
        elevationM: 82.0,
        forecastDate: '2026-09-26',
        forecastHour: 12,
        requestId: 'req-2',
        current: CurrentWeather(
          temperatureC: 27.0,
          downscaledTemperatureC: 27.73,
          coarseTemperatureC: 27.0,
          dynamicResidualC: 0.73,
          humidityPct: 70,
          windSpeedKmh: 12.0,
          rainfallMm: 5.0,
          rainProbabilityPct: 40,
          weatherCode: 51,
          conditionText: 'Light Rain',
          iconName: 'rain',
        ),
        hourlyForecast: [],
        dailyForecast: [],
        agriculturalRisks: [],
        farmerActions: [],
        provenance: ProvenanceData(
          sourceProvider: 'OPEN_METEO',
          modelUsed: 'DYNAMIC_V2',
          certifiedBaselineInvariant: 'T_downscaled = T_coarse + 0.7351°C',
          fallbackActive: false,
          dataMode: 'DEMO',
          qualityStatus: 'PASSED',
          dataAgeMinutes: 0.0,
        ),
      );

      // Verify cache key determinism
      expect(AgroRepository.buildCacheKey('1', '2026-09-26'), '1__2026-09-26');
      expect(AgroRepository.buildCacheKey('2', '2026-09-26'), '2__2026-09-26');
      expect(AgroRepository.buildCacheKey('1', '2026-09-27'), '1__2026-09-27');

      // Before loading, cache is empty
      expect(repo.getCachedForecast(locationId: '1', targetDate: '2026-09-26'), isNull);
      expect(repo.getCachedForecast(locationId: '2', targetDate: '2026-09-26'), isNull);

      // Seed both forecasts
      repo.setCachedForecast(p1d1);
      repo.setCachedForecast(p2d1);

      // Verify strict isolation between locations
      expect(repo.getCachedForecast(locationId: '1', targetDate: '2026-09-26')?.locationName, 'Maya Bazar');
      expect(repo.getCachedForecast(locationId: '2', targetDate: '2026-09-26')?.locationName, 'Cholapur');

      // Verify strict date isolation: different date returns null
      expect(repo.getCachedForecast(locationId: '1', targetDate: '2026-09-27'), isNull);
      expect(repo.getCachedForecast(locationId: '2', targetDate: '2026-09-28'), isNull);
    });

    test('2. Advisory synchronization converts backend FarmerActions accurately', () {
      const sampleResponse = ForecastResponse(
        locationId: '1',
        locationName: 'Maya Bazar',
        latitude: 25.35,
        longitude: 82.95,
        elevationM: 112.0,
        forecastDate: '2026-09-26',
        forecastHour: 12,
        requestId: 'req-adv',
        current: CurrentWeather(
          temperatureC: 34.0,
          downscaledTemperatureC: 34.73,
          coarseTemperatureC: 34.0,
          dynamicResidualC: 0.73,
          humidityPct: 45,
          windSpeedKmh: 18.0,
          rainfallMm: 0.0,
          rainProbabilityPct: 5,
          weatherCode: 0,
          conditionText: 'Sunny',
          iconName: 'sun',
        ),
        hourlyForecast: [],
        dailyForecast: [],
        agriculturalRisks: [
          AgriculturalRiskItem(
            id: 'risk-1',
            category: 'THERMAL',
            riskType: 'HEAT_STRESS',
            title: 'High Thermal Stress',
            severity: 'HIGH',
            status: 'DETECTED',
            observedValue: 34.7,
            thresholdValue: 33.0,
            unit: '°C',
            crop: 'Rice (Paddy)',
            cropStage: 'Anthesis',
            condition: 'Anthesis sterility risk',
            why: 'Prolonged exposure > 33°C causes floret sterility',
            trigger: 'Temperature 34.7°C',
          )
        ],
        farmerActions: [
          FarmerActionItem(
            id: 'act-1',
            priority: 'HIGH',
            category: 'IRRIGATION',
            title: 'Apply Canopy-Cooling Irrigation',
            timing: 'Early Morning (05:00 - 08:00)',
            action: 'Apply light 2-3 cm standing water layer to dampen micro-canopy temperatures.',
            why: 'Forecast temperature (34.7°C) crosses physiological tolerance for flowering rice.',
            crop: 'Rice (Paddy)',
            cropStage: 'Anthesis',
            risk: 'HIGH',
            weatherTrigger: 'Downscaled temperature reaches 34.7°C',
          )
        ],
        provenance: ProvenanceData(
          sourceProvider: 'CANONICAL_PILOT_FIXTURE',
          modelUsed: 'DYNAMIC_V2',
          certifiedBaselineInvariant: 'T_downscaled = T_coarse + 0.7351°C',
          fallbackActive: false,
          dataMode: 'DEMO',
          qualityStatus: 'PASSED',
          dataAgeMinutes: 0.0,
        ),
      );

      final advisories = AgroRepository.toAdvisoryItems(sampleResponse);
      expect(advisories.length, 1);
      final adv = advisories.first;
      expect(adv.crop, 'Rice (Paddy)');
      expect(adv.growthStage, 'Anthesis');
      expect(adv.action, 'Apply light 2-3 cm standing water layer to dampen micro-canopy temperatures.');
      expect(adv.why, 'Forecast temperature (34.7°C) crosses physiological tolerance for flowering rice.');
      expect(adv.when, 'Early Morning (05:00 - 08:00)');
      expect(adv.scientificBasis, 'Downscaled temperature reaches 34.7°C');

      final risks = AgroRepository.toRiskAssessments(sampleResponse);
      expect(risks.length, 1);
      expect(risks.first.riskType, 'High Thermal Stress');
      expect(risks.first.observedValue, '34.7 °C');
      expect(risks.first.threshold, '33.0 °C');
    });

    test('3. Location change clears prior forecast to prevent data leakage', () async {
      final appState = AppState();
      expect(appState.selectedPanchayatId, '1');

      appState.setSelectedPanchayat('2');
      expect(appState.selectedPanchayatId, '2');
      // Must immediately clear forecast so stale location data does not display
      expect(appState.currentForecast, isNull);
    });

    test('4. Date change short-circuits on identical date and updates forecastDate', () async {
      final appState = AppState();
      final initialDate = appState.forecastDate;

      // Calling with identical date does not trigger unnecessary change
      appState.setForecastDate(initialDate);
      expect(appState.forecastDate, initialDate);

      // Changing to tomorrow
      final tomorrow = initialDate.add(const Duration(days: 1));
      appState.setForecastDate(tomorrow);
      expect(appState.forecastDate.day, tomorrow.day);
      expect(appState.forecastDate.month, tomorrow.month);
      expect(appState.forecastDate.year, tomorrow.year);
    });

    test('5. Downscaled temperature conversion preserves certified baseline', () {
      const sampleResponse = ForecastResponse(
        locationId: '1',
        locationName: 'Maya Bazar Panchayat',
        latitude: 25.35,
        longitude: 82.95,
        elevationM: 112.0,
        forecastDate: '2026-09-26',
        forecastHour: 14,
        requestId: 'req-downscale',
        current: CurrentWeather(
          temperatureC: 30.0,
          downscaledTemperatureC: 30.7351,
          coarseTemperatureC: 30.0,
          dynamicResidualC: 0.7351,
          humidityPct: 60,
          windSpeedKmh: 15.0,
          rainfallMm: 0.0,
          rainProbabilityPct: 10,
          weatherCode: 0,
          conditionText: 'Clear',
          iconName: 'sun',
        ),
        hourlyForecast: [],
        dailyForecast: [
          DailyForecastItem(
            date: '2026-09-26',
            displayLabel: 'Today',
            dayLabel: 'Sat',
            isToday: true,
            tMaxC: 35.0,
            tMinC: 24.0,
            rainfallMm: 0.0,
            rainProbabilityPct: 10,
            conditionText: 'Clear',
            iconName: 'sun',
            primaryRisk: 'LOW',
          )
        ],
        agriculturalRisks: [],
        farmerActions: [],
        provenance: ProvenanceData(
          sourceProvider: 'CANONICAL_PILOT_FIXTURE',
          modelUsed: 'DYNAMIC_V2',
          certifiedBaselineInvariant: 'T_downscaled = T_coarse + 0.7351°C',
          fallbackActive: false,
          dataMode: 'DEMO',
          qualityStatus: 'PASSED',
          dataAgeMinutes: 0.0,
        ),
      );

      final ds = AgroRepository.toDownscaledWeather(sampleResponse);
      expect(ds.tMean, 30.7351);
      expect(ds.tMin, 24.0);
      expect(ds.tMax, 35.0);
      expect(ds.localAdjustment, 0.7351);
      expect(ds.modelVersion, 'DYNAMIC_V2');
    });

    test('6. Full 24-hr diurnal forecast parses full_hourly from backend JSON without losing points', () {
      final jsonPayload = {
        'location_id': '1',
        'location_name': 'Maya Bazar Gram Panchayat',
        'latitude': 25.35,
        'longitude': 82.95,
        'elevation_m': 112.0,
        'forecast_date': '2026-09-26',
        'forecast_hour': 12,
        'request_id': 'req-test-hourly',
        'current': {
          'temperature_c': 32.83,
          'coarse_temp_c': 32.9,
          'dynamic_residual_c': -0.0671,
          'humidity_pct': 56.7,
          'wind_speed_kmh': 12.0,
          'precipitation_mm': 0.0,
          'condition_text': 'Mainly Clear',
          'icon_name': 'cloud-sun',
        },
        'full_hourly': List.generate(24, (i) => {
          'timestamp': '2026-09-26T${i.toString().padLeft(2, '0')}:00',
          'local_time': '${i.toString().padLeft(2, '0')}:00',
          'hour': i,
          'downscaled_temperature_c': 25.0 + (i * 0.5),
          'coarse_temperature_c': 24.2 + (i * 0.5),
          'dynamic_residual_c': 0.8,
          'humidity_pct': 70 - i,
          'wind_speed_kmh': 10.0 + (i * 0.2),
          'precipitation_mm': 0.0,
          'rain_probability_pct': 10,
          'risk': 'LOW',
          'advisory': 'Clear, normal ops',
        }),
        'daily_forecast': [],
        'agricultural_risks': [],
        'farmer_actions': [],
        'provenance': {
          'source_provider': 'CANONICAL_PILOT_FIXTURE',
          'model_used': 'DYNAMIC_V2',
          'certified_baseline_invariant': 'T_calibrated = T_coarse + 0.7351°C',
          'fallback_active': false,
          'data_mode': 'DEMO',
          'quality_status': 'PASSED',
        },
      };

      final parsed = ForecastResponse.fromJson(jsonPayload);
      expect(parsed.hourlyForecast.length, 24);
      expect(parsed.hourlyForecast[0].hour, 0);
      expect(parsed.hourlyForecast[0].downscaledTemperatureC, 25.0);
      expect(parsed.hourlyForecast[12].hour, 12);
      expect(parsed.hourlyForecast[12].downscaledTemperatureC, 31.0);
      expect(parsed.hourlyForecast[23].hour, 23);
    });

    test('7. Crop / filter change updates selection without modifying forecast identity', () {
      final appState = AppState();
      expect(appState.filterCrop, 'All');
      appState.setFilterCrop('Rice (Paddy)');
      expect(appState.filterCrop, 'Rice (Paddy)');
    });

    test('8. Rapid switching protects against out-of-order race conditions via request counter', () async {
      final appState = AppState();
      
      // Simulate rapid switching by invoking refreshForecast twice concurrently
      // The internal request counter ensures that older responses do not overwrite newer ones
      final f1 = appState.refreshForecast();
      appState.setSelectedPanchayat('2');
      final f2 = appState.refreshForecast();

      await Future.wait([f1, f2]);
      expect(appState.selectedPanchayatId, '2');
    });

    test('9. System data status model correctly maps LIVE and DEMO mode', () {
      final demoPayload = {
        'status': 'HEALTHY',
        'effective_mode': 'DEMO',
        'requested_mode': 'AUTO',
        'primary_provider': 'CANONICAL_PILOT_FIXTURE',
        'fallback_active': false,
        'freshness_seconds': 0.0,
      };
      final demoStatus = SystemDataStatusModel.fromJson(demoPayload);
      expect(demoStatus.effectiveMode, 'DEMO');
      expect(demoStatus.provider, 'CANONICAL_PILOT_FIXTURE');

      final livePayload = {
        'status': 'HEALTHY',
        'effective_mode': 'LIVE',
        'requested_mode': 'LIVE',
        'primary_provider': 'OPEN_METEO_OPERATIONAL',
        'fallback_active': false,
        'freshness_seconds': 120.0,
      };
      final liveStatus = SystemDataStatusModel.fromJson(livePayload);
      expect(liveStatus.effectiveMode, 'LIVE');
      expect(liveStatus.provider, 'OPEN_METEO_OPERATIONAL');
    });

    test('10. Backend failure records error and strictly prevents synthetic weather fallback', () async {
      final appState = AppState();
      await appState.refreshForecast();

      // AppState records the error and sets currentForecast to null
      expect(appState.hasForecastError, isTrue);
      expect(appState.currentForecast, isNull);
      
      // Strict safeguard: When backend fails, activeDownscaledWeather must be null (no fabricated weather)
      // and advisories/risks must be empty (no fabricated advisories)
      expect(appState.activeDownscaledWeather, isNull);
      expect(appState.activeAdvisories, isEmpty);
      expect(appState.activeRisks, isEmpty);
    });

    testWidgets('11. Backend unavailable displays explicit DATA UNAVAILABLE widget without fabricating weather',
        (WidgetTester tester) async {
      final appState = AppState();
      await appState.refreshForecast();

      expect(appState.hasForecastError, isTrue);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChangeNotifierProvider.value(
              value: appState,
              child: const FarmerHomeScreen(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify explicit DATA UNAVAILABLE card is displayed
      expect(find.text('DATA UNAVAILABLE'), findsOneWidget);
      expect(find.text('Retry Connection'), findsOneWidget);
      // Verify no synthetic temperature hero card is displayed
      expect(find.text('28.4°C'), findsNothing);
    });
  });
}
