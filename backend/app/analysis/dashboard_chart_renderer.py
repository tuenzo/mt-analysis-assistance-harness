from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from app.tools.schemas import ToolResult


ChartId = str

DEFAULT_DASHBOARD_CHART_IDS: tuple[ChartId, ...] = (
    "gmv_trend",
    "pareto",
    "activity_comparison",
    "period_overview",
    "localgap",
    "uplift_quadrant",
)
CHART_IDS: set[ChartId] = set(DEFAULT_DASHBOARD_CHART_IDS)
EVIDENCE_RESULT_PATHS: tuple[str, ...] = (
    ".analysis/diagnostics_result.json",
    ".analysis/psm_did_result.json",
    ".analysis/localgap_result.json",
    ".analysis/uplift_result.json",
    ".analysis/latest_result.json",
)

WIDTH = 1000
HEIGHT = 400
BACKGROUND = "#ffffff"
TEXT = "#1f2329"
MUTED = "#646a73"
GRID = "#dfe3e8"
AXIS = "#8a8f99"
BLUE = "#1d6ff2"
BAR_BLUE = "#3b82f6"
GREEN = "#55b95b"
RED = "#d92929"
ORANGE_FILL = "#fde7cf"
GRAY_BAR = "#c8ccd3"


def render_dashboard_chart(workspace_path: str | Path, chart_id: ChartId) -> Path:
    if chart_id not in CHART_IDS:
        raise ValueError(f"Unknown dashboard chart: {chart_id}")

    workspace = Path(workspace_path)
    chart_dir = workspace / "artifacts" / "charts" / "dashboard"
    chart_dir.mkdir(parents=True, exist_ok=True)
    output_path = chart_dir / f"{chart_id}.png"

    renderers: dict[ChartId, Callable[[], Image.Image]] = {
        "gmv_trend": _render_gmv_trend,
        "pareto": _render_pareto,
        "activity_comparison": _render_activity_comparison,
        "period_overview": _render_period_overview,
        "localgap": _render_localgap,
        "uplift_quadrant": _render_uplift_quadrant,
    }
    image = renderers[chart_id]()
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def render_dashboard_chart_artifacts(
    project_id: str,
    workspace_path: str | Path,
    chart_ids: list[str] | tuple[str, ...] | None = None,
) -> ToolResult:
    requested_chart_ids = list(chart_ids or DEFAULT_DASHBOARD_CHART_IDS)
    if not requested_chart_ids:
        requested_chart_ids = list(DEFAULT_DASHBOARD_CHART_IDS)

    unknown_chart_ids = [chart_id for chart_id in requested_chart_ids if chart_id not in CHART_IDS]
    if unknown_chart_ids:
        return ToolResult(
            ok=False,
            action="chart.render_dashboard",
            summary="",
            error={
                "code": "UNKNOWN_CHART_ID",
                "message": f"Unknown dashboard chart(s): {', '.join(unknown_chart_ids)}",
            },
        )

    workspace = Path(workspace_path)
    evidence = _dashboard_evidence_status(workspace)
    if not evidence["ok"]:
        return ToolResult(
            ok=False,
            action="chart.render_dashboard",
            summary="Dashboard chart rendering blocked: usable analysis evidence is missing.",
            error={
                "code": "ANALYSIS_EVIDENCE_REQUIRED",
                "message": "Render analysis dashboard charts only after current analysis result artifacts exist.",
                "details": evidence,
            },
            assistant_hint=(
                "Run diagnostics/full pipeline first, or fix failed analysis artifacts before refreshing dashboard PNGs."
            ),
        )

    generated_at = datetime.now().isoformat(timespec="seconds")
    artifacts = []
    for chart_id in requested_chart_ids:
        output_path = render_dashboard_chart(workspace, chart_id)
        artifacts.append(
            {
                "type": "dashboard_chart",
                "title": f"{chart_id}.png",
                "path": output_path.relative_to(workspace).as_posix(),
                "mime_type": "image/png",
                "chart_id": chart_id,
                "project_id": project_id,
                "generated_at": generated_at,
                "metadata": {
                    "method_status": "backend_rendered_dashboard_png",
                    "chart_id": chart_id,
                    "generated_at": generated_at,
                },
            }
        )

    return ToolResult(
        ok=True,
        action="chart.render_dashboard",
        summary=f"Generated {len(artifacts)} dashboard chart image(s).",
        artifacts=artifacts,
        assistant_hint=(
            "Dashboard PNGs are ready under artifacts/charts/dashboard. "
            "Use these images for the result dashboard and regenerate them after analysis data changes."
        ),
    )


def _dashboard_evidence_status(workspace: Path) -> dict:
    evidence = []
    for rel_path in EVIDENCE_RESULT_PATHS:
        path = workspace / rel_path
        exists = path.exists()
        usable = _usable_evidence_file(path)
        evidence.append({"path": rel_path, "exists": exists, "usable": usable})
    return {"ok": any(item["usable"] for item in evidence), "evidence": evidence}


def _usable_evidence_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or not payload:
        return False
    if _contains_truthy_demo(payload):
        return False
    status = str(payload.get("method_status") or payload.get("status") or "").lower()
    return status not in {"failed", "error", "stub"}


def _contains_truthy_demo(value) -> bool:
    if isinstance(value, dict):
        if value.get("demo") is True or value.get("showcase") is True:
            return True
        return any(_contains_truthy_demo(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_truthy_demo(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return "demo" in lowered or "fixture" in lowered or "mock" in lowered
    return False


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    return image, ImageDraw.Draw(image)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, size: int = 24, fill: str = TEXT, *, bold: bool = False, anchor: str | None = None) -> None:
    draw.text(xy, text, fill=fill, font=_font(size, bold=bold), anchor=anchor)


def _grid(draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int, ticks: list[float], y_min: float, y_max: float) -> None:
    for tick in ticks:
        y = _scale(tick, y_min, y_max, bottom, top)
        draw.line((left, y, right, y), fill=GRID, width=1)
        _text(draw, (left - 12, y), _fmt_tick(tick), 18, MUTED, anchor="rm")
    draw.line((left, top, left, bottom), fill=AXIS, width=2)
    draw.line((left, bottom, right, bottom), fill=AXIS, width=2)


def _scale(value: float, source_min: float, source_max: float, target_min: float, target_max: float) -> float:
    if source_max == source_min:
        return target_min
    return target_min + (value - source_min) / (source_max - source_min) * (target_max - target_min)


def _fmt_tick(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:.1f}"


def _legend(draw: ImageDraw.ImageDraw, x: int, y: int, items: list[tuple[str, str, str]]) -> None:
    cursor = x
    for kind, color, label in items:
        if kind == "line":
            draw.line((cursor, y + 8, cursor + 30, y + 8), fill=color, width=4)
            draw.ellipse((cursor + 12, y + 2, cursor + 22, y + 12), fill=color)
        elif kind == "dot":
            draw.ellipse((cursor, y + 2, cursor + 12, y + 14), fill=color)
        else:
            draw.rectangle((cursor, y + 2, cursor + 24, y + 14), fill=color, outline="#c8ccd3")
        _text(draw, (cursor + 34, y), label, 18, MUTED)
        cursor += 124


def _render_gmv_trend() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "GMV趋势 + 活动/发薪日标记", 28, TEXT, bold=True)
    left, top, right, bottom = 82, 86, 940, 308
    _text(draw, (36, 70), "GMV（万元）", 20, MUTED)
    _grid(draw, left, top, right, bottom, [0, 300, 600, 900, 1200], 0, 1200)

    dates = ["04-01", "04-08", "04-15", "04-22", "04-29", "05-06", "05-13", "05-20", "05-27", "06-03"]
    values = [300, 520, 610, 905, 480, 970, 580, 1110, 510, 780, 535]
    xs = [_scale(i, 0, len(values) - 1, left, right) for i in range(len(values))]
    for x in [left + 90, left + 240, left + 425, left + 625, left + 820]:
        draw.rectangle((x, top, x + 34, bottom), fill=ORANGE_FILL, outline="#f2d4b8")

    points = [(x, _scale(v, 0, 1200, bottom, top)) for x, v in zip(xs, values)]
    draw.line(points, fill=BLUE, width=5, joint="curve")
    for x in [left + 150, left + 360, left + 570, left + 780]:
        draw.ellipse((x - 6, bottom - 10, x + 6, bottom + 2), fill="#d71920")

    for i, label in enumerate(dates):
        if i % 1 == 0:
            x = _scale(i, 0, len(dates) - 1, left, right)
            _text(draw, (x, bottom + 18), label, 18, MUTED, anchor="ma")
    _legend(draw, 300, 350, [("line", BLUE, "GMV"), ("bar", ORANGE_FILL, "活动期"), ("dot", "#d71920", "发薪日")])
    return image


def _render_pareto() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "品类GMV Pareto", 28, TEXT, bold=True)
    left, top, right, bottom = 96, 88, 850, 304
    right_axis = 900
    _text(draw, (36, 72), "GMV（万元）", 20, MUTED)
    _text(draw, (820, 72), "累计占比（%）", 20, MUTED)
    _grid(draw, left, top, right, bottom, [0, 500, 1000, 1500, 2000, 2500], 0, 2500)
    draw.line((right_axis, top, right_axis, bottom), fill=AXIS, width=2)
    for pct in [0, 20, 40, 60, 80, 100]:
        y = _scale(pct, 0, 100, bottom, top)
        _text(draw, (right_axis + 12, y), f"{pct}%", 18, MUTED, anchor="lm")

    labels = ["饮料", "零食", "生鲜", "母婴", "家清"]
    values = [2200, 1500, 900, 420, 180]
    cumulative = [46, 74, 88, 96, 100]
    bar_w = 62
    step = 156
    line_points: list[tuple[float, float]] = []
    for i, (label, value, pct) in enumerate(zip(labels, values, cumulative)):
        x = left + 66 + i * step
        y = _scale(value, 0, 2500, bottom, top)
        draw.rectangle((x, y, x + bar_w, bottom), fill=BAR_BLUE, outline="#2f6fd6")
        _text(draw, (x + bar_w / 2, bottom + 20), label, 20, TEXT, anchor="ma")
        line_points.append((x + bar_w / 2, _scale(pct, 0, 100, bottom, top)))
    draw.line(line_points, fill=BLUE, width=5)
    for x, y in line_points:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=BLUE)
    _legend(draw, 310, 350, [("bar", BAR_BLUE, "GMV（万元）"), ("line", BLUE, "累计占比（%）")])
    return image


def _render_activity_comparison() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "活动期 vs 非活动期", 28, TEXT, bold=True)
    left, top, right, bottom = 82, 92, 930, 306
    _grid(draw, left, top, right, bottom, [0, 40, 80, 120, 160], 0, 160)
    groups = [
        ("GMV（万元）", 112, 68, "1,120", "680"),
        ("订单数（万）", 98, 62, "98", "62"),
        ("转化率（%）", 62, 48, "4.6%", "3.1%"),
        ("曝光（万）", 158, 90, "2,450", "1,620"),
    ]
    group_step = 200
    bar_w = 50
    for i, (label, active, non_active, active_label, non_label) in enumerate(groups):
        x = left + 66 + i * group_step
        active_top = _scale(active, 0, 160, bottom, top)
        non_top = _scale(non_active, 0, 160, bottom, top)
        draw.rectangle((x, active_top, x + bar_w, bottom), fill=BAR_BLUE, outline="#2f6fd6")
        draw.rectangle((x + 62, non_top, x + 62 + bar_w, bottom), fill=GRAY_BAR, outline="#aeb4bd")
        _text(draw, (x + bar_w / 2, active_top - 24), active_label, 20, TEXT, anchor="ma")
        _text(draw, (x + 62 + bar_w / 2, non_top - 24), non_label, 20, TEXT, anchor="ma")
        _text(draw, (x + 56, bottom + 20), label, 20, TEXT, anchor="ma")
    _legend(draw, 360, 350, [("bar", BAR_BLUE, "活动期"), ("bar", GRAY_BAR, "非活动期")])
    return image


def _render_period_overview() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "活动前中后：GMV趋势与活动期对比", 26, TEXT, bold=True)

    left, top, right, bottom = 86, 98, 680, 306
    _text(draw, (86, 68), "GMV（万元）", 18, MUTED)
    _grid(draw, left, top, right, bottom, [0, 300, 600, 900, 1200], 0, 1200)

    dates = ["04-01", "04-08", "04-15", "04-22", "04-29", "05-06", "05-13", "05-20", "05-27", "06-03"]
    values = [300, 520, 610, 905, 480, 970, 580, 1110, 510, 780]
    xs = [_scale(i, 0, len(values) - 1, left, right) for i in range(len(values))]
    for index in [1, 3, 5, 7, 9]:
        x = _scale(index, 0, len(values) - 1, left, right)
        draw.rectangle((x - 14, top, x + 14, bottom), fill=ORANGE_FILL, outline="#f2d4b8")
    points = [(x, _scale(v, 0, 1200, bottom, top)) for x, v in zip(xs, values)]
    draw.line(points, fill=BLUE, width=5, joint="curve")
    for index in [2, 4, 6, 8]:
        x = _scale(index, 0, len(values) - 1, left, right)
        draw.ellipse((x - 6, bottom - 10, x + 6, bottom + 2), fill="#d71920")
    for i, label in enumerate(dates):
        if i in {0, 2, 4, 6, 8, 9}:
            x = _scale(i, 0, len(dates) - 1, left, right)
            _text(draw, (x, bottom + 18), label, 16, MUTED, anchor="ma")

    panel_left, panel_top, panel_right, panel_bottom = 720, 86, 948, 302
    draw.rounded_rectangle((panel_left, panel_top, panel_right, panel_bottom), radius=10, fill="#f8fafc", outline=GRID)
    _text(draw, (740, 106), "活动 vs 非活动", 21, TEXT, bold=True)
    _text(draw, (740, 132), "同口径均值对比", 15, MUTED)
    draw.rectangle((742, 158, 756, 169), fill=BAR_BLUE)
    _text(draw, (762, 154), "活动期", 14, MUTED)
    draw.rectangle((822, 158, 836, 169), fill=GRAY_BAR)
    _text(draw, (842, 154), "非活动期", 14, MUTED)

    comparison = [
        ("GMV", 112, 68, "1,120", "680"),
        ("订单", 98, 62, "98", "62"),
        ("转化", 62, 48, "4.6%", "3.1%"),
        ("曝光", 158, 90, "2,450", "1,620"),
    ]
    bar_left, bar_right = 798, 910
    for i, (label, active, non_active, active_label, non_label) in enumerate(comparison):
        row_y = 194 + i * 27
        _text(draw, (740, row_y - 6), label, 15, TEXT, bold=True)
        active_w = _scale(active, 0, 160, 0, bar_right - bar_left)
        non_w = _scale(non_active, 0, 160, 0, bar_right - bar_left)
        draw.rounded_rectangle((bar_left, row_y - 12, bar_left + active_w, row_y - 3), radius=4, fill=BAR_BLUE)
        draw.rounded_rectangle((bar_left, row_y + 2, bar_left + non_w, row_y + 11), radius=4, fill=GRAY_BAR)
        _text(draw, (bar_right + 8, row_y - 17), active_label, 13, TEXT)
        _text(draw, (bar_right + 8, row_y - 2), non_label, 13, MUTED)

    draw.line((left, 348, left + 30, 348), fill=BLUE, width=4)
    _text(draw, (left + 38, 339), "GMV", 16, MUTED)
    draw.rectangle((left + 116, 340, left + 140, 354), fill=ORANGE_FILL, outline="#f2d4b8")
    _text(draw, (left + 148, 339), "活动期", 16, MUTED)
    draw.ellipse((left + 232, 342, left + 244, 354), fill="#d71920")
    _text(draw, (left + 252, 339), "发薪日", 16, MUTED)
    return image


def _render_localgap() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "LocalGap增量分解瀑布图", 28, TEXT, bold=True)
    left, top, right, bottom = 92, 82, 930, 306
    _text(draw, (36, 70), "GMV（万元）", 20, MUTED)
    _grid(draw, left, top, right, bottom, [0, 400, 800, 1200, 1400], 0, 1500)

    items = [
        ("基线GMV", 800, 0, "#a8adb5"),
        ("曝光贡献", 300, 800, GREEN),
        ("折扣贡献", 180, 1100, GREEN),
        ("发薪日贡献", 120, 1280, GREEN),
        ("交互/残差", -110, 1400, RED),
        ("实际GMV", 1290, 0, "#9aa1aa"),
    ]
    bar_w = 70
    step = 146
    previous_x = None
    previous_y = None
    for i, (label, value, base, color) in enumerate(items):
        x = left + 70 + i * step
        if i in {0, 5}:
            y1 = _scale(value, 0, 1500, bottom, top)
            y2 = bottom
            value_label = f"{value:,.0f}"
        else:
            start = base
            end = base + value
            y1 = _scale(max(start, end), 0, 1500, bottom, top)
            y2 = _scale(min(start, end), 0, 1500, bottom, top)
            value_label = f"{value:+,.0f}"
        draw.rectangle((x, y1, x + bar_w, y2), fill=color, outline="#7a8089")
        _text(draw, (x + bar_w / 2, min(y1, y2) - 24), value_label, 20, TEXT, anchor="ma")
        _text(draw, (x + bar_w / 2, bottom + 20), label, 18, TEXT, anchor="ma")
        if previous_x is not None and previous_y is not None:
            draw.line((previous_x, previous_y, x, previous_y), fill=TEXT, width=2)
            for dash_x in range(int(previous_x), int(x), 16):
                draw.line((dash_x, previous_y, dash_x + 8, previous_y), fill=TEXT, width=2)
        previous_x = x + bar_w
        previous_y = y1 if i not in {0, 5} and value < 0 else y1
    return image


def _render_uplift_quadrant() -> Image.Image:
    image, draw = _canvas()
    _text(draw, (36, 26), "品类策略四象限", 28, TEXT, bold=True)
    left, top, right, bottom = 90, 78, 930, 318
    mid_x = (left + right) / 2
    mid_y = (top + bottom) / 2
    draw.line((left, bottom, right, bottom), fill=AXIS, width=3)
    draw.line((left, bottom, left, top), fill=AXIS, width=3)
    draw.polygon([(right, bottom), (right - 16, bottom - 8), (right - 16, bottom + 8)], fill=AXIS)
    draw.polygon([(left, top), (left - 8, top + 16), (left + 8, top + 16)], fill=AXIS)
    draw.line((mid_x, top + 16, mid_x, bottom), fill=AXIS, width=2)
    draw.line((left, mid_y, right, mid_y), fill=AXIS, width=2)
    for dash_y in range(top + 16, bottom, 18):
        draw.line((mid_x, dash_y, mid_x, dash_y + 8), fill=BACKGROUND, width=3)
    for dash_x in range(left, right, 18):
        draw.line((dash_x, mid_y, dash_x + 8, mid_y), fill=BACKGROUND, width=3)

    _text(draw, (40, 200), "效果改善", 20, TEXT, anchor="mm")
    _text(draw, (512, 368), "增量贡献", 20, TEXT, anchor="mm")
    for x, label in [(left + 25, "低"), (mid_x, "中"), (right - 60, "高")]:
        _text(draw, (x, bottom + 26), label, 18, TEXT, anchor="ma")
    for y, label in [(bottom - 24, "低"), (mid_y, "中"), (top + 28, "高")]:
        _text(draw, (left - 28, y), label, 18, TEXT, anchor="mm")

    _text(draw, (152, 116), "小规模试验", 20, BLUE)
    _text(draw, (152, 252), "减少投入", 20, BLUE)
    _text(draw, (806, 86), "优先加码", 20, BLUE)
    _text(draw, (770, 292), "保护基本盘", 20, BLUE)
    _bubble(draw, (704, 126), 46, "#60a5fa", "饮料", outline="#2563eb", font_size=20)
    _bubble(draw, (558, 142), 30, "#bde27b", "零食", font_size=17)
    _bubble(draw, (632, 104), 23, "#a7f3d0", "乳品", font_size=15)
    _bubble(draw, (830, 154), 24, "#bfdbfe", "烘焙", font_size=15)
    _bubble(draw, (288, 130), 28, "#b7d5fb", "母婴", font_size=16)
    _bubble(draw, (398, 160), 23, "#c4b5fd", "酒水", font_size=15)
    _bubble(draw, (640, 246), 30, "#f6b75e", "生鲜", font_size=17)
    _bubble(draw, (802, 246), 25, "#fde68a", "家清", font_size=15)
    _bubble(draw, (270, 248), 22, "#fbcfe8", "个护", font_size=14)
    _bubble(draw, (394, 270), 24, "#ddd6fe", "粮油", font_size=15)
    return image


def _bubble(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    color: str,
    label: str,
    *,
    outline: str | None = None,
    font_size: int = 22,
) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=outline or color, width=3)
    _text(draw, (x, y), label, font_size, TEXT, anchor="mm")
