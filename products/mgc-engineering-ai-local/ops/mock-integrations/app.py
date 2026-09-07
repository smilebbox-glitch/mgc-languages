from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, Response

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"
app = FastAPI(title="MGC Integration Simulator", version="1.0")

ASSETS = [
    {
        "external_id": "PLM-DOC-001",
        "name": "8450012345_REV_D_test_report.txt",
        "kind": "test_report",
        "part_number": "8450012345",
        "revision": "D",
        "project_code": "DEMO-RD",
        "modified_at": "2026-09-04T08:00:00Z",
        "download_url": "/api/assets/PLM-DOC-001/content",
    },
    {
        "external_id": "PLM-DOC-002",
        "name": "8450012345_REV_D_ECR-2041.txt",
        "kind": "change_request",
        "part_number": "8450012345",
        "revision": "D",
        "project_code": "DEMO-RD",
        "modified_at": "2026-09-04T08:05:00Z",
        "download_url": "/api/assets/PLM-DOC-002/content",
    },
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "integration-simulator"}


@app.get("/api/assets")
def assets(cursor: str | None = None, limit: int = 100):
    offset = int(cursor or 0)
    page = ASSETS[offset:offset + limit]
    next_cursor = offset + len(page)
    return {"items": page, "next_cursor": str(next_cursor) if next_cursor < len(ASSETS) else None}


@app.get("/api/assets/{external_id}/content")
def asset_content(external_id: str):
    mapping = {
        "PLM-DOC-001": "8450012345_REV_D_test_report.txt",
        "PLM-DOC-002": "8450012345_REV_D_ECR-2041.txt",
    }
    name = mapping.get(external_id)
    if not name:
        return Response(status_code=404)
    return FileResponse(SAMPLES / name, filename=name)


@app.get("/api/boms")
def boms(cursor: str | None = None, limit: int = 100):
    items = [{
        "id": "BOM-8450012345-D",
        "part_number": "8450012345",
        "revision": "D",
        "modified_at": "2026-09-04T08:10:00Z",
    }]
    return {"items": items, "next_cursor": None}


@app.get("/api/boms/{external_id}")
def bom_detail(external_id: str):
    return {"items": [
        {"child_part_number": "FASTENER-001", "child_revision": "A", "quantity": 4, "description": "Mounting fastener"},
        {"child_part_number": "BUSH-004", "child_revision": "B", "quantity": 2, "description": "Isolation bush"},
    ]}


@app.get("/capabilities")
def capabilities():
    return {
        "mode": "SIMULATOR_ONLY",
        "formats": ["CATPart", "CATProduct", "PRT", "JT", "SLDPRT", "SLDASM", "M3D", "A3D", "T3D", "CDW", "FRW", "GRB"],
        "targets": ["STEP", "PDF", "DXF"],
        "note": "Replace this simulator with a licensed CAD SDK gateway for production.",
    }


@app.post("/convert")
async def convert(target_format: str = "step", file: UploadFile = File(...)):
    # The simulator does not parse proprietary CAD. It returns a deterministic
    # sample STEP so the conversion workflow, provenance and downstream CAD
    # analysis can be tested end to end without a commercial SDK.
    content = (SAMPLES / "8450012345_REV_D_mounting_plate.step").read_bytes()
    return Response(
        content=content,
        media_type="application/step",
        headers={"X-CAD-SDK": "MGC-SIMULATOR", "X-CAD-SDK-Version": "1.0", "X-CAD-Target-Format": "step", "X-CAD-Vendor": "simulator"},
    )
