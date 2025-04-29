from django.contrib import admin
from .models import HourlyUsage, UserUsage, ChildLocation, Notification

admin.site.register(UserUsage)
admin.site.register(HourlyUsage)
admin.site.register(ChildLocation)
admin.site.register(Notification)