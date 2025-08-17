from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers.user_serializers import RegisterSerializer, LoginSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import random

User = get_user_model()
class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    Allows new users to register with email, phone, and password.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        tags=["auth"],
        operation_description="This endpoint allows anyone to create a new user account by providing "
                                "an email, phone number, and password. The response contains the created user data.",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="User successfully registered",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "phone": "+213600000000",
                        "is_active": True
                    }
                }
            ),
            400: openapi.Response(
                description="Validation error",
                examples={
                    "application/json": {
                        "email": ["This field is required."],
                        "password": ["Password must be at least 8 characters long."]
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Custom POST method to ensure swagger schema works."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ----------------------------
# Login
# ----------------------------
login_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
        'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number (if logging in with phone)'),
        'password': openapi.Schema(type=openapi.TYPE_STRING, description='User password'),
    },
    required=['password'],
)

login_response = openapi.Response(
    description="Successful login response",
    examples={
        "application/json": {
            "refresh": "refresh_token_here",
            "access": "access_token_here"
        }
    }
)

class LoginView(APIView):
    @swagger_auto_schema(
        request_body=login_request_body,
        responses={200: login_response, 400: "Invalid credentials"},
        operation_summary="Login endpoint",
        tags=["auth"],
        operation_description="Login with either **email + password** or **phone + password**. "
                                "Only one of `email` or `phone` should be provided.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        })


# ----------------------------
# Logout
# ----------------------------

class LogoutView(APIView):
    @swagger_auto_schema(
        tags=["auth"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The refresh token to blacklist"
                ),
            },
            example={"refresh": "your_refresh_token_here"},
        ),
        responses={
            205: "Logout successful. Token blacklisted.",
            400: "Invalid or missing token."
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# ----------------------------
# Send Phone Code
# ----------------------------
class SendPhoneCodeView(APIView):
    @swagger_auto_schema(
        operation_description="Send a verification code to the provided phone number",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone"],
            properties={
                "phone": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number to send the code"),
            },
        ),
        responses={200: "Code sent successfully", 400: "Invalid phone number"},
        tags=["auth"]
    )
    def post(self, request):
        phone = request.data.get("phone")
        if not phone:
            return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a random 6-digit code
        code = str(random.randint(100000, 999999))

        # TODO: Save this code in DB/Redis/cache for verification
        # TODO: Integrate with SMS provider (Twilio, etc.)
        print(f"DEBUG: Verification code for {phone} is {code}")

        return Response({"message": f"Verification code sent to {phone}"}, status=status.HTTP_200_OK)


# ----------------------------
# Verify Phone
# ----------------------------
class VerifyPhoneView(APIView):
    @swagger_auto_schema(
        operation_description="Verify phone number with the code received via SMS",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["phone", "code"],
            properties={
                "phone": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number to verify"),
                "code": openapi.Schema(type=openapi.TYPE_STRING, description="Verification code"),
            },
        ),
        responses={200: "Phone verified successfully", 400: "Invalid code or phone"},
        tags=["auth"]
    )
    def post(self, request):
        phone = request.data.get("phone")
        code = request.data.get("code")

        if not phone or not code:
            return Response({"error": "Phone and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Retrieve code from DB/Redis/cache and compare
        if code != "123456":  # placeholder check
            return Response({"error": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone)
            user.is_phone_verified = True
            user.save()
            return Response({"message": "Phone verified successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this phone does not exist"}, status=status.HTTP_400_BAD_REQUEST)
