from rest_framework import serializers

from control.models import (BadWord, ChildLocation, HourlyUsage, Notification,
                            UserUsage, Schedule, ChildCallRecording)


class ChildCallRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildCallRecording
        fields = '__all__'
        read_only_fields = ['date']
        extra_kwargs = {"child": {"write_only": True}, "is_deleted": {"write_only": True}}


class ScheduleSerializer(serializers.ModelSerializer):
    is_active_now = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = '__all__'

    def get_is_active_now(self, obj):
        return obj.is_active_now

class BadWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadWord
        fields = ["word"]


class NotificationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notification
        fields = [
            "id",
            "child",
            "title",
            "content",
            "timestamp",
            "type",
        ]  # Specify fields you want to expose


class ChildLocationSerializer(serializers.ModelSerializer):
    coordinates = serializers.CharField(read_only=True)

    class Meta:
        model = ChildLocation
        fields = [
            "id",  # Include ID for reference
            "latitude",
            "longitude",
            "coordinates",
            "accuracy",
            "timestamp",
            "created_at",
        ]

    def get_coordinates(self, obj):
        return {
            "type": "Point",
            "coordinates": [float(obj.longitude), float(obj.latitude)],
        }


class HourlyUsageSerializer(serializers.ModelSerializer):
    date = serializers.DateField()

    class Meta:
        model = HourlyUsage
        fields = ["date", "hour", "usage_seconds"]


class HourlyUsageSerializerShow(serializers.ModelSerializer):
    class Meta:
        model = HourlyUsage
        fields = ["hour", "usage_seconds"]


class UserHourlyUsageSerializer(serializers.ModelSerializer):
    hourly_usages = HourlyUsageSerializerShow(many=True)

    class Meta:
        model = UserUsage
        fields = ["date", "hourly_usages"]


class UserDailyUsageSerializer(serializers.ModelSerializer):
    total_usage_seconds = serializers.ReadOnlyField()

    class Meta:
        model = UserUsage
        fields = ["date", "total_usage_seconds"]
