from django.urls import path
from .views import UserUsageAPIView, SetHourlyUsageAPIView

urlpatterns = [
    path('user-usage/<uuid:cid>/', SetHourlyUsageAPIView.as_view(), name='user-usage-set'),
    path('user-usage/<uuid:cid>/hourly/', UserUsageAPIView.as_view(), name='user-usage-hourly'),
    path('user-usage/<uuid:cid>/daily/', UserUsageAPIView.as_view(), name='user-usage-daily'),
]
