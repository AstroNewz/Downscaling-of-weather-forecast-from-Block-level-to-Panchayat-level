# Runbook 03: Downscaling Model Drift & Performance Degradation
**System**: SIH 26074 Panchayat Agro-Meteorological Advisory Platform  
**Target SLA**: Weekly model drift review; < 2 hours hotfix deployment if RMSE > 1.8°C  
**Severity**: P2 - High (Degrades accuracy of heat stress & disease risk triggers)

---

## 1. Trigger Conditions
- 7-day rolling Root Mean Squared Error (RMSE) against IMD/AWS observations exceeds **1.5°C** (baseline target: <= 0.85°C).
- Coefficient of Determination (R²) drops below **0.88** (baseline target: >= 0.94).
- Systematic bias detected: Mean Bias Error (MBE) > ±0.75°C persistently for 3 consecutive days.
- Extreme weather event (severe western disturbance, cyclonic remnant, heatwave spell) causing out-of-distribution errors.

---

## 2. Automated Drift Monitoring Pipeline

The platform runs an automated verification cron job at 00:30 IST daily:
```bash
python scripts/eval_model_drift.py --district "Ayodhya" --days 7
```
Output metrics:
- `rmse_24h`: Mean RMSE across all operational panchayat 1-km cells.
- `bias_direction`: Directional shift (over-prediction vs under-prediction).
- `cropland_specific_residual`: Residual error specifically over irrigated agricultural pixels.

---

## 3. Escalation & Remediation Workflow

```text
Daily Drift Check (00:30 IST)
           │
     RMSE <= 1.0°C?
     ├── YES ──> Status GREEN (Log to Governance Dashboard)
     └── NO  ──> Warning Alert to Extension Officer & ML Admin
           │
     RMSE > 1.5°C?
     ├── YES ──> [Action 1: Enable Dynamic Bias Correction]
     └── NO  ──> [Action 2: Schedule Weekly Transfer Learning]
```

### Action 1: Dynamic Topo-Thermal Bias Correction (Immediate Hotfix)
If an unexpected synoptic weather front creates temporary systematic offset:
1. Apply spatial Kalman filter bias offset based on last 24h ground AWS observations:
   ```bash
   curl -X POST http://localhost:8000/api/v1/models/bias-correction/enable \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"method": "kalman_residual_filter", "damping_factor": 0.65}'
   ```
2. Verify updated cell predictions in mobile app inspector:
   Ensure mean absolute difference against latest AWS reading drops below 0.6°C.

### Action 2: Incremental Model Retraining (Transfer Learning)
If seasonal transition (e.g. Rabi to Zaid summer crop shift) alters surface albedo and evapotranspiration dynamics:
1. Trigger automated incremental fine-tuning of the XGBoost / Random Forest downscaler:
   ```bash
   python models/train_downscaler.py \
     --dataset /data/training/ayodhya_rolling_90d.parquet \
     --target t_surface \
     --epochs 40 \
     --learning_rate 0.03
   ```
2. Execute shadow model evaluation against validation hold-out set:
   ```bash
   python models/validate_shadow.py --model-id "xgb-downscale-v2.2-candidate"
   ```
3. If shadow model RMSE < 0.78°C and R² > 0.95:
   Promote candidate model to production via zero-downtime hot-swap:
   ```bash
   curl -X POST http://localhost:8000/api/v1/models/promote \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"model_version": "v2.2-ayodhya", "approved_by": "DAO_Ayodhya"}'
   ```

---

## 4. Verification & Audit Trail
1. Open Mobile App -> Navigate to **Governance > Operational Metrics**:
   - Verify `RMSE` displays <= 0.85°C.
   - Verify `Active Model Version` reflects promoted version.
2. Verify **Audit Logs**:
   Confirm log entry: `"Model v2.2 promoted to production by DAO_Ayodhya"`.
