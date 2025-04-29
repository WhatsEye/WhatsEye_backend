from django.urls import path
from .views import UserUsageAPIView, SetHourlyUsageAPIView, ChildLocationListView,NotificationListView

urlpatterns = [
    path('notifications/<uuid:child_id>/', NotificationListView.as_view(), name='notification-list'),
    path('child-locations/<uuid:child_id>/', ChildLocationListView.as_view(), name='child-location-list'),    
    path('user-usage/', SetHourlyUsageAPIView.as_view(), name='user-usage-set'),
    path('user-usage/<uuid:cid>/hourly/', UserUsageAPIView.as_view(), name='user-usage-hourly'),
    path('user-usage/<uuid:cid>/daily/', UserUsageAPIView.as_view(), name='user-usage-daily'),
]
