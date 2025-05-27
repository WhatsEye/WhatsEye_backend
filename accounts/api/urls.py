from django.urls import path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .auth import MyTokenObtainPairView
from .views import (  # SetPasskeyView,; UpdatePasskeyView,; RegisterParentAPI,; JoinFamilyParentAPI,; JoinFamilyChildAPI,; FamilyViewSet
    ChangePasswordAPI, CodeResetAPI, RegisterChildAPI, RegisterFamilyAPI,
    RegisterParentAPI, ResetPasswordAPI, ResetPasswordPhoneAPI,FamilyProfileAPI,
    ChildProfileAPI, ParentProfileAPI,CheckPasswordView,
    parentInvitationAPI, resendResetPasswordAPI)

app_name = "accounts"


router = routers.DefaultRouter()
# router.register(r"register/family", FamilyViewSet)


urlpatterns = [
    path('check-password/', CheckPasswordView.as_view(), name='check_password'),
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
        "token/child/<uuid:pid>/<str:code>/",
        MyTokenObtainPairView.as_view(),
        name="token_obtain_pair_child",
    ),
    path('profile/child/<uuid:id>/', ChildProfileAPI.as_view(), name='child-profile'),
    path('profile/parent/', ParentProfileAPI.as_view(), name='parent-profile'),

    path('profile/family/', FamilyProfileAPI.as_view(), name='family-profile'),

    # path(
    #     "profile/whatsappname/<int:num>/<str:name>/", setWhatsAppNameAPI, name="setWhatsAppNameAPI"
    # ),
    path(
        "invitation/parent/<str:email>/", parentInvitationAPI, name="invitation_parent"
    ),
    path("register/family/", RegisterFamilyAPI.as_view(), name="register_family"),
    path(
        "register/parent/<uuid:fid>/",
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
