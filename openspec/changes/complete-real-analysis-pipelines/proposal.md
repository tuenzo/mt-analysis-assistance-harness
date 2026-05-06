# Complete Real Analysis Pipelines

## Why

The current harness can build a real category-day panel and run basic diagnostics, LocalGap, and simplified PSM-DID, but the GPS/uplift step still emits stub outputs. That makes reports look polished while part of the analytical evidence chain is still illustrative.

## What

- Replace GPS/uplift stub output with deterministic project-level analysis scripts over `category_day_panel.json`.
- Add dose-response, uplift ranking, and business action recommendations as real workspace artifacts.
- Improve LocalGap and PSM-DID diagnostics so downstream reports can distinguish strong, weak, and directional evidence.
- Keep outputs local, reproducible, and compatible with the current `business_analysis` gateway.

## Impact

- `analysis.run_gps_uplift` becomes an implemented analysis step rather than a placeholder.
- `result.get_latest`, report generation, and dashboard/report surfaces receive richer strategy evidence.
- Existing demo data can produce reasonable, traceable recommendations without claiming production-grade causality.
