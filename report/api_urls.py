from .views import ReportViewSet, SightingViewSet
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register("reports", ReportViewSet)
router.register("sightings", SightingViewSet)

urlpatterns = router.urls
