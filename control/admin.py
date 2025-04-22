from django.contrib import admin
from .models import HourlyUsage, UserUsage

admin.site.register(UserUsage)
admin.site.register(HourlyUsage)