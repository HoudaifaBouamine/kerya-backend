from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "phone_number", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")
        password = attrs.get("password")

        if not password:
            raise serializers.ValidationError("Password is required")

        if bool(email) == bool(phone):  # both filled or both empty
            raise serializers.ValidationError(
                "You must provide either email OR phone, not both."
            )

        attrs["username"] = email or phone  # unify for authenticate()
        return attrs

