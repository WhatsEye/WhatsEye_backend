from django.contrib import admin

from .models import (BadWord, ChildBadWords, ChildLocation, HourlyUsage,
                     Notification, UserUsage)

admin.site.register(UserUsage)
admin.site.register(HourlyUsage)
admin.site.register(ChildLocation)
admin.site.register(Notification)
admin.site.register(BadWord)
admin.site.register(ChildBadWords)
