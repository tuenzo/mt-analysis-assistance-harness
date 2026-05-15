import pytest
import tempfile
import shutil
import os
import csv
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db
from app.projects.service import ProjectService
from app.analysis.pipelines.build_panel import _find_role_files, validate_files


@pytest.fixture
def test_db():
    tmp = tempfile.mkdtemp()
    os.chdir(tmp)
    init_db()
    yield
    os.chdir("..")
    shutil.rmtree(tmp)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def project_with_data(client):
    r = client.post("/api/projects", json={"name": "ValidateTest"})
    project = r.json()

    workspace_path = Path(f"./workspaces/{project['id']}")
    data_dir = workspace_path / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)

    order_csv = data_dir / "order_info.csv"
    with open(order_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "user_id", "category", "date", "gmv", "discount"])
        writer.writeheader()
        writer.writerows([
            {"order_id": "o1", "user_id": "u1", "category": "food", "date": "2024-01-01", "gmv": "100", "discount": "10"},
            {"order_id": "o2", "user_id": "u2", "category": "food", "date": "2024-01-01", "gmv": "200", "discount": "20"},
        ])

    exposure_csv = data_dir / "exposure_info.csv"
    with open(exposure_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "exposure"])
        writer.writeheader()
        writer.writerows([
            {"category": "food", "date": "2024-01-01", "exposure": "500"},
        ])

    activity_csv = data_dir / "activity_timeline.csv"
    with open(activity_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "date", "payday", "activity_id"])
        writer.writeheader()
        writer.writerows([
            {"category": "food", "date": "2024-01-01", "payday": "1", "activity_id": "act1"},
        ])

    return project


def test_validate_missing_files_returns_error(test_db):
    tmp_dir = tempfile.mkdtemp()
    try:
        val_result = validate_files(Path(tmp_dir))
        assert val_result.ok is False
        assert len(val_result.issues) > 0
    finally:
        shutil.rmtree(tmp_dir)


def test_validate_success(project_with_data):
    workspace_path = Path(f"./workspaces/{project_with_data['id']}")
    val_result = validate_files(workspace_path)
    assert val_result.ok is True


def test_validate_detects_missing_columns(test_db):
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    try:
        workspace_path = Path(f"./workspaces/test_missing_cols")
        data_dir = workspace_path / "data" / "raw"
        data_dir.mkdir(parents=True)

        bad_csv = data_dir / "order_info.csv"
        with open(bad_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["order_id", "category", "date"])
            writer.writeheader()
            writer.writerow({"order_id": "o1", "category": "food", "date": "2024-01-01"})

        val_result = validate_files(workspace_path)
        assert val_result.ok is False
        assert any("gmv" in issue.lower() for issue in val_result.issues)
    finally:
        os.chdir("..")
        shutil.rmtree(tmp_dir)


def test_validate_accepts_common_alias_columns(test_db):
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    try:
        workspace_path = Path("./workspaces/test_alias_cols")
        data_dir = workspace_path / "data" / "raw"
        data_dir.mkdir(parents=True)

        with open(data_dir / "orders.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["pay_date", "cat_name", "pay_amount"])
            writer.writeheader()
            writer.writerow({"pay_date": "20250927", "cat_name": "Snacks", "pay_amount": "100"})

        with open(data_dir / "exposure.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["dt", "cat_name", "exposure"])
            writer.writeheader()
            writer.writerow({"dt": "20250927", "cat_name": "Snacks", "exposure": "1000"})

        with open(data_dir / "activity_timeline.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["start_date", "end_date", "activity"])
            writer.writeheader()
            writer.writerow({"start_date": "2025-09-27", "end_date": "2025-09-27", "activity": "Payday"})

        val_result = validate_files(workspace_path)
        assert val_result.ok is True
        assert val_result.file_info["order_info"]["recommended_mappings"]["gmv"] == "pay_amount"
    finally:
        os.chdir("..")
        shutil.rmtree(tmp_dir)


def test_validate_accepts_realdata_chinese_activity_headers(test_db):
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    try:
        workspace_path = Path("./workspaces/test_realdata_alias_cols")
        data_dir = workspace_path / "data" / "raw"
        data_dir.mkdir(parents=True)

        with open(data_dir / "①Keemat业务选题_order_info_脱敏数据表.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "dt",
                    "stat_pay_user_id",
                    "stat_pay_main_order_id",
                    "category_name_cn",
                    "base_sku_id",
                    "sku_sale_amt",
                    "sku_sale_num",
                    "biz_total_discount_amt",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "dt": "2025-09-27",
                    "stat_pay_user_id": "u1",
                    "stat_pay_main_order_id": "o1",
                    "category_name_cn": "饮料",
                    "base_sku_id": "sku1",
                    "sku_sale_amt": "100",
                    "sku_sale_num": "2",
                    "biz_total_discount_amt": "10",
                }
            )

        with open(data_dir / "②Keemart业务选题_exposure_info_脱敏数据表.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["dt", "base_sku_id", "buy_uv", "view_uv"])
            writer.writeheader()
            writer.writerow({"dt": "2025-09-27", "base_sku_id": "sku1", "buy_uv": "10", "view_uv": "100"})

        with open(data_dir / "③Keemart业务选题_activity_timeline_脱敏数据表.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["日期", "营销活动"])
            writer.writeheader()
            writer.writerow({"日期": "2025-09-27", "营销活动": "发薪日促销"})

        val_result = validate_files(workspace_path)

        assert val_result.ok is True
        assert val_result.file_info["activity_timeline"]["recommended_mappings"]["date"] == "日期"
        assert val_result.file_info["activity_timeline"]["recommended_mappings"]["activity_name"] == "营销活动"
        assert val_result.file_info["order_info"]["recommended_mappings"]["quantity"] == "sku_sale_num"
    finally:
        os.chdir("..")
        shutil.rmtree(tmp_dir)


def test_role_file_selection_prefers_exact_role_names_over_legacy_processed_files(test_db):
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)
    try:
        data_dir = Path("./workspaces/test_role_selection/data/raw")
        data_dir.mkdir(parents=True)
        (data_dir / "baseline_processed_orders.csv").write_text(
            "dt,category_name_cn,sku_sale_amt\n2025-09-27,饮料,100\n",
            encoding="utf-8",
        )
        (data_dir / "category_date_panel.csv").write_text(
            "dt,category_name_cn,gmv,exposure_view_uv,is_activity_day\n2025-09-27,饮料,100,200,1\n",
            encoding="utf-8",
        )
        (data_dir / "①Keemat业务选题_order_info_脱敏数据表.csv").write_text(
            "dt,category_name_cn,sku_sale_amt\n2025-09-27,饮料,100\n",
            encoding="utf-8",
        )

        files = _find_role_files(data_dir)

        assert files["order_info"].name == "①Keemat业务选题_order_info_脱敏数据表.csv"
    finally:
        os.chdir("..")
        shutil.rmtree(tmp_dir)
