from django.db import models
from accounts.models import Child

class HourlyUsage(models.Model):
    hour = models.IntegerField()  # 0 to 23
    usage_seconds = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(hour__gte=0, hour__lte=23), name='valid_hour_range')
        ]
        ordering = ['hour']

    def __str__(self):
        return f"{self.hour}:00 → {self.usage_seconds} sec"


class UserUsage(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='daily_usages')
    date = models.DateField()
    hourly_usages = models.ManyToManyField(HourlyUsage, related_name='child_usages')

    class Meta:
        unique_together = ('child', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.child.user.username} on {self.date}"
    @property
    def total_usage_seconds(self):
        return self.hourly_usages.aggregate(
            total=models.Sum('usage_seconds')
        )['total'] or 0

class ChildLocation(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='locations')

    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        help_text="Longitude coordinate"
    )
    accuracy = models.FloatField(
        help_text="Location accuracy in meters"
    )
    timestamp = models.DateTimeField(
        help_text="Device timestamp of the location reading"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Server timestamp of when the record was created"
    )

    class Meta:
        indexes = [
            models.Index(fields=['child', '-timestamp']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.child.user.username} - {self.timestamp}"

    @property
    def coordinates(self):
        return f"{self.latitude},{self.longitude}"