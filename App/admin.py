from django.contrib import admin
from .models import *


class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room_id",
        "game_mode",
        "current_player",
        "zhuangjia",
        "player1",
        "player1",
        "player2",
        "player3",
        "player4",
        "bamboo1",
        "bamboo2",
        "bamboo3",
        "bamboo4",
        "bamboo5",
        "bamboo6",
        "bamboo7",
        "bamboo8",
        "bamboo9",
        "wan1",
        "wan2",
        "wan3",
        "wan4",
        "wan5",
        "wan6",
        "wan7",
        "wan8",
        "wan9",
        "circle1",
        "circle2",
        "circle3",
        "circle4",
        "circle5",
        "circle6",
        "circle7",
        "circle8",
        "circle9",
    )


class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "player_id",
        "room",
        "bamboo1",
        "bamboo2",
        "bamboo3",
        "bamboo4",
        "bamboo5",
        "bamboo6",
        "bamboo7",
        "bamboo8",
        "bamboo9",
        "wan1",
        "wan2",
        "wan3",
        "wan4",
        "wan5",
        "wan6",
        "wan7",
        "wan8",
        "wan9",
        "circle1",
        "circle2",
        "circle3",
        "circle4",
        "circle5",
        "circle6",
        "circle7",
        "circle8",
        "circle9",
    )


class UserScoreProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "total_score",
        "wins",
        "losses",
        "draws",
        "games_played",
        "updated_at",
    )


class GameHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room_id_snapshot",
        "status",
        "winner",
        "started_at",
        "ended_at",
    )
    search_fields = ("room_id_snapshot",)


class GameParticipantResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "game_history",
        "username_snapshot",
        "result",
        "score_delta",
        "total_score_after_game",
    )
    search_fields = ("username_snapshot",)


class GameOperationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "game_history",
        "sequence",
        "operation_type",
        "actor_username",
        "created_at",
    )
    search_fields = ("operation_type", "actor_username")


# Register your models here.
admin.site.register(Room, RoomAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(UserScoreProfile, UserScoreProfileAdmin)
admin.site.register(GameHistory, GameHistoryAdmin)
admin.site.register(GameParticipantResult, GameParticipantResultAdmin)
admin.site.register(GameOperation, GameOperationAdmin)
