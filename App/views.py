import json

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets

from .auth_utils import extract_bearer_token, generate_auth_token, get_user_from_token
from .models import (
    GameHistory,
    GameOperation,
    GameParticipantResult,
    Player,
    Room,
    UserScoreProfile,
)
from .serializers import PlayerSerializer, RoomSerializer


class RoomView(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    queryset = Room.objects.all()


class PlayerView(viewsets.ModelViewSet):
    serializer_class = PlayerSerializer
    queryset = Player.objects.all()


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


def _get_or_create_score_profile(user):
    profile, _ = UserScoreProfile.objects.get_or_create(user=user)
    return profile


def _serialize_profile(profile):
    return {
        "total_score": profile.total_score,
        "wins": profile.wins,
        "losses": profile.losses,
        "draws": profile.draws,
        "games_played": profile.games_played,
    }


def _get_authenticated_user(request):
    token = extract_bearer_token(request)
    if not token:
        return None, None
    user = get_user_from_token(token)
    return user, token


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    data = _parse_json_body(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return JsonResponse(
            {"message": "Username must be at least 3 characters long."},
            status=400,
        )

    if not username.replace("_", "").isalnum():
        return JsonResponse(
            {"message": "Username can only contain letters, numbers and underscore."},
            status=400,
        )

    if len(password) < 6:
        return JsonResponse(
            {"message": "Password must be at least 6 characters long."},
            status=400,
        )

    if User.objects.filter(username=username).exists():
        return JsonResponse({"message": "Username already exists."}, status=400)

    user = User.objects.create_user(username=username, password=password)
    profile = _get_or_create_score_profile(user)
    token = generate_auth_token(user)

    return JsonResponse(
        {
            "message": "register_success",
            "token": token,
            "user": {"username": user.username},
            "stats": _serialize_profile(profile),
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    data = _parse_json_body(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({"message": "Invalid username or password."}, status=401)

    profile = _get_or_create_score_profile(user)
    token = generate_auth_token(user)
    return JsonResponse(
        {
            "message": "login_success",
            "token": token,
            "user": {"username": user.username},
            "stats": _serialize_profile(profile),
        }
    )


@require_http_methods(["GET"])
def auth_me_view(request):
    user, _ = _get_authenticated_user(request)
    if user is None:
        return JsonResponse({"message": "Unauthorized."}, status=401)

    profile = _get_or_create_score_profile(user)
    return JsonResponse(
        {
            "message": "ok",
            "user": {"username": user.username},
            "stats": _serialize_profile(profile),
        }
    )


@require_http_methods(["GET"])
def history_list_view(request):
    user, _ = _get_authenticated_user(request)
    if user is None:
        return JsonResponse({"message": "Unauthorized."}, status=401)

    profile = _get_or_create_score_profile(user)
    results = (
        GameParticipantResult.objects.filter(user=user)
        .select_related("game_history", "game_history__winner")
        .order_by("-game_history__started_at", "-id")
    )

    game_ids = [result.game_history_id for result in results]
    operation_counts = {
        item["game_history_id"]: item["total"]
        for item in GameOperation.objects.filter(game_history_id__in=game_ids)
        .values("game_history_id")
        .annotate(total=Count("id"))
    }

    games = []
    for result in results:
        game = result.game_history
        games.append(
            {
                "game_id": game.id,
                "room_id": game.room_id_snapshot,
                "status": game.status,
                "result": result.result,
                "score_delta": result.score_delta,
                "total_score_after_game": result.total_score_after_game,
                "winner": game.winner.username if game.winner else None,
                "started_at": game.started_at.isoformat() if game.started_at else None,
                "ended_at": game.ended_at.isoformat() if game.ended_at else None,
                "operations_count": operation_counts.get(game.id, 0),
            }
        )

    return JsonResponse(
        {
            "message": "ok",
            "user": {"username": user.username},
            "stats": _serialize_profile(profile),
            "games": games,
        }
    )


@require_http_methods(["GET"])
def history_detail_view(request, game_id):
    user, _ = _get_authenticated_user(request)
    if user is None:
        return JsonResponse({"message": "Unauthorized."}, status=401)

    participation = GameParticipantResult.objects.filter(
        user=user, game_history_id=game_id
    ).first()
    if participation is None:
        return JsonResponse({"message": "Game history not found."}, status=404)

    game = participation.game_history
    participants = (
        GameParticipantResult.objects.filter(game_history=game)
        .select_related("user")
        .order_by("-score_delta", "username_snapshot")
    )
    operations = GameOperation.objects.filter(game_history=game).order_by("sequence", "id")

    return JsonResponse(
        {
            "message": "ok",
            "game": {
                "game_id": game.id,
                "room_id": game.room_id_snapshot,
                "status": game.status,
                "winner": game.winner.username if game.winner else None,
                "started_at": game.started_at.isoformat() if game.started_at else None,
                "ended_at": game.ended_at.isoformat() if game.ended_at else None,
                "score_delta": game.score_delta,
                "participants": [
                    {
                        "username": participant.username_snapshot,
                        "result": participant.result,
                        "score_delta": participant.score_delta,
                        "total_score_after_game": participant.total_score_after_game,
                    }
                    for participant in participants
                ],
                "your_result": {
                    "username": participation.username_snapshot,
                    "result": participation.result,
                    "score_delta": participation.score_delta,
                    "total_score_after_game": participation.total_score_after_game,
                },
                "operations": [
                    {
                        "sequence": operation.sequence,
                        "operation_type": operation.operation_type,
                        "actor_username": operation.actor_username,
                        "payload": operation.payload,
                        "state_snapshot": operation.state_snapshot,
                        "created_at": operation.created_at.isoformat(),
                    }
                    for operation in operations
                ],
            },
        }
    )
