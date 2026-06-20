from django.contrib import admin
from .models import AIModel

# tells django how to show/modify ai models
@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_url", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "agent_url")
