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
