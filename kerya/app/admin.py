from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models.user import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "email", "phone", "role", "is_active")
    search_fields = ("email", "phone")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "role")}),
        ("Verification", {"fields": ("is_phone_verified", "is_email_verified")}),
    )
