from fastapi import APIRouter

from app.demo.seed import DemoSeedService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/status")
def demo_status():
    return {"ok": True, "data": DemoSeedService().status()}
