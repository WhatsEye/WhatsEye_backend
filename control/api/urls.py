from django.urls import path

from .views import (ChildLocationListView, NotificationListView,
                    SetHourlyUsageAPIView, UserUsageAPIView,ScheduleViewSet,
                    ScheduleChildListView, ChildBadWordsView,ChangeChildPasswordAPI,
                    ChildCallRecordingAPIView,ChildCallRecordingUpdateView,ChildCallRecordingPostAPIView, make_read_notifications)

urlpatterns = [
    path('records/<uuid:child_id>/', ChildCallRecordingPostAPIView.as_view(), name='child-records-post'),
    path('records/<uuid:child_id>/update/<int:pk>/', ChildCallRecordingUpdateView.as_view(), name='child-record-update'),
    path('records/<uuid:child_id>/<str:recording_type>/', ChildCallRecordingAPIView.as_view(), name='child-records'),
    path('schedules/', ScheduleChildListView.as_view(),name="child-schedules"),
    path('schedules/<uuid:child_id>/', ScheduleViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('schedules/<uuid:child_id>/<int:pk>/', ScheduleViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'})),
    path(
        "change-password/<uuid:child_id>/",
        ChangeChildPasswordAPI.as_view(),
        name="child-bad-words",
    ),
    path(
        "bad-words/<uuid:child_id>/<str:word>/",
        ChildBadWordsView.as_view(),
        name="delete-child-bad-words",
    ),
    path(
        "bad-words/<uuid:child_id>/",
        ChildBadWordsView.as_view(),
        name="child-bad-words",
    ),
    path("notifications/make/read/<uuid:child_id>/", make_read_notifications, name="make_read_notifications"),
    path(
        "notifications/<uuid:child_id>/<int:pk>/",
        NotificationListView.as_view(),
        name="delete-notification-list",
    ),
    path(
        "notifications/<uuid:child_id>/",
        NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "child-locations/<uuid:child_id>/<int:pk>/",
        ChildLocationListView.as_view(),
        name="delete-child-location-list",
    ),
    path(
        "child-locations/<uuid:child_id>/",
        ChildLocationListView.as_view(),
        name="child-location-list",
    ),
    path("user-usage/", SetHourlyUsageAPIView.as_view(), name="user-usage-set"),
    path(
        "user-usage/<uuid:cid>/hourly/",
        UserUsageAPIView.as_view(),
        name="user-usage-hourly",
    ),
    path(
        "user-usage/<uuid:cid>/daily/",
        UserUsageAPIView.as_view(),
        name="user-usage-daily",
    ),
]
