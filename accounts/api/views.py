import datetime
import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.mail import EmailMessage
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import (filters, generics, pagination, permissions, status,
                            viewsets)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Child, Family, Parent, ResetPassword

from .serializers import (ChangePasswordSerializer,  # SetPasskeySerializer,
                          GetCodeResetSerializer, RegisterFamilySerializer,
                          RegisterSerializer, ResetPasswordPhoneSerializer,
                          ResetPasswordSerializer)


def get_user_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# class SetPasskeyView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         serializer = SetPasskeySerializer(data=request.data)
#         if serializer.is_valid():
#             child = request.user.child
#             passkey = serializer.validated_data['passkey']
#             hash_object = hashlib.sha256(passkey.encode('utf-8'))
#             child.passkey = hash_object.hexdigest()
#             child.save()
#             return Response({"message": "passkey set successfully"}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class UpdatePasskeyView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, cid=None):
#         serializer = SetPasskeySerializer(data=request.data)
#         if serializer.is_valid():
#             parent = request.user.parent
#             child = get_object_or_404(Child, id=cid)
#             if child.my_family != parent.my_family:
#                 return Response({"error": "No permission to access this child"}, status=status.HTTP_403_FORBIDDEN)
#             passkey = serializer.validated_data['passkey']
#             hash_object = hashlib.sha256(passkey.encode('utf-8'))
#             child.passkey = hash_object.hexdigest()
#             child.save()
#             return Response({"message": "passkey set successfully"}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordPhoneAPI(generics.GenericAPIView):
    serializer_class = ResetPasswordPhoneSerializer

    def post(self, request):
        data = self.get_serializer(data=request.data)
        if data.is_valid():
            number = request.data["number"]
            data1 = Parent.objects.filter(phone_number=number)
            data2 = Child.objects.filter(phone_number=number)
            data = data1 if data1 != None else data2
            if data != None:
                obj = ResetPassword.objects.create(
                    phone_number=number, username_email=data.first().user.email
                )
                obj.save()

                #    try:
                #         send_sms(obj)
                #     except:
                #         obj.delete()
                #         return Response({"status": status.HTTP_404_NOT_FOUND})

                return Response({"status": status.HTTP_200_OK})
        return Response(
            {"status": status.HTTP_406_NOT_ACCEPTABLE, "error": data.errors}
        )


class ResetPasswordAPI(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        data = self.get_serializer(data=request.data)
        if data.is_valid():
            username_email = request.data["username_email"]
            user = get_object_or_404(
                get_user_model(),
                Q(username=username_email)
                | Q(email=username_email) & Q(is_active=True),
            )
            if user != None:
                obj = ResetPassword(username_email=user.email)
                obj.save()

                template = render_to_string("email/code_reset.html", {"code": obj.code})
                msg = EmailMessage(
                    "Code de confirmation",
                    template,
                    settings.EMAIL_HOST_USER,
                    [user.email],
                )
                msg.content_subtype = "html"

                msg.send()
                return Response({"status": status.HTTP_200_OK})
        return Response(
            {"status": status.HTTP_406_NOT_ACCEPTABLE, "error": data.errors}
        )


class CodeResetAPI(generics.GenericAPIView):
    serializer_class = GetCodeResetSerializer

    def post(self, request, *args, **kwargs):
        code = request.data.get("confirmation_code")
        obj = get_object_or_404(ResetPassword, code=code)
        now = datetime.datetime.now()

        if (now.hour - obj.created_at.hour) > 1 and (
            (now.day - obj.created_at.day) > 0
            or (now.month - obj.created_at.month) > 0
            or (now.year - obj.created_at.year) > 0
        ):
            obj.delete()
            return Response(
                {"error": "get new code", "status": status.HTTP_406_NOT_ACCEPTABLE}
            )
        obj.checked = True
        obj.save()
        return Response({"rid": obj.id, "status": status.HTTP_200_OK})


class ChangePasswordAPI(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request, id=None):
        data = self.get_serializer(data=request.data)
        if not data.is_valid():
            return Response({"status": status.HTTP_406_NOT_ACCEPTABLE})
        if id == None:
            user = request.user
        else:
            reset = ResetPassword.objects.filter(id=id).first()
            if reset == None or reset.checked == False:
                return Response({"status": status.HTTP_404_NOT_FOUND})
            user = (
                get_user_model()
                .objects.filter(
                    Q(username=reset.username_email)
                    | Q(email=reset.username_email) & Q(is_active=True)
                )
                .first()
            )
            reset.delete()
        if user.id == None:
            return Response({"status": status.HTTP_406_NOT_ACCEPTABLE})
        user.set_password(request.data.get("password"))
        user.save()
        update_session_auth_hash(request, user)
        return Response({"status": status.HTTP_202_ACCEPTED})


class RegisterFamilyAPI(generics.CreateAPIView):
    serializer_class = RegisterFamilySerializer
    queryset = Family.objects.filter(deleted=False)


class RegisterParentAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, fid=None, code=None, *args, **kwargs):
        family = get_object_or_404(Family, id=fid)
        if family.father != None and request.data["gender"] == "M":
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "error": "already exist a father in this family",
                }
            )
        if family.mother != None and request.data["gender"] == "F":
            return Response(
                {
                    "status": status.HTTP_400_BAD_REQUEST,
                    "error": "already exist a mother in this family",
                }
            )
        if code != None:
            parent = get_object_or_404(Parent, qr_code=code)
            if parent != family.father and parent != family.mother:
                return Response(
                    {"status": status.HTTP_400_BAD_REQUEST, "error": "wrong id"}
                )
            parent.get_new_qr
            parent.save()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user = Parent(
            user=user,
            phone_number=request.data["phone_number.phone_number"],
            gender=request.data["gender"],
            birthday=request.data["birthday"],
        )
        user.first_ip = get_user_ip(request)
        user.ip = get_user_ip(request)
        user.get_new_code
        user.save()
        if user.gender == "M":
            family.father = user
        else:
            family.mother = user
        family.save()

        # template = render_to_string(
        #     "email/code_conform.html",
        #     {"code": user.profile.conform_code, "username": user.username},
        # )
        # msg = EmailMessage(
        #     "Confirmez votre compte",
        #     template,
        #     settings.EMAIL_HOST_USER,
        #     [user.email],
        # )
        # msg.content_subtype = "html"
        # msg.send()
        return Response({"status": status.HTTP_200_OK})


class RegisterChildAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, fid=None, code=None, *args, **kwargs):
        family = get_object_or_404(Family, id=fid, qr_code=code)
        family.get_new_qr
        family.save()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user = Child(
            user=user,
            phone_number=request.data["phone_number.phone_number"],
            gender=request.data["gender"],
            birthday=request.data["birthday"],
        )
        user.first_ip = get_user_ip(request)
        user.ip = get_user_ip(request)
        user.get_new_code
        user.save()
        family.kids.add(user)

        # template = render_to_string(
        #     "email/code_conform.html",
        #     {"code": user.profile.conform_code, "username": user.username},
        # )
        # msg = EmailMessage(
        #     "Confirmez votre compte",
        #     template,
        #     settings.EMAIL_HOST_USER,
        #     [user.email],
        # )
        # msg.content_subtype = "html"
        # msg.send()
        return Response({"status": status.HTTP_200_OK})


@api_view(["get"])
def parentInvitationAPI(request, email):
    user = request.user
    family = Family.objects.filter(Q(father__user=user) | Q(mother__user=user)).first()
    print(family)
    template = render_to_string(
        "email/invitation.html",
        {"fid": family.id, "code": user.parent.qr_code},
    )
    msg = EmailMessage(
        "invitation",
        template,
        settings.EMAIL_HOST_USER,
        [email],
    )
    msg.content_subtype = "html"
    msg.send()
    return Response({"status": status.HTTP_200_OK})


@api_view(["get"])
def resendResetPasswordAPI(request, username_email):
    user = (
        get_user_model()
        .objects.filter(
            Q(username=username_email) | Q(email=username_email) & Q(is_active=True)
        )
        .first()
    )
    if user != None:
        obj = ResetPassword.objects.filter(username_email=user.email).first()
        if obj != None:
            obj.get_new_code
            obj.save()
            if obj.phone_number == None:
                template = render_to_string("email/code_reset.html", {"code": obj.code})
                msg = EmailMessage(
                    "Code de confirmation",
                    template,
                    settings.EMAIL_HOST_USER,
                    [user.email],
                )
                msg.content_subtype = "html"
                msg.send()
                return Response({"status": status.HTTP_200_OK})
            else:
                #    try:
                #         send_sms(obj)
                #     except:
                #         obj.delete()
                #         return Response({"status": status.HTTP_404_NOT_FOUND})
                print(obj.code)
                return Response({"status": status.HTTP_200_OK})

    return Response({"status": status.HTTP_406_NOT_ACCEPTABLE, "error": "no user"})
