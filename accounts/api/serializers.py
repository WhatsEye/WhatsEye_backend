from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from accounts.models import BaseUser, Family, Parent, Child

from rest_framework import serializers

from control.models import Notification, ChildCallRecording


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
        read_only_fields = ["id", "username","date_joined", "last_login"]
        
class BaseUserShortSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "user_id",
            "username",
            "full_name",
            "gender",
            "photo",
        ]

    def get_username(self, obj):
        return getattr(obj.user, "username", None)

    def get_full_name(self, obj):
        return f'{getattr(obj.user, "first_name", None)} {getattr(obj.user, "last_name", None)}'

    def get_user_id(self, obj):
        return getattr(obj.user, "id", None)

class ChildShortSerializer(BaseUserShortSerializer):
    class Meta(BaseUserShortSerializer.Meta):
        model = Child

class ParentShortSerializer(BaseUserShortSerializer):
    class Meta(BaseUserShortSerializer.Meta):
        fields = [*BaseUserShortSerializer.Meta.fields, "qr_image"]
        model = Parent

class ChildProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    num_unread_notifications = serializers.SerializerMethodField(read_only=True)
    num_unread_voice_calls = serializers.SerializerMethodField(read_only=True)
    num_unread_video_calls = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Child
        fields = (
            "id",
            "photo",
            "birthday",
            "phone_number",
            "phone_locked",
            "user",
            'num_unread_notifications', 
            'num_unread_voice_calls', 
            'num_unread_video_calls'
        )
        read_only_fields = ["id"]
    
    def get_num_unread_notifications(self, obj):
        # Example: count notifications where 'read' is False
        return Notification.objects.filter(child__user=obj.user, is_read=False).count()

    def get_num_unread_voice_calls(self, obj):
        # Example: count unread voice calls
        return ChildCallRecording.objects.filter(child__user=obj.user, recording_type='voice', is_read=False).count()

    def get_num_unread_video_calls(self, obj):
        # Example: count unread video calls
        return ChildCallRecording.objects.filter(child__user=obj.user, recording_type='video', is_read=False).count()
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
        return super().update(instance, validated_data)        

class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = Parent
        fields = (
            "id",
            "photo",
            "birthday",
            "phone_number",
            "user"
        )
    def update(self, instance, validated_data):
        # Extract user data from validated data
        user_data = validated_data.pop("user", None)
        
        # Update user if user_data is provided
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
        
        # Update parent fields
        return super().update(instance, validated_data)

class FamilyProfileSerializer(serializers.ModelSerializer):
    kids = ChildShortSerializer(many=True, read_only=True)
    mother = ParentShortSerializer(read_only=True)
    father = ParentShortSerializer(read_only=True)
    count_kids = serializers.SerializerMethodField(read_only=True)
    count_parents = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Family
        fields = ["id", "photo","qr_image", "name", "about", "mother", "father", "kids", "count_kids", "count_parents"]

    def get_count_kids(self, obj):
        return obj.kids.all().count()
    
    def get_count_parents(self, obj):
        return int(obj.father!=None) + int(obj.mother!=None)

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
        fields = ["phone_number", "birthday", "gender", "photo"]
        read_only_fields = ["is_confirmed"]


class RegisterFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = ["id", "name", "about"]
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
