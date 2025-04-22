from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from accounts.models import Parent, Family, BaseUser

class SetPasslockSerializer(serializers.Serializer):
    passlock = serializers.CharField(write_only=True)

    def validate_passlock(self, value):
        if len(value) < 4:
            raise serializers.ValidationError("Passlock must be at least 4 characters long.")
        return value

    def update(self, instance, validated_data):
        instance.passlock = validated_data['passlock']
        instance.save()
        return instance

class CheckPasslockSerializer(serializers.Serializer):
    passlock = serializers.CharField(write_only=True)

    def validate(self, data):
        child = self.context['child']
        if not child.check_passlock(data['passlock']):
            raise serializers.ValidationError({"passlock": "Incorrect passlock."})
        return data

class UpdatePasslockSerializer(serializers.Serializer):
    new_passlock = serializers.CharField(write_only=True)
    new_passlock2 = serializers.CharField(write_only=True)
    def validate_passlock(self, value):
        if len(value) < 4:
            raise serializers.ValidationError("Passlock must be at least 4 characters long.")
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "last_login",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["date_joined", "last_login"]


class ResetPasswordSerializer(serializers.Serializer):
    username_email = serializers.CharField(max_length=255)

    def validate(self, data):
        username_email = data.get("username_email")
        if (
            get_user_model()
            .objects.filter(
                Q(username=username_email) | Q(email=username_email) & Q(is_active=True)
            )
            .count()
            == 0
        ):
            raise serializers.ValidationError("No user with this email or username")
        return data


class ResetPasswordPhoneSerializer(serializers.Serializer):
    number = PhoneNumberField()

    def validate(self, data):
        number = data.get("number")
        return number


class GetCodeResetSerializer(serializers.Serializer):
    confirmation_code = serializers.CharField(max_length=7, min_length=7, required=True)


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        min_length=8, write_only=True, required=True, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        min_length=8, write_only=True, required=True, style={"input_type": "password"}
    )

    def validate(self, data):
        password = data.get("password")
        password_confirm = data.get("password_confirm")
        if password == password_confirm:
            return data
        else:
            raise serializers.ValidationError("Passwords don't match")


class ParentAPI(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ["phone_number", "birthday", "gender", "photo", "photo_icon"]
        read_only_fields = ["is_confirmed"]


class RegisterFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = ["id", "name", "about", "family_status"]
        read_only_fields = [
            "id",
        ]


class ProfilePhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ["phone_number"]


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(
        min_length=8, write_only=True, required=True, style={"input_type": "password"}
    )
    password = serializers.CharField(
        min_length=8, write_only=True, required=True, style={"input_type": "password"}
    )
    phone_number = ProfilePhoneSerializer(required=True)
    gender = serializers.ChoiceField(choices=BaseUser.GENDER_CHOICES)
    birthday = serializers.DateField()

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "phone_number",
            "password",
            "password1",
            "gender",
            "birthday",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        password1 = data.get("password1")
        password = data.get("password")
        gender = data.get("gender")
        phone_number = data.get("phone_number").get("phone_number")
        if password == password1:
            if Parent.objects.filter(Q(phone_number=phone_number)).count() == 0:
                return data
            else:
                raise serializers.ValidationError(
                    "already a user exists with this email"
                )
        else:
            raise serializers.ValidationError("password didn't match")

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data.get("username"),
            email=validated_data.get("email"),
            password=validated_data.get("password"),
        )
        user.save()
        return user
