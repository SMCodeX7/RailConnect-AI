from fastapi import APIRouter

from railconnect.modules.identity.routes import router as auth_router
from railconnect.modules.incidents.audit_routes import router as audit_router
from railconnect.modules.incidents.lifecycle_routes import router as lifecycle_router
from railconnect.modules.incidents.public_routes import router as public_incidents_router
from railconnect.modules.incidents.report_routes import router as reports_router
from railconnect.modules.incidents.review_routes import router as review_router
from railconnect.modules.journeys.routes import router as journeys_router
from railconnect.modules.stations.routes import router as stations_router

router = APIRouter(prefix="/api/v1")
router.include_router(stations_router)
router.include_router(journeys_router)
router.include_router(auth_router)
router.include_router(reports_router)
router.include_router(review_router)
router.include_router(lifecycle_router)
router.include_router(audit_router)
router.include_router(public_incidents_router)
