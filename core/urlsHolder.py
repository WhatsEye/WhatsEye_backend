from django.urls import include, path

urlpatterns = [
    path("accounts/", include("accounts.api.urls")),
    path("control/", include("control.api.urls")),
]
