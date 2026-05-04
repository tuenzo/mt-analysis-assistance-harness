import pytest
import tempfile
import shutil
import os
from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db


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
def project(client):
    r = client.post("/api/projects", json={"name": "FileTest"})
    return r.json()


def test_upload_file(client, project):
    proj_id = project["id"]
    content = b"order_id,gmv,date\n1,100,2026-01-01"
    r = client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order_info.csv", BytesIO(content), "text/csv")},
        data={"role": "order_info"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "order_info"
    assert data["checksum"].startswith("sha256:")


def test_list_files(client, project):
    proj_id = project["id"]
    client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("test.csv", BytesIO(b"a,b\n1,2"), "text/csv")},
        data={"role": "unknown"},
    )
    r = client.get(f"/api/projects/{proj_id}/files")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_infer_schema(client, project):
    proj_id = project["id"]
    content = b"order_id,pay_time,gmv,discount,category\n1,2026-01-01,100,10,food"
    client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order_info.csv", BytesIO(content), "text/csv")},
        data={"role": "order_info"},
    )
    r = client.post(f"/api/projects/{proj_id}/files/infer-schema")
    assert r.status_code == 200
    data = r.json()["data"]["files"]
    assert len(data) >= 1
    assert "columns" in data[0]


def test_apply_schema(client, project):
    proj_id = project["id"]
    content = b"order_id,gmv\n1,100"
    upload = client.post(
        f"/api/projects/{proj_id}/files",
        files={"file": ("order.csv", BytesIO(content), "text/csv")},
        data={"role": "unknown"},
    )
    file_id = upload.json()["file_id"]

    r = client.post(f"/api/projects/{proj_id}/schema/apply", json={
        "mappings": {file_id: {"order_id": "order_id", "gmv": "gmv"}}
    })
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "mapped"
