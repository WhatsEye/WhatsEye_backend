from rest_framework import serializers
from control.models import UserUsage, HourlyUsage

class HourlyUsageSerializer(serializers.ModelSerializer):
    date = serializers.DateField()

    class Meta:
        model = HourlyUsage
        fields = ['date', 'hour', 'usage_seconds']

class HourlyUsageSerializerShow(serializers.ModelSerializer):
    class Meta:
        model = HourlyUsage
        fields = ['hour', 'usage_seconds']
        
class UserHourlyUsageSerializer(serializers.ModelSerializer):
    hourly_usages = HourlyUsageSerializerShow(many=True)

    class Meta:
        model = UserUsage
        fields = ['date', 'hourly_usages']

class UserDailyUsageSerializer(serializers.ModelSerializer):
    total_usage_seconds = serializers.ReadOnlyField()

    class Meta:
        model = UserUsage
        fields = ['date', 'total_usage_seconds']

