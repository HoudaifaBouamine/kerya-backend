from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

# ------------------------
# Register
# ------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "phone_number", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# Response serializer (hide password in output)
class RegisterResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone_number", "is_active")
        read_only_fields = ("id", "email", "phone_number", "is_active")


# ------------------------
# Login
# ------------------------
# class LoginSerializer(serializers.Serializer):
#     email = serializers.EmailField(required=False)
#     phone = serializers.CharField(required=False)
#     password = serializers.CharField(write_only=True)

#     def validate(self, attrs):
#         email = attrs.get("email")
#         phone = attrs.get("phone")
#         password = attrs.get("password")

#         if not password:
#             raise serializers.ValidationError("Password is required")

#         if bool(email) == bool(phone):  # both filled or both empty
#             raise serializers.ValidationError(
#                 "You must provide either email OR phone, not both."
#             )

#         attrs["username"] = email or phone
#         return attrs

class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class PhoneLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
# Login response (JWT tokens)
class LoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


# ------------------------
# Logout
# ------------------------
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# ------------------------
# Phone Verification
# ------------------------
class SendPhoneCodeSerializer(serializers.Serializer):
    phone = serializers.CharField()


class VerifyPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
