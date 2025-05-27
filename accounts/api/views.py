import datetime
import hashlib

from accounts.twilloV import send_sms
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
from django.contrib.auth import authenticate

from accounts.models import Child, Family, Parent, ResetPassword
from rest_framework.parsers import MultiPartParser, FormParser

from .auth import MyTokenObtainPairSerializer
from .serializers import (ChangePasswordSerializer,PasswordCheckSerializer,
                          GetCodeResetSerializer, RegisterFamilySerializer,
                          RegisterSerializer, ResetPasswordPhoneSerializer,
                          ResetPasswordSerializer, FamilyProfileSerializer,UserSerializer,
                          ChildProfileSerializer,ParentProfileSerializer)


def get_user_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

class ChildProfileAPI(generics.RetrieveUpdateAPIView):
    serializer_class = ChildProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"  
    lookup_url_kwarg = "id"  

    def get_queryset(self):
        return Child.objects.all()

    def get_object(self):
        uuid = self.kwargs.get(self.lookup_url_kwarg)
        queryset = self.get_queryset().filter(id=uuid)
        obj = generics.get_object_or_404(queryset)
        return obj

class CheckPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordCheckSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        password = serializer.validated_data['password']
        user = authenticate(username=request.user.username, password=password)
        
        if user is not None:
            return Response({
                'is_correct': True,
                'message': 'Password is correct'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'is_correct': False,
            'message': 'Password is incorrect'
        }, status=status.HTTP_401_UNAUTHORIZED)

class ParentProfileAPI(generics.RetrieveUpdateAPIView):
    serializer_class = ParentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # Support file uploads for photo


    def get_queryset(self):
        return Parent.objects.filter(user=self.request.user)

    def get_object(self):
        return self.get_queryset().first()

class FamilyProfileAPI(generics.RetrieveUpdateAPIView):
    serializer_class = FamilyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.parent.my_family

    def get_object(self):
        return self.get_queryset()
    
class ResetPasswordPhoneAPI(generics.GenericAPIView):
    serializer_class = ResetPasswordPhoneSerializer

    def post(self, request):
        data = self.get_serializer(data=request.data)
        if data.is_valid():
            number = request.data["number"]
            data = get_object_or_404(Parent, phone_number=number)
            if data != None:
                obj = ResetPassword.objects.create(
                    phone_number=number, username_email=data.user.email
                )
                obj.save()

                # try:
                #     send_sms(obj.phone_number, obj.code)
                # except:
                #     obj.delete()
                #     return Response({"status": status.HTTP_101_SWITCHING_PROTOCOLS})
                return Response({"status": status.HTTP_200_OK, "username":data.user.username})
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
                Parent,
                Q(user__username=username_email)
                | Q(user__email=username_email) & Q(user__is_active=True),
            )
            user = user.user
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
                return Response({"status": status.HTTP_200_OK, "username": user.username})
        return Response(
            {"status": status.HTTP_406_NOT_ACCEPTABLE, "error": data.errors}
        )


class CodeResetAPI(generics.GenericAPIView):
    serializer_class = GetCodeResetSerializer

    def post(self, request, *args, **kwargs):
        code = request.data.get("confirmation_code")
        obj = get_object_or_404(ResetPassword, code=code)
        print(obj)
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

        parent = Parent(
            user=user,
            phone_number=request.data["phone_number"]["phone_number"],
            gender=request.data["gender"],
            birthday=request.data["birthday"],
        )
        parent.first_ip = get_user_ip(request)
        parent.ip = get_user_ip(request)
        parent.get_new_code
        parent.save()
        if parent.gender == "M":
            family.father = parent
        else:
            family.mother = parent
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

        token_serializer = MyTokenObtainPairSerializer(data={
            'username': user.username,
            'password': request.data.get('password')  # Assuming password is sent in request.data
        }, context={'request': request})
        token_serializer.is_valid(raise_exception=True)
        tokens = token_serializer.validated_data

        # Return response with tokens
        return Response({
            "status": status.HTTP_200_OK,
            "access": tokens.get('access'),
            "refresh": tokens.get('refresh')
        })

        


class RegisterChildAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, fid=None, code=None, *args, **kwargs):
        print(request.data["phone_number"]["phone_number"])
        family = get_object_or_404(Family, id=fid, qr_code=code)
       
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        child = Child(
            user=user,
            gender=request.data["gender"],
            birthday=request.data["birthday"],
        )
        child.phone_number = request.data["phone_number"]["phone_number"]
        child.phone_locked = False
        child.first_ip = get_user_ip(request)
        child.ip = get_user_ip(request)
        child.save()
        family.kids.add(child)
        family.get_new_qr
        family.save()
         # Generate tokens for the user
        token_serializer = MyTokenObtainPairSerializer(data={
            'username': user.username,
            'password': request.data.get('password')  # Assuming password is sent in request.data
        }, context={'request': request})
        token_serializer.is_valid(raise_exception=True)
        tokens = token_serializer.validated_data

        # Return response with tokens
        return Response({
            "status": status.HTTP_200_OK,
            "access": tokens.get('access'),
            "refresh": tokens.get('refresh')
        })
        return Response({"status": status.HTTP_200_OK})


# @api_view(["post"])
# def setWhatsAppNameAPI(request, num=None, name=None):

#     user = request.user
#     child = get_object_or_404(Child, user=user)
#     if(num==1):
#         child.whatsapp_name= name
#     elif(num==2):
#         child.whatsapp2_name= name
#     else:
#         return Response({"status": status.HTTP_400_BAD_REQUEST})
#     child.save()
#     return Response({"status": status.HTTP_200_OK})

@api_view(["get"])
def parentInvitationAPI(request, email):
    user = request.user
    family = Family.objects.filter(Q(father__user=user) | Q(mother__user=user)).first()

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
            Q(username=username_email) & Q(is_active=True)
        )
        .first()
    )
    if user != None:
        obj = ResetPassword.objects.filter(username_email=user.email).first()
        if obj != None:
            obj.get_new_code
            obj.save()
            ##if obj.phone_number == None:
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
            # else:
            #     # try:
            #     #    send_sms(obj.phone_number, obj.code)
            #     # except:
            #         # obj.delete()
            #         # return Response({"status": status.HTTP_404_NOT_FOUND})
            #     print(obj.code)
            #     return Response({"status": status.HTTP_200_OK})

    return Response({"status": status.HTTP_406_NOT_ACCEPTABLE, "error": "no user"})
