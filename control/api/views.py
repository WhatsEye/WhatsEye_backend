from datetime import datetime, date, time
from django.shortcuts import get_object_or_404
from rest_framework import (filters, generics, pagination, permissions, status,
                            viewsets)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from accounts.api.serializers import ChangePasswordSerializer
from accounts.models import Child, Parent
from control.models import (BadWord, ChildBadWords, ChildLocation, HourlyUsage,
                            Notification, UserUsage,Schedule,ChildCallRecording)

from .serializers import (ScheduleSerializer, ChildLocationSerializer,
                          HourlyUsageSerializer, NotificationSerializer,
                          UserDailyUsageSerializer, UserHourlyUsageSerializer,
                          ChildCallRecordingSerializer)

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

def blacklist_user_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 7  # page size. Adjust as needed.
    page_size_query_param = "page_size"
    max_page_size = 100

class ScheduleChildListView(generics.ListAPIView):
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Schedule.objects.filter(is_deleted=False)

    def get_queryset(self):
        queryset = super().get_queryset()
        try:
            child = Child.objects.get(user=self.request.user)
            #child = Child.objects.first()
        except ObjectDoesNotExist:
            return queryset.none()  # Return empty queryset if no child exists

        # Get current time and date
        now = timezone.now()
        today = now.date()
        
        # Filter schedules to mimic is_active_now logic
        active_schedules = Schedule.objects.filter(
            child=child,
            is_deleted=False,
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=today),
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        )

        # Filter ChildLocation objects for children with active schedules
        queryset = queryset.filter(child=child, child__schedules__in=active_schedules)

        return queryset.distinct()
    
class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.filter(is_deleted=False)
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]  # Adjust permissions as needed
    pagination_class = StandardResultsSetPagination
    # Optional: filter schedules by child, user, etc.
    def get_queryset(self):
        queryset = super().get_queryset()
        child_id = dict(self.kwargs)["child_id"]
        child = get_object_or_404(Child, id=child_id)
        parent = Parent.objects.filter(user=self.request.user).first() 
        if not parent or child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        queryset = queryset.filter(child__id=child_id)
        return queryset

class ChildCallRecordingUpdateView(generics.UpdateAPIView):
    queryset = ChildCallRecording.objects.filter(is_deleted=False)
    serializer_class = ChildCallRecordingSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        child_id = self.kwargs['child_id']
        child = get_object_or_404(Child, id=child_id)
        parent = Parent.objects.filter(user=self.request.user).first() 
        if not parent or child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        return self.queryset.filter(child__id=child_id)
    
class ChildCallRecordingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated] 
    pagination_class = StandardResultsSetPagination

    def get(self, request, child_id=None, recording_type=None):
        child = get_object_or_404(Child, id=child_id)
        parent = Parent.objects.filter(user=self.request.user).first() 
        if not parent or child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        if recording_type not in ["voice", "video"]:
            return Response({"detail": "Invalid recording type."}, status=status.HTTP_400_BAD_REQUEST)

        recordings = ChildCallRecording.objects.filter(
            child=child,
            is_deleted=False,
            recording_type=recording_type,
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(recordings, request)

        serializer = ChildCallRecordingSerializer(page, many=True,context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
class ChildCallRecordingPostAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated] 

    def post(self, request, child_id=None):
        child = get_object_or_404(Child, id=child_id)
        if request.user != child.user:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        data = request.data.copy()
        dt = datetime.fromtimestamp(int(data["timestamp"]) / 1000.0)
        data['child'] = str(child.id)
        data["timestamp"] = dt
        serializer = ChildCallRecordingSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            print(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ChangeChildPasswordAPI(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request, child_id=None):
        child = get_object_or_404(Child, id=child_id)

        parent = Parent.objects.filter(user=request.user).first()
        if not parent or child.my_family != parent.my_family:
            return Response(
                {"detail": "No permission to access this child"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_password = serializer.validated_data.get("password")
        user = child.user
        user.set_password(new_password)
        user.save()
        blacklist_user_tokens(user)

        return Response({"detail": "Password updated successfully"}, status=status.HTTP_202_ACCEPTED)

class ChildBadWordsView(APIView):
    def get(self, request, child_id=None):
        child = get_object_or_404(Child, id=child_id)
        if child.user != request.user:
            parent = Parent.objects.filter(user=request.user).first() 
            if not parent or child.my_family != parent.my_family:
                self.permission_denied(
                    self.request,
                    message="No permission to access this child",
                    code=status.HTTP_403_FORBIDDEN,
                )
        cbw, _ = ChildBadWords.objects.get_or_create(child=child)
        bad_words = cbw.bad_words.values_list('word', flat=True)  # Just get the word strings
        return Response({"bad_words": list(bad_words)})

    def post(self, request, child_id=None):
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
            bad_word, _ = BadWord.objects.get_or_create(
                word=word.lower()
            )  # normalize to lowercase
            cbw.bad_words.add(bad_word)
        cbw.save()
        return Response({"message": "Bad words added successfully"}, status=200)
    
    def delete(self, request,child_id=None, word=None, *args, **kwargs):
        child = get_object_or_404(Child, id=child_id)
        parent = Parent.objects.filter(user=request.user).first() 
        if child.my_family != parent.my_family:
            self.permission_denied(
                self.request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        # Retrieve the object to delete
        cbw = ChildBadWords.objects.filter(child=child).first()
        bad_word = BadWord.objects.filter(word=word.lower()).first()
        if (cbw==None or bad_word==None):
            return Response(
                {"error": "bad word not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        cbw.bad_words.remove(bad_word)
        
        return Response(
                {"message": "bad word deleted successfully"},
                status=status.HTTP_200_OK
            )

class NotificationListView(generics.ListAPIView):
    queryset = Notification.objects.filter(is_deleted=False)
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    lookup_url_kwarg = "child_id"
    filter_backends = [DjangoFilterBackend]

    #search_fields = ['type']
    filterset_fields = ['type']

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        except Exception as e:
            return Response(
                {"error": f"Error retrieving notifications: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def delete(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if not pk:
            return Response(
                {"error": "No ID provided for deletion"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Get the filtered queryset (respects child_id and permissions)
        queryset = self.get_queryset()

        try:
            # Get the specific object
            obj = queryset.get(pk=pk)
            obj.is_deleted = True  # Soft deletion
            obj.save()
            return Response(
                {"message": "Notification deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Error during deletion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    queryset = ChildLocation.objects.filter(is_deleted=False)
    lookup_url_kwarg = "child_id"

    def delete(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if not pk:
            return Response(
                {"error": "No ID provided for deletion"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the filtered queryset (respects child_id and permissions)
        queryset = self.get_queryset()

        try:
            # Get the specific object
            obj = queryset.get(pk=pk)
            obj.is_deleted = True  # Soft deletion
            obj.save()
            return Response(
                {"message": "Location deleted successfully"},
                status=status.HTTP_200_OK
            )
        except ChildLocation.DoesNotExist:
            return Response(
                {"error": "Location not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Error during deletion: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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


@api_view(["GET"])
@permission_classes((permissions.IsAuthenticated,))
def make_read_notifications(request, child_id=None):
    if id != None:
        parent = request.user.parent
        child = get_object_or_404(Child, id=child_id)

        if child.my_family != parent.my_family:
            permission_denied(
                request,
                message="No permission to access this child",
                code=status.HTTP_403_FORBIDDEN,
            )
        
        Notification.objects.filter(Q(child__id=child_id) & Q(is_deleted=False) & Q(is_read=False)).update(
            is_read=True
        )
        return Response({"status": status.HTTP_200_OK})

    return Response({"status": status.HTTP_404_NOT_FOUND})