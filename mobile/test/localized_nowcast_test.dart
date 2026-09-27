import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:agro_meteo_panchayat/data/models/api_models.dart';
import 'package:agro_meteo_panchayat/data/repositories/agro_repository.dart';
import 'package:agro_meteo_panchayat/widgets/localized_precipitation_card.dart';

void main() {
  group('Task 6: Localized Precipitation Nowcast Typed Model Tests', () {
    test('1. Parses complete nowcast model and horizons from JSON', () {
      final json = {
        'panchayat_id': 'DHOLAKPUR_PANCHAYAT_A',
        'panchayat_name': 'Dholakpur West Gram Panchayat',
        'block_name': 'Dholakpur Block',
        'district_name': 'Dholakpur District',
        'issue_time': '2026-09-27T10:00:00Z',
        'source_state': 'NWP_SATELLITE',
        'primary_horizon': {
          'horizon_minutes': 30,
          'precipitation_probability': 0.72,
          'expected_precipitation_mm': 3.5,
          'confidence': 'HIGH',
          'evidence_sources': ['NWP_IMD', 'INSAT_3D_TIR1'],
          'disagreement_detected': false,
          'baseline_probability': 0.55,
          'baseline_precipitation_mm': 1.2,
        },
        'horizons': [
          {
            'horizon_minutes': 30,
            'precipitation_probability': 0.72,
            'expected_precipitation_mm': 3.5,
            'confidence': 'HIGH',
            'evidence_sources': ['NWP_IMD', 'INSAT_3D_TIR1'],
            'disagreement_detected': false,
            'baseline_probability': 0.55,
            'baseline_precipitation_mm': 1.2,
          },
          {
            'horizon_minutes': 60,
            'precipitation_probability': 0.68,
            'expected_precipitation_mm': 2.8,
            'confidence': 'HIGH',
            'evidence_sources': ['NWP_IMD', 'INSAT_3D_TIR1'],
            'disagreement_detected': false,
            'baseline_probability': 0.55,
            'baseline_precipitation_mm': 1.2,
          },
          {
            'horizon_minutes': 120,
            'precipitation_probability': 0.51,
            'expected_precipitation_mm': 1.4,
            'confidence': 'MEDIUM',
            'evidence_sources': ['NWP_IMD'],
            'disagreement_detected': false,
            'baseline_probability': 0.55,
            'baseline_precipitation_mm': 1.2,
          },
        ],
        'confidence': 'HIGH',
        'disagreement_detected': false,
        'observation_age_minutes': 15.0,
        'is_stale': false,
        'spatial_coverage_fraction': 1.0,
        'native_source_resolution_km': 4.0,
        'display_resolution_note': 'Display grid is finer than source resolution.',
        'method_version': 'FUSION_RESEARCH_V1',
        'success': true,
      };

      final model = LocalizedPrecipitationNowcastModel.fromJson(json);

      expect(model.panchayatId, equals('DHOLAKPUR_PANCHAYAT_A'));
      expect(model.panchayatName, equals('Dholakpur West Gram Panchayat'));
      expect(model.confidence, equals('HIGH'));
      expect(model.sourceState, equals('NWP_SATELLITE'));
      expect(model.isStale, isFalse);
      expect(model.observationAgeMinutes, equals(15.0));
      expect(model.horizons.length, equals(3));
      expect(model.primaryHorizon?.horizonMinutes, equals(30));
      expect(model.primaryHorizon?.precipitationProbability, equals(0.72));
      expect(model.primaryHorizon?.expectedPrecipitationMm, equals(3.5));
    });

    test('2. Preserves null expected amount safely (never converts null to 0 mm)', () {
      final json = {
        'panchayat_id': 'DHOLAKPUR_PANCHAYAT_B',
        'issue_time': '2026-09-27T10:00:00Z',
        'source_state': 'NWP_ONLY',
        'primary_horizon': {
          'horizon_minutes': 30,
          'precipitation_probability': 0.18,
          'expected_precipitation_mm': null, // unestimable
          'confidence': 'LOW',
          'evidence_sources': ['NWP_IMD'],
          'disagreement_detected': true,
          'baseline_probability': 0.55,
          'baseline_precipitation_mm': 1.2,
        },
        'horizons': [],
        'confidence': 'LOW',
        'disagreement_detected': true,
        'disagreement_reason': 'NWP predicted rain but local satellite shows clear sky.',
        'is_stale': false,
        'success': true,
      };

      final model = LocalizedPrecipitationNowcastModel.fromJson(json);

      expect(model.primaryHorizon?.expectedPrecipitationMm, isNull);
      expect(model.disagreementDetected, isTrue);
      expect(model.disagreementReason, contains('NWP predicted rain'));
    });

    test('3. Confidence tiers parse faithfully without numerical conversion', () {
      for (final tier in ['HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT_DATA']) {
        final json = {
          'panchayat_id': 'TEST_P',
          'confidence': tier,
          'source_state': 'NWP_ONLY',
          'issue_time': '2026-09-27T10:00:00Z',
          'is_stale': false,
          'success': true,
        };
        final m = LocalizedPrecipitationNowcastModel.fromJson(json);
        expect(m.confidence, equals(tier));
      }
    });

    test('4. Dholakpur Adjacent Panchayat A/B Separation Verification', () {
      // Dholakpur West (A) - high localized rain probability
      final jsonA = {
        'location_id': 'DHOLAKPUR_PANCHAYAT_A',
        'location_name': 'Dholakpur West Gram Panchayat',
        'block': 'Dholakpur Block',
        'district': 'Dholakpur District',
        'latitude': 25.35,
        'longitude': 82.90,
        'elevation_m': 110.0,
        'forecast_date': '2026-09-27',
        'forecast_hour': 10,
        'request_id': 'req_a',
        'current': {
          'temperature_c': 28.0,
          'downscaled_temperature_c': 28.7,
          'coarse_temp_c': 28.0,
          'dynamic_residual_c': 0.74,
          'humidity_pct': 85,
          'wind_speed_kmh': 18.0,
          'rainfall_mm': 4.5,
          'rain_probability_pct': 75,
          'weather_code': 61,
          'condition_text': 'Heavy Localized Showers',
          'icon_name': 'cloud-rain',
        },
        'precipitation_nowcast': {
          'panchayat_id': 'DHOLAKPUR_PANCHAYAT_A',
          'panchayat_name': 'Dholakpur West Gram Panchayat',
          'block_name': 'Dholakpur Block',
          'district_name': 'Dholakpur District',
          'issue_time': '2026-09-27T10:00:00Z',
          'source_state': 'NWP_SATELLITE',
          'confidence': 'HIGH',
          'disagreement_detected': false,
          'is_stale': false,
          'primary_horizon': {
            'horizon_minutes': 30,
            'precipitation_probability': 0.78,
            'expected_precipitation_mm': 4.2,
            'confidence': 'HIGH',
            'evidence_sources': ['NWP_IMD', 'INSAT_3D_TIR1'],
            'disagreement_detected': false,
            'baseline_probability': 0.55,
            'baseline_precipitation_mm': 1.2,
          },
          'horizons': [],
          'success': true,
        },
        'farmer_actions': [
          {
            'id': 'act_a',
            'priority': 'HIGH',
            'category': 'WATER_MANAGEMENT',
            'title': 'Postpone Spraying — Rain Imminent',
            'timing': 'Next 30–60 min',
            'action': 'Suspend chemical spraying immediately; rain imminent.',
            'why': 'Nowcast indicates 78% localized rain probability.',
            'crop': 'Rice (Paddy)',
            'crop_stage': 'Flowering',
            'risk': 'Wash-off',
            'weather_trigger': 'Localized rain probability 78%',
          }
        ],
      };

      // Dholakpur East (B) - low localized rain probability under same baseline
      final jsonB = {
        'location_id': 'DHOLAKPUR_PANCHAYAT_B',
        'location_name': 'Dholakpur East Gram Panchayat',
        'block': 'Dholakpur Block',
        'district': 'Dholakpur District',
        'latitude': 25.35,
        'longitude': 83.05,
        'elevation_m': 105.0,
        'forecast_date': '2026-09-27',
        'forecast_hour': 10,
        'request_id': 'req_b',
        'current': {
          'temperature_c': 32.0,
          'downscaled_temperature_c': 32.7,
          'coarse_temp_c': 32.0,
          'dynamic_residual_c': 0.74,
          'humidity_pct': 55,
          'wind_speed_kmh': 10.0,
          'rainfall_mm': 0.0,
          'rain_probability_pct': 20,
          'weather_code': 1,
          'condition_text': 'Mainly Clear',
          'icon_name': 'sun',
        },
        'precipitation_nowcast': {
          'panchayat_id': 'DHOLAKPUR_PANCHAYAT_B',
          'panchayat_name': 'Dholakpur East Gram Panchayat',
          'block_name': 'Dholakpur Block',
          'district_name': 'Dholakpur District',
          'issue_time': '2026-09-27T10:00:00Z',
          'source_state': 'NWP_SATELLITE',
          'confidence': 'MEDIUM',
          'disagreement_detected': true,
          'disagreement_reason': 'NWP forecast rain but local satellite confirms clear conditions.',
          'is_stale': false,
          'primary_horizon': {
            'horizon_minutes': 30,
            'precipitation_probability': 0.15,
            'expected_precipitation_mm': null,
            'confidence': 'MEDIUM',
            'evidence_sources': ['NWP_IMD', 'INSAT_3D_TIR1'],
            'disagreement_detected': true,
            'baseline_probability': 0.55,
            'baseline_precipitation_mm': 1.2,
          },
          'horizons': [],
          'success': true,
        },
        'farmer_actions': [
          {
            'id': 'act_b',
            'priority': 'LOW',
            'category': 'FIELD_OPERATIONS',
            'title': 'Clear Weather Window Confirmed',
            'timing': 'Next 2–4 hours',
            'action': 'Proceed with planned field operations; clear window active.',
            'why': 'Localized satellite observations confirm clear sky.',
            'crop': 'Rice (Paddy)',
            'crop_stage': 'Flowering',
            'risk': 'None',
            'weather_trigger': 'Localized rain risk 15%',
          }
        ],
      };

      final respA = ForecastResponse.fromJson(jsonA);
      final respB = ForecastResponse.fromJson(jsonB);

      // Verify strict separation
      expect(respA.locationId, equals('DHOLAKPUR_PANCHAYAT_A'));
      expect(respB.locationId, equals('DHOLAKPUR_PANCHAYAT_B'));

      expect(respA.precipitationNowcast?.primaryHorizon?.precipitationProbability, equals(0.78));
      expect(respB.precipitationNowcast?.primaryHorizon?.precipitationProbability, equals(0.15));

      expect(respA.precipitationNowcast?.disagreementDetected, isFalse);
      expect(respB.precipitationNowcast?.disagreementDetected, isTrue);

      // Advisory mapping
      final advA = AgroRepository.toAdvisoryItems(respA);
      final advB = AgroRepository.toAdvisoryItems(respB);

      expect(advA.first.localizedNowcastContext, contains('78% rain risk'));
      expect(advB.first.localizedNowcastContext, contains('15% rain risk'));
      expect(advB.first.nowcastDisagreement, isTrue);
    });
  });

  group('Task 6: LocalizedPrecipitationCard Widget Rendering Tests', () {
    testWidgets('1. Renders baseline and localized nowcast values distinctly', (tester) async {
      final nowcast = LocalizedPrecipitationNowcastModel(
        panchayatId: 'DHOLAKPUR_PANCHAYAT_A',
        panchayatName: 'Dholakpur West',
        blockName: 'Dholakpur Block',
        districtName: 'Varanasi',
        issueTime: '2026-09-27T10:00:00Z',
        sourceState: 'NWP_SATELLITE',
        confidence: 'HIGH',
        disagreementDetected: false,
        isStale: false,
        observationAgeMinutes: 12.0,
        success: true,
        primaryHorizon: const NowcastHorizonModel(
          horizonMinutes: 30,
          precipitationProbability: 0.72,
          expectedPrecipitationMm: 3.5,
          confidence: 'HIGH',
          evidenceSources: ['NWP', 'SATELLITE'],
          disagreementDetected: false,
          baselineProbability: 0.55,
          baselinePrecipitationMm: 1.0,
        ),
        horizons: const [
          NowcastHorizonModel(
            horizonMinutes: 30,
            precipitationProbability: 0.72,
            expectedPrecipitationMm: 3.5,
            confidence: 'HIGH',
            evidenceSources: ['NWP', 'SATELLITE'],
            disagreementDetected: false,
            baselineProbability: 0.55,
          ),
          NowcastHorizonModel(
            horizonMinutes: 60,
            precipitationProbability: 0.65,
            expectedPrecipitationMm: 2.1,
            confidence: 'HIGH',
            evidenceSources: ['NWP', 'SATELLITE'],
            disagreementDetected: false,
            baselineProbability: 0.55,
          ),
        ],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LocalizedPrecipitationCard(
              nowcast: nowcast,
              baselineRainfallMm: 1.0,
              baselineProbabilityPct: 55,
              panchayatName: 'Dholakpur West',
              panchayatId: 'DHOLAKPUR_PANCHAYAT_A',
              blockName: 'Dholakpur Block',
              districtName: 'Varanasi',
              isToday: true,
            ),
          ),
        ),
      );

      // Verify baseline and nowcast labels are both present
      expect(find.text('BASELINE NWP'), findsOneWidget);
      expect(find.text('LOCAL NOWCAST'), findsOneWidget);
      expect(find.text('1.0 mm (55%)'), findsOneWidget);
      expect(find.text('Rain risk: 72%'), findsOneWidget);
      expect(find.text('Expected: ~3.5 mm'), findsOneWidget);
      expect(find.text('CONFIDENCE: HIGH'), findsOneWidget);
      expect(find.textContaining('Next 30m'), findsOneWidget);
      expect(find.textContaining('Next 60m'), findsOneWidget);
    });

    testWidgets('2. Displays disagreement warning when baseline and local observations differ', (tester) async {
      final nowcast = LocalizedPrecipitationNowcastModel(
        panchayatId: 'DHOLAKPUR_PANCHAYAT_B',
        panchayatName: 'Dholakpur East',
        blockName: 'Dholakpur Block',
        districtName: 'Varanasi',
        issueTime: '2026-09-27T10:00:00Z',
        sourceState: 'NWP_SATELLITE',
        confidence: 'LOW',
        disagreementDetected: true,
        disagreementReason: 'Baseline model predicted rain while satellite confirms clear sky.',
        isStale: false,
        observationAgeMinutes: 10.0,
        success: true,
        primaryHorizon: const NowcastHorizonModel(
          horizonMinutes: 30,
          precipitationProbability: 0.15,
          expectedPrecipitationMm: null,
          confidence: 'LOW',
          evidenceSources: ['NWP', 'SATELLITE'],
          disagreementDetected: true,
          baselineProbability: 0.55,
          baselinePrecipitationMm: 1.0,
        ),
        horizons: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LocalizedPrecipitationCard(
              nowcast: nowcast,
              baselineRainfallMm: 1.0,
              baselineProbabilityPct: 55,
              panchayatName: 'Dholakpur East',
              panchayatId: 'DHOLAKPUR_PANCHAYAT_B',
              isToday: true,
            ),
          ),
        ),
      );

      expect(find.text('Forecast and local observations differ.'), findsOneWidget);
      expect(find.text('Baseline model predicted rain while satellite confirms clear sky.'), findsOneWidget);
      expect(find.text('Expected: — (unavailable)'), findsOneWidget);
      expect(find.text('CONFIDENCE: LOW'), findsOneWidget);
    });

    testWidgets('3. Renders honest unavailable notice when nowcast is null or failed', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: LocalizedPrecipitationCard(
              nowcast: null,
              baselineRainfallMm: 0.0,
              baselineProbabilityPct: 10,
              isToday: true,
            ),
          ),
        ),
      );

      expect(find.text('LOCAL PRECIPITATION OUTLOOK · UNAVAILABLE'), findsOneWidget);
    });

    testWidgets('4. Does not fabricate nowcast values on historical or future dates', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: LocalizedPrecipitationCard(
              nowcast: null,
              baselineRainfallMm: 0.0,
              baselineProbabilityPct: 10,
              isToday: false,
            ),
          ),
        ),
      );

      expect(find.textContaining('active for today\'s operational window only'), findsOneWidget);
    });
  });
}
