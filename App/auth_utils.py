from django.contrib.auth.models import User
from django.core import signing

TOKEN_SALT = "reedies-mahjong-auth"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def generate_auth_token(user):
    payload = {"user_id": user.id, "username": user.username}
    return signing.dumps(payload, salt=TOKEN_SALT)


def get_user_from_token(token):
    if not token:
        return None

    try:
        payload = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE_SECONDS,
        )
    except signing.BadSignature:
        return None
    except signing.SignatureExpired:
        return None

    user_id = payload.get("user_id")
    username = payload.get("username")
    if not user_id or not username:
        return None

    try:
        return User.objects.get(id=user_id, username=username, is_active=True)
    except User.DoesNotExist:
        return None


def extract_bearer_token(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:].strip()
