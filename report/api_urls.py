from django.urls import path,include
from .views import *
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register("reports", ReportViewSet)
router.register("getreports", GetReportViewSet)
router.register("dropdownvalue", DropdownValueViewSet)
router.register("domainlist", DomainListViewSet)
router.register("sightings", SightingViewSet)
router.register("comments", CommentViewSet)
router.register("watchlist", WatchlistViewSet)
router.register("profile", ProfileViewSet)
router.register("profiledetail", ProfileTokenViewSet)
router.register("article", ArticleViewSet)
router.register("allreportlist", NewReportViewSet)
router.register("reportupdate", ReportUpdateViewSet)
router.register("notification", NotificationHistoryViewset)

# urlpatterns = router.urls

urlpatterns = [ 
    # path('api/', include(router.urls)),
    path('', include(router.urls)),
    # path('allreportlist/', ReportList.as_view(), name="allreportlist"),
    path('reportactivity/', ReportActivityList.as_view(), name="reportactivity"),
    path('sightactivity/', SightActivityList.as_view(), name="sightactivity"),
    path('watchlistactivity/', WatchlistActivityList.as_view(), name="watchlistactivity"),
    path('mytask/', MyTaskList.as_view(), name="mytask"),
]
