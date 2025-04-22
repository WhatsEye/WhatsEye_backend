from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework.response import Response  
from accounts.models import Child
from control.models import HourlyUsage, UserUsage
from .serializers import UserDailyUsageSerializer, UserHourlyUsageSerializer,HourlyUsageSerializer
from rest_framework import filters, generics, pagination, status, viewsets, permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView


class UserUsageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, cid=None):
        parent = request.user.parent
        child = get_object_or_404(Child, id=cid)

        if child.my_family != parent.my_family:
            return Response({"error": "No permission to access this child"}, status=status.HTTP_403_FORBIDDEN)

        # Check the URL path
        if request.path.endswith('/daily/'):
            serializer_class = UserDailyUsageSerializer
        elif request.path.endswith('/hourly/'):
            serializer_class = UserHourlyUsageSerializer
        else:
            return Response({"error": "Invalid usage path"}, status=status.HTTP_400_BAD_REQUEST)

        usages = UserUsage.objects.filter(child=child).prefetch_related('hourly_usages')
        serializer = serializer_class(usages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

class SetHourlyUsageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, cid=None):
        parent = request.user.parent
        child = get_object_or_404(Child, id=cid)

        if child.my_family != parent.my_family:
            return Response({"error": "No permission to access this child"}, status=status.HTTP_403_FORBIDDEN)

        serializer = HourlyUsageSerializer(data=request.data)

        if serializer.is_valid():
            hour = serializer.validated_data['hour']
            usage_seconds = serializer.validated_data['usage_seconds']

            # Get or create the UserUsage for today
            user_usage, _ = UserUsage.objects.get_or_create(
                child=child,
                date=date.today()
            )

            # Check if the hour is already used today
            if user_usage.hourly_usages.filter(hour=hour).exists():
                return Response(
                    {"error": f"Usage for hour {hour}:00 already exists for today"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create or get the HourlyUsage object
            hourly_obj, _ = HourlyUsage.objects.get_or_create(
                hour=hour,
                usage_seconds=usage_seconds
            )

            # Link to today's usage
            user_usage.hourly_usages.add(hourly_obj)
            return Response({"message": f"Hour {hour}:00 usage added successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)