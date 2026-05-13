## Design

The panel builder is the first point where raw files, inferred mappings, and standardized numeric columns meet. It will create `measure_units` metadata in `panel_summary.json` for GMV and discount fields.

Unit inference is conservative:

- If the mapped source column includes explicit markers such as `yuan`, `rmb`, `cny`, `元`, `fen`, `分`, `usd`, or `sar`, the unit label reflects that marker.
- If the source column is generic, such as `gmv` or `discount`, the unit label is `GMV原始单位` or `折扣原始单位` and `declared` is false.
- No frontend surface may infer yuan or ten-thousand-yuan solely from numeric magnitude.

Analysis quality gates are generated from the category-day panel and LocalGap enriched panel. The gates flag smoke-test or limited status when date coverage is too short, activity samples are sparse, LocalBaseline support is weak, or channel attribution terms cannot be estimated.

Dashboard recommendations use those gates. If evidence is limited, categories may still be shown for review, but they are grouped under small-scale validation rather than "priority boost". Reports include the unit provenance and limited-evidence reasons near executive and evidence sections.

## Key Choices

- **Source unit over display convenience:** values remain in the raw table's numeric unit; scaling is not guessed in the browser.
- **Quality status travels with artifacts:** panel and LocalGap artifacts carry machine-readable status and reasons so Agent, dashboard, and report stay aligned.
- **Cautious strategy labels:** weak evidence downgrades recommendations rather than hiding real data.
