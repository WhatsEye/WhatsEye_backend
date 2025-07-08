import os
from datetime import datetime
from django.db import models
from django.forms import ValidationError

from accounts.models import Child
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField


def child_record_upload_path(instance, filename):
    # Use the child's ID in the path
    return os.path.join('records', f"{instance.child.id}/{instance.recording_type}", filename)


class HourlyUsage(models.Model):
    hour = models.IntegerField()  # 0 to 23
    usage_seconds = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(hour__gte=0, hour__lte=23), name="valid_hour_range"
            )
        ]
        ordering = ["hour"]

    def __str__(self):
        return f"{self.hour}:00 → {self.usage_seconds} sec"

class UserUsage(models.Model):
    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="daily_usages"
    )
    date = models.DateField()
    hourly_usages = models.ManyToManyField(HourlyUsage, related_name="child_usages")

    class Meta:
        unique_together = ("child", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.child.user.username} on {self.date}"

    @property
    def total_usage_seconds(self):
        return (
            self.hourly_usages.aggregate(total=models.Sum("usage_seconds"))["total"]
            or 0
        )

class ChildLocation(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="locations")

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, help_text="Longitude coordinate"
    )
    accuracy = models.FloatField(help_text="Location accuracy in meters")
    timestamp = models.DateTimeField(
        help_text="Device timestamp of the location reading"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Server timestamp of when the record was created"
    )

    is_deleted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["child", "-timestamp"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.child.user.username} - {self.timestamp}"

    @property
    def coordinates(self):
        return f"{self.latitude},{self.longitude}"

class Day(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    value = models.IntegerField(choices=DAY_CHOICES, unique=True)

    def __str__(self):
        return dict(self.DAY_CHOICES).get(self.value, "Unknown")
    
class Schedule(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    days = models.ManyToManyField(Day, related_name='schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)



    @property
    def is_active_now(self):
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        weekday = today.weekday()  # 0 = Monday, 6 = Sunday

        start_date_obj = self.start_date
        if isinstance(start_date_obj, str):
            try:
                start_date_obj = datetime.strptime(start_date_obj, '%Y-%m-%d').date()
            except ValueError:
                return False # Or log an error

        end_date_obj = self.end_date
        if isinstance(end_date_obj, str):
            try:
                end_date_obj = datetime.strptime(end_date_obj, '%Y-%m-%d').date()
            except ValueError:
                return False # Or log an error


        if start_date_obj and today < start_date_obj:
            return False
        if end_date_obj and today > end_date_obj:
            return False

        if not self.days.filter(value=weekday).exists():
            return False

        if not (self.start_time <= current_time <= self.end_time):
            return False

        return True

    def clean(self):
        super().clean()
        if self.start_date is None and self.end_date is not None:
            raise ValidationError("End date requires a start date for non-recurring schedules.")
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date must be before end date.")

    def __str__(self):
        return f"{self.name} for {self.child.user.username}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("message", "Message"),
        ("alert", "Alert"),
        ("reminder", "Reminder"),
        ("info", "Information"),
        ("warning", "Warning"),
    )
    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return f"Notification: {self.title} (Type: {self.type}, Timestamp: {self.timestamp})"

    class Meta:
        ordering = ["-timestamp"]  # To order notifications by most recent first

class BadWord(models.Model):
    word = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.word

class ChildBadWords(models.Model):
    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="child_bad_words"
    )
    bad_words = models.ManyToManyField(BadWord, blank=True)

    def __str__(self):
        return f"{self.child.user.username}'s BadWord list"




class ChildCallRecording(models.Model):
    RECORDING_TYPE_CHOICES = [
        ("voice", "Voice"),
        ("video", "Video"),
    ]

    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name="records"
    )
    date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(
        help_text="Device timestamp of the call"
    )
    record_file = models.FileField(upload_to=child_record_upload_path)
    
    recording_type = models.CharField(
        max_length=10,
        choices=RECORDING_TYPE_CHOICES,
        default="voice",
    )

    def __str__(self):
        return f"{self.child.user} - {self.date} ({self.recording_type})"
    
