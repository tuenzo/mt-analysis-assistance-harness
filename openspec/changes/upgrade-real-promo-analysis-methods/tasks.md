## 1. Current-State Audit

- [x] 1.1 Compare current diagnostics, LocalGap, PSM-DID, and GPS/Uplift modules against promo-causal-analysis skill guidance
- [x] 1.2 Confirm old repo-local skills do not contain better GPS/Uplift/LocalGap scripts
- [x] 1.3 Decide whether upgrade is needed

## 2. Method Upgrades

- [x] 2.1 Upgrade diagnostics with richer GMV, activity, payday/weekday, and quality outputs
- [x] 2.2 Upgrade LocalGap with same-weekday historical baseline, enriched panel, quality coverage, and decomposition
- [x] 2.3 Upgrade GPS dose-response to consume LocalGap enriched outcome and report support/overlap diagnostics
- [x] 2.4 Upgrade uplift prioritization with time-safe folds and stability-based buckets

## 3. Tests

- [x] 3.1 Add regression tests for enriched LocalGap outputs
- [x] 3.2 Add regression tests for GPS/Uplift diagnostics, fold stability, and warnings
- [x] 3.3 Run targeted pytest suite
