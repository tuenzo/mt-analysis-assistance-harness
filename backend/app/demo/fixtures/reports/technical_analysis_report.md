# Keemart Demo 技术分析报告

## 数据

- Raw files: order_info.csv, exposure_info.csv, activity_timeline.csv
- Processed panel: category_date_panel.csv
- Grain: category x date

## 方法

1. Schema inference validates core fields.
2. Panel build aggregates GMV, orders, discounts, exposure, and activity flags.
3. Diagnostics compare active and non-active periods.
4. LocalGap separates natural cycle movement from promotion-attributed residual.

## Demo Result

The seeded result is intentionally small and deterministic. It exists to validate the harness, not algorithmic precision.
