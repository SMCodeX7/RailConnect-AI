from fastapi import APIRouter

from railconnect.modules.stations.routes import router as stations_router

router = APIRouter(prefix="/api/v1")
router.include_router(stations_router)
