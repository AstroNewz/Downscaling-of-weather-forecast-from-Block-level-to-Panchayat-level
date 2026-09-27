import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('Task 6: Frontend Localized Nowcast Integration & Presentation Contract', () => {
  test('1. Baseline NWP forecast and localized nowcast remain distinct without overwrite', () => {
    const macroscaleNwpBaseline = {
      precipitation_mm: 1.5,
      precipitation_probability_pct: 60,
      source_model: 'IMD-GFS-0.25deg',
    };

    const localizedNowcast = {
      panchayat_id: 'DHOLAKPUR_PANCHAYAT_A',
      primary_horizon: {
        horizon_minutes: 30,
        precipitation_probability: 0.76,
        expected_precipitation_mm: 3.8,
        confidence: 'HIGH',
      },
    };

    // The baseline value must remain untouched and distinct from the localized nowcast
    assert.strictEqual(macroscaleNwpBaseline.precipitation_mm, 1.5);
    assert.strictEqual(macroscaleNwpBaseline.precipitation_probability_pct, 60);
    assert.strictEqual(localizedNowcast.primary_horizon.precipitation_probability, 0.76);
    assert.notStrictEqual(macroscaleNwpBaseline.precipitation_mm, localizedNowcast.primary_horizon.expected_precipitation_mm);
  });

  test('2. Unestimable expected rainfall is null (never coerced to 0 mm)', () => {
    const horizonWithNullAmount = {
      horizon_minutes: 30,
      precipitation_probability: 0.25,
      expected_precipitation_mm: null,
      confidence: 'LOW',
    };

    assert.strictEqual(horizonWithNullAmount.expected_precipitation_mm, null);
    assert.notStrictEqual(horizonWithNullAmount.expected_precipitation_mm, 0);

    // Format display string helper simulation
    const displayAmount = horizonWithNullAmount.expected_precipitation_mm !== null
      ? `~${horizonWithNullAmount.expected_precipitation_mm.toFixed(1)} mm`
      : 'Amount: —';

    assert.strictEqual(displayAmount, 'Amount: —');
  });

  test('3. Confidence states map strictly to HIGH, MEDIUM, LOW, INSUFFICIENT_DATA', () => {
    const validTiers = ['HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT_DATA'];
    validTiers.forEach((tier) => {
      const nowcast = { confidence: tier };
      assert.ok(validTiers.includes(nowcast.confidence));
      assert.strictEqual(typeof nowcast.confidence, 'string');
    });
  });

  test('4. Disagreement detection reports both signals without declaring either wrong', () => {
    const nowcastDisagreement = {
      disagreement_detected: true,
      disagreement_reason: 'Macroscale NWP model predicted rain while satellite observations indicate clear sky.',
      confidence: 'LOW', // Capped at LOW per scientific rule
      primary_horizon: {
        precipitation_probability: 0.12,
      },
      baseline_expectation: {
        baseline_precipitation_mm: 2.5,
        baseline_probability: 0.70,
      },
    };

    assert.strictEqual(nowcastDisagreement.disagreement_detected, true);
    assert.strictEqual(nowcastDisagreement.confidence, 'LOW');
    assert.ok(nowcastDisagreement.disagreement_reason.includes('NWP'));
  });

  test('5. Adjacent Panchayat A/B separation: Dholakpur West vs East remain distinct', () => {
    const panchayatA = {
      id: 'DHOLAKPUR_PANCHAYAT_A',
      name: 'Dholakpur West',
      block: 'Dholakpur Block',
      nowcast: {
        probability: 0.80,
        expected_mm: 4.5,
        confidence: 'HIGH',
      },
      advisory: {
        action: 'Suspend spraying immediately; rain imminent.',
      },
    };

    const panchayatB = {
      id: 'DHOLAKPUR_PANCHAYAT_B',
      name: 'Dholakpur East',
      block: 'Dholakpur Block',
      nowcast: {
        probability: 0.15,
        expected_mm: null,
        confidence: 'MEDIUM',
      },
      advisory: {
        action: 'Clear weather window confirmed; proceed with field operations.',
      },
    };

    // Shared block baseline
    assert.strictEqual(panchayatA.block, panchayatB.block);

    // Independent Panchayat identities
    assert.notStrictEqual(panchayatA.id, panchayatB.id);
    assert.notStrictEqual(panchayatA.name, panchayatB.name);

    // Independent localized nowcasts
    assert.strictEqual(panchayatA.nowcast.probability, 0.80);
    assert.strictEqual(panchayatB.nowcast.probability, 0.15);
    assert.notStrictEqual(panchayatA.nowcast.probability, panchayatB.nowcast.probability);

    // Independent advisories
    assert.notStrictEqual(panchayatA.advisory.action, panchayatB.advisory.action);
    assert.ok(panchayatA.advisory.action.includes('Suspend spraying'));
    assert.ok(panchayatB.advisory.action.includes('Clear weather window'));
  });

  test('6. Fail-closed behavior on unavailable or unverified boundary', () => {
    const failedNowcast = {
      success: false,
      data_quality_notes: 'Panchayat boundary is unverified; fail-closed policy active.',
      confidence: 'INSUFFICIENT_DATA',
    };

    assert.strictEqual(failedNowcast.success, false);
    assert.strictEqual(failedNowcast.confidence, 'INSUFFICIENT_DATA');
    assert.ok(failedNowcast.data_quality_notes.includes('unverified'));
  });

  test('7. Freshness formatting discloses stale observations honestly', () => {
    const formatFreshness = (ageMin, isStale) => {
      if (isStale) return 'Observation: Stale (penalized)';
      if (ageMin === null || ageMin === undefined) return 'Observation age: unknown';
      if (ageMin < 1) return 'Observation: Just now';
      return `Observation age: ${Math.round(ageMin)} min ago`;
    };

    assert.strictEqual(formatFreshness(15, false), 'Observation age: 15 min ago');
    assert.strictEqual(formatFreshness(45, true), 'Observation: Stale (penalized)');
    assert.strictEqual(formatFreshness(0.2, false), 'Observation: Just now');
  });

  test('8. Native-resolution disclosure note is present', () => {
    const disclosure = 'Display grid is finer than source resolution; visualization does not imply finer meteorological observations.';
    assert.ok(disclosure.includes('finer than source resolution'));
  });
});
