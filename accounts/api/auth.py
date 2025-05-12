from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from phonenumbers import (NumberParseException, PhoneNumberFormat,
                          format_number, is_valid_number, parse)
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import Child, Parent



User = get_user_model()

def get_user_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    def get_token(self, user):
        token = super().get_token(user)
        request = self.context["request"]
        if Parent.objects.filter(user=user).first():
            account = user.parent
            family_id = (account.father.all() | account.mother.all()).first().id
        else:
            account = user.child
            family_id = account.family_set.all().first().id
        token["id"] = str(account.id)
        token["family_id"] = str(family_id)
        token["username"] = str(account.user.username)
        account.ip = get_user_ip(request)

        account.save()
        return token

    def validate(self, attrs):
        user_identifier = attrs["username"]  # use 'username' for authentication
        try:
            user = User.objects.get(username=user_identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                _("User with this identifier does not exist.")
            )

        # Validate password
        if not user.check_password(attrs.get("password")):
            raise serializers.ValidationError(_("Incorrect password."))
        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, pid=None, code=None, *args, **kwargs):
        data = dict(request.data)
        identifier = data["username"]
        print(identifier)
        user = None
        if identifier.isdigit() or identifier.startswith("+"):
            try:
                parsed_number = parse(identifier, "DZ")
                if is_valid_number(parsed_number):
                    identifier = format_number(parsed_number, PhoneNumberFormat.E164)
            except NumberParseException:
                pass
            obj1 = Child.objects.filter(phone_number=identifier).first()
            if obj1:
                user = obj1.user

            obj2 = Parent.objects.filter(phone_number=identifier).first()
            if obj2:
                user = obj2.user
        else:
            user = User.objects.filter(
                Q(username=identifier) | Q(email=identifier)
            ).first()

        if user:
            data["username"] = user.username

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        if pid != None and code != None:
            obj = Parent.objects.filter(id=pid, qr_code=code).first()
            obj2 = Child.objects.filter(user__username=data["username"]).first()
            if obj and obj2:
                if (
                    obj.father.all() | obj.mother.all()
                ).first() != obj2.family_set.all().first():
                    return Response({"status": False})
                else:
                    obj.get_new_qr
                    obj.save()
        else:
            obj = Parent.objects.filter(user__username=data["username"]).first()

        if obj:
            response = Response(
                {**serializer.validated_data, "status": True}, status=status.HTTP_200_OK
            )
            return response

        return Response({"status": False})
