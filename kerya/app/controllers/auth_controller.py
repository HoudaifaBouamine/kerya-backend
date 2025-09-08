from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout

from ..serializers.user_serializers import (
    EmailLoginSerializer,
    PhoneLoginSerializer,
    RegisterSerializer,
    RegisterResponseSerializer,
    # LoginSerializer,
    LoginResponseSerializer,
    LogoutSerializer,
    SendPhoneCodeSerializer,
    VerifyPhoneSerializer,
)

User = get_user_model()


# ----------------------------
# Register
# ----------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user",
        tags=["auth"],
        request_body=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(RegisterResponseSerializer(user).data, status=status.HTTP_201_CREATED)


# ----------------------------
# Login
# ----------------------------
# class LoginView(APIView):
#     permission_classes = [permissions.AllowAny]

#     @swagger_auto_schema(
#         operation_summary="Login with email or phone",
#         tags=["auth"],
#         # request_body=LoginSerializer,
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 "email": openapi.Schema(type=openapi.TYPE_STRING, example="admin@gmail.com"),
#                 "phone": openapi.Schema(type=openapi.TYPE_STRING, example="+213675706769"),
#                 "password": openapi.Schema(type=openapi.TYPE_STRING, example="admin"),
#             },
#             required=["email", "password"]
#         ),
#         responses={200: LoginResponseSerializer, 400: "Invalid credentials"},
#     )
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         user = authenticate(
#             request,
#             username=serializer.validated_data["username"],
#             password=serializer.validated_data["password"],
#         )

#         if not user:
#             return Response({"detail": "Invalid credentials"}, status=400)

#         refresh = RefreshToken.for_user(user)
#         return Response(LoginResponseSerializer({
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#         }).data)
            

class EmailLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Login with email",
        tags=["auth"],
        manual_parameters=[
            openapi.Parameter(
                "auth_type",
                openapi.IN_QUERY,
                description="Authentication type: 'jwt' (default) or 'session'",
                type=openapi.TYPE_STRING,
                enum=["jwt", "session"],
                required=False,
            )
        ],
        request_body=EmailLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "jwt": {
                            "refresh": "eyJ0eXAiOiJKV1QiLCJh...",
                            "access": "eyJ0eXAiOiJKV1QiLCJh..."
                        },
                        "session": {
                            "detail": "Logged in with session"
                        }
                    }
                },
            ),
            400: "Invalid credentials",
        },
    )
    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        auth_type = request.query_params.get("auth_type", "jwt")

        user = authenticate(request, email=email, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        if auth_type == "session":
            login(request, user)
            return Response({"detail": "Logged in with session"})
        else:
            refresh = RefreshToken.for_user(user)
            return Response(LoginResponseSerializer({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }).data)


from django.contrib.auth import login
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken

from kerya.app.serializers import PhoneLoginSerializer, LoginResponseSerializer


class PhoneLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Login with phone",
        tags=["auth"],
        manual_parameters=[
            openapi.Parameter(
                "auth_type",
                openapi.IN_QUERY,
                description="Authentication type: `jwt` or `session`",
                type=openapi.TYPE_STRING,
                required=False,
                default="jwt"
            )
        ],
        request_body=PhoneLoginSerializer,
        responses={200: LoginResponseSerializer, 400: "Invalid credentials"},
    )
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request,
            phone=phone,
            password=password,
        )

        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)

        # Decide based on query param
        auth_type = request.query_params.get("auth_type", "jwt").lower()

        if auth_type == "session":
            login(request, user)  # sets sessionid + csrftoken cookies
            return Response({"detail": "Logged in with session."})

        # Default: JWT
        refresh = RefreshToken.for_user(user)
        return Response(LoginResponseSerializer({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }).data)



# ----------------------------
# Logout
# ----------------------------
class LogoutView(APIView):
    @swagger_auto_schema(
        tags=["auth"],
        operation_summary="Logout (JWT or Session)",
        manual_parameters=[
            openapi.Parameter(
                "auth_type",
                openapi.IN_QUERY,
                description="Authentication type: `jwt` or `session`",
                type=openapi.TYPE_STRING,
                required=False,
                default="jwt",
            )
        ],
        request_body=LogoutSerializer,
        responses={
            205: "Logout successful",
            400: "Invalid or missing token",
        },
    )
    def post(self, request):
        auth_type = request.query_params.get("auth_type", "jwt").lower()

        if auth_type == "session":
            # End the Django session
            logout(request)
            return Response(
                {"detail": "Session logged out."},
                status=status.HTTP_205_RESET_CONTENT
            )

        # Default: JWT logout (blacklist refresh token)
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
            return Response(
                {"detail": "JWT logged out."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception:
            return Response(
                {"detail": "Invalid or missing token."},
                status=status.HTTP_400_BAD_REQUEST
            )

# ----------------------------
# Send Phone Code
# ----------------------------
class SendPhoneCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["auth"],
        operation_summary="Send phone verification code",
        request_body=SendPhoneCodeSerializer,
        responses={200: "Code sent successfully", 400: "Invalid phone number"},
    )
    def post(self, request):
        serializer = SendPhoneCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]

        # TODO: send actual SMS
        import random
        code = str(random.randint(100000, 999999))
        print(f"DEBUG: Verification code for {phone} is {code}")

        return Response({"message": f"Verification code sent to {phone}"}, status=status.HTTP_200_OK)


# ----------------------------
# Verify Phone
# ----------------------------
class VerifyPhoneView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        tags=["auth"],
        operation_summary="Verify phone number",
        request_body=VerifyPhoneSerializer,
        responses={200: "Phone verified successfully", 400: "Invalid code or phone"},
    )
    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        if code != "123456":  # TODO: replace with real verification
            return Response({"error": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone=phone)
            user.is_phone_verified = True
            user.save()
            return Response({"message": "Phone verified successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this phone does not exist"}, status=status.HTTP_400_BAD_REQUEST)
