from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework import routers

from django.urls import path
from .views import (
    ResetPasswordAPI,
    ResetPasswordPhoneAPI,
    resendResetPasswordAPI,
    parentInvitationAPI,
    ChangePasswordAPI,
    CodeResetAPI,
    RegisterFamilyAPI,
    RegisterParentAPI,
    RegisterChildAPI,
    # SetPasskeyView,
    # UpdatePasskeyView,
    # RegisterParentAPI,
    # JoinFamilyParentAPI,
    # JoinFamilyChildAPI,
    # FamilyViewSet
)
from .auth import MyTokenObtainPairView

app_name = "accounts"


router = routers.DefaultRouter()
# router.register(r"register/family", FamilyViewSet)


urlpatterns = [
    # path('child/passlock/set/', SetPasskeyView.as_view(), name='set-passlock'),
    # path('child/passlock/update/<uuid:cid>/', UpdatePasskeyView.as_view(), name='update-passlock'),

    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path(
        "token/parent/",
        MyTokenObtainPairView.as_view(),
        name="token_obtain_pair_parent",
    ),
    path(
        "token/child/<uuid:pid>/<str:code>/",
        MyTokenObtainPairView.as_view(),
        name="token_obtain_pair_child",
    ),
    path(
        "invitation/parent/<str:email>/", parentInvitationAPI, name="invitation_parent"
    ),
    path("register/family/", RegisterFamilyAPI.as_view(), name="register_family"),
    path(
        "register/parent/<uuid:fid>",
        RegisterParentAPI.as_view(),
        name="register_parent",
    ),
    path(
        "join/parent/<uuid:fid>/<str:code>/",
        RegisterParentAPI.as_view(),
        name="join_family_parent",
    ),
    path(
        "join/child/<uuid:fid>/<str:code>/",
        RegisterChildAPI.as_view(),
        name="join_family_child",
    ),
    path(
        "reset_password_phone/", ResetPasswordPhoneAPI.as_view(), name="reset_password"
    ),
    path("reset_password/", ResetPasswordAPI.as_view(), name="reset_password"),
    path(
        "resend_reset_password/<str:username_email>/",
        resendResetPasswordAPI,
        name="resend_reset_password",
    ),
    path("reset_password/code/", CodeResetAPI.as_view(), name="reset_password_code"),
    path(
        "reset_password/change/",
        ChangePasswordAPI.as_view(),
        name="reset_password_change",
    ),
    path(
        "reset_password/change/<uuid:id>/",
        ChangePasswordAPI.as_view(),
        name="reset_password_change",
    ),
]

urlpatterns += router.urls
