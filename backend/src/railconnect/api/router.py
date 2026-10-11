from fastapi import APIRouter

from railconnect.modules.journeys.routes import router as journeys_router
from railconnect.modules.stations.routes import router as stations_router

router = APIRouter(prefix="/api/v1")
router.include_router(stations_router)
router.include_router(journeys_router)
