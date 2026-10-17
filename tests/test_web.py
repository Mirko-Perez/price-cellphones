from fastapi.testclient import TestClient

from pricecomp.web.app import app

client = TestClient(app)


def test_defaults():
    d = client.get("/api/defaults").json()
    assert d["margin_min"] > 0 and "personal" in d["sources"]


def test_upload_rejects_non_pdf():
    r = client.post("/api/upload", files={"file": ("x.pdf", b"hola", "application/pdf")})
    assert r.status_code == 400


def test_unknown_job_and_file():
    assert client.get("/api/jobs/nope").status_code == 404
    assert client.post("/api/compare", json={"file_id": "nope"}).status_code == 404
