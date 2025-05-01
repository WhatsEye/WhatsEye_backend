from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import (filters, generics, pagination, permissions, status,
                            viewsets)
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Child, Parent
from control.models import (BadWord, ChildBadWords, ChildLocation, HourlyUsage,
                            Notification, UserUsage)

from .serializers import (BadWordSerializer, ChildLocationSerializer,
                          HourlyUsageSerializer, NotificationSerializer,
                          UserDailyUsageSerializer, UserHourlyUsageSerializer)


class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 7  # page size. Adjust as needed.
    page_size_query_param = "page_size"
    max_page_size = 100


class ChildBadWordsView(APIView):
    def get(self, request, child_id):
        child = get_object_or_404(Child, id=child_id)
        if child.user != request.user:
            parent = Parent.objects.filter(user=request.user).first() 
            if not parent or child.my_family != parent.my_family:
                self.permission_denied(
                    self.request,
                    message="No permission to access this child",
                    code=status.HTTP_403_FORBIDDEN,
                )
        cbw = ChildBadWords.objects.get(child__id=child_id)
        bad_words = cbw.bad_words.values_list('word', flat=True)  # Just get the word strings
        return Response({"bad_words": list(bad_words)})


    def post(self, request, child_id):
        child = get_object_or_404(Child, id=child_id)
        parent = Parent.objects.filter(user=request.user).first() 
        if not parent or child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        word_list = request.data.get(
            "bad_words", []
        )  # {"bad_words": ["word1", "word2", ...]}
        if not isinstance(word_list, list):
            return Response(
                {"error": "bad_words must be a list of strings"}, status=400
            )

        cbw, _ = ChildBadWords.objects.get_or_create(child=child)

        for word in word_list:
            print(word)
            bad_word, _ = BadWord.objects.get_or_create(
                word=word.lower()
            )  # normalize to lowercase
            cbw.bad_words.add(bad_word)
        cbw.save()
        return Response({"message": "Bad words added successfully"}, status=200)


class NotificationListView(generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "child_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        child_id = self.kwargs.get(self.lookup_url_kwarg)
        parent = self.request.user.parent
        child = get_object_or_404(Child, id=child_id)

        if child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )

        queryset = queryset.filter(child__id=child_id)
        return queryset


class ChildLocationListView(generics.ListAPIView):
    serializer_class = ChildLocationSerializer
    permission_classes = [permissions.IsAuthenticated]  # Require authenticated users
    queryset = ChildLocation.objects.all()
    lookup_url_kwarg = "child_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        child_id = self.kwargs.get(self.lookup_url_kwarg)
        parent = self.request.user.parent
        child = get_object_or_404(Child, id=child_id)

        if child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )

        queryset = queryset.filter(child__id=child_id)
        return queryset


class UserUsageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, cid=None):
        parent = request.user.parent
        child = get_object_or_404(Child, id=cid)

        if child.my_family != parent.my_family:
            return Response(
                {"error": "No permission to access this child"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check the URL path and select the appropriate serializer
        if request.path.endswith("/daily/"):
            serializer_class = UserDailyUsageSerializer
        elif request.path.endswith("/hourly/"):
            serializer_class = UserHourlyUsageSerializer
        else:
            return Response(
                {"error": "Invalid usage path"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch usages for the child
        usages = UserUsage.objects.filter(child=child).prefetch_related("hourly_usages")

        # Paginate the queryset using the pagination class
        paginator = self.pagination_class()
        paginated_usages = paginator.paginate_queryset(usages, request)

        # Serialize the paginated results
        serializer = serializer_class(paginated_usages, many=True)

        # Return paginated response
        return paginator.get_paginated_response(serializer.data)


class SetHourlyUsageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        child = request.user.child
        serializer = HourlyUsageSerializer(data=request.data)
        if serializer.is_valid():
            hour = serializer.validated_data["hour"]
            usage_seconds = serializer.validated_data["usage_seconds"]
            date_value = serializer.validated_data["date"]

            # Get or create the UserUsage for today
            user_usage, _ = UserUsage.objects.get_or_create(
                child=child, date=date_value
            )
            # Check if the hour is already used today
            if user_usage.hourly_usages.filter(hour=hour).exists():
                target = user_usage.hourly_usages.filter(hour=hour).first()
                user_usage.hourly_usages.remove(target)

            hourly_obj, _ = HourlyUsage.objects.get_or_create(
                hour=hour, usage_seconds=usage_seconds
            )
            # Link to today's usage
            user_usage.hourly_usages.add(hourly_obj)
            return Response(
                {"message": f"Hour {hour}:00 usage added successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
