from django.conf import settings
from django.db import models


class Room(models.Model):
    room_id = models.CharField(max_length=8, unique=True)
    game_mode = models.BooleanField(default=False)

    player1 = models.CharField(max_length=50, default="")
    player2 = models.CharField(max_length=50, default="")
    player3 = models.CharField(max_length=50, default="")
    player4 = models.CharField(max_length=50, default="")

    current_player = models.CharField(max_length=50, default="")
    zhuangjia = models.CharField(max_length=50, default="")

    bamboo1 = models.SmallIntegerField(default=4)
    bamboo2 = models.SmallIntegerField(default=4)
    bamboo3 = models.SmallIntegerField(default=4)
    bamboo4 = models.SmallIntegerField(default=4)
    bamboo5 = models.SmallIntegerField(default=4)
    bamboo6 = models.SmallIntegerField(default=4)
    bamboo7 = models.SmallIntegerField(default=4)
    bamboo8 = models.SmallIntegerField(default=4)
    bamboo9 = models.SmallIntegerField(default=4)
    wan1 = models.SmallIntegerField(default=4)
    wan2 = models.SmallIntegerField(default=4)
    wan3 = models.SmallIntegerField(default=4)
    wan4 = models.SmallIntegerField(default=4)
    wan5 = models.SmallIntegerField(default=4)
    wan6 = models.SmallIntegerField(default=4)
    wan7 = models.SmallIntegerField(default=4)
    wan8 = models.SmallIntegerField(default=4)
    wan9 = models.SmallIntegerField(default=4)
    circle1 = models.SmallIntegerField(default=4)
    circle2 = models.SmallIntegerField(default=4)
    circle3 = models.SmallIntegerField(default=4)
    circle4 = models.SmallIntegerField(default=4)
    circle5 = models.SmallIntegerField(default=4)
    circle6 = models.SmallIntegerField(default=4)
    circle7 = models.SmallIntegerField(default=4)
    circle8 = models.SmallIntegerField(default=4)
    circle9 = models.SmallIntegerField(default=4)


class Player(models.Model):
    player_id = models.CharField(max_length=50, unique=True)

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="player_set", null=True
    )

    bamboo1 = models.SmallIntegerField(default=0)
    bamboo2 = models.SmallIntegerField(default=0)
    bamboo3 = models.SmallIntegerField(default=0)
    bamboo4 = models.SmallIntegerField(default=0)
    bamboo5 = models.SmallIntegerField(default=0)
    bamboo6 = models.SmallIntegerField(default=0)
    bamboo7 = models.SmallIntegerField(default=0)
    bamboo8 = models.SmallIntegerField(default=0)
    bamboo9 = models.SmallIntegerField(default=0)
    wan1 = models.SmallIntegerField(default=0)
    wan2 = models.SmallIntegerField(default=0)
    wan3 = models.SmallIntegerField(default=0)
    wan4 = models.SmallIntegerField(default=0)
    wan5 = models.SmallIntegerField(default=0)
    wan6 = models.SmallIntegerField(default=0)
    wan7 = models.SmallIntegerField(default=0)
    wan8 = models.SmallIntegerField(default=0)
    wan9 = models.SmallIntegerField(default=0)
    circle1 = models.SmallIntegerField(default=0)
    circle2 = models.SmallIntegerField(default=0)
    circle3 = models.SmallIntegerField(default=0)
    circle4 = models.SmallIntegerField(default=0)
    circle5 = models.SmallIntegerField(default=0)
    circle6 = models.SmallIntegerField(default=0)
    circle7 = models.SmallIntegerField(default=0)
    circle8 = models.SmallIntegerField(default=0)
    circle9 = models.SmallIntegerField(default=0)


class UserScoreProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="score_profile",
    )
    total_score = models.IntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    games_played = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-total_score", "user__username")

    def __str__(self):
        return f"{self.user.username}: {self.total_score}"


class GameHistory(models.Model):
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_FINISHED = "FINISHED"
    STATUS_DRAW = "DRAW"
    STATUS_CHOICES = (
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_FINISHED, "Finished"),
        (STATUS_DRAW, "Draw"),
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game_histories",
    )
    room_id_snapshot = models.CharField(max_length=8, db_index=True)
    participants = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_game_histories",
    )
    score_delta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return f"Game {self.id} Room {self.room_id_snapshot}"


class GameParticipantResult(models.Model):
    RESULT_WIN = "WIN"
    RESULT_LOSS = "LOSS"
    RESULT_DRAW = "DRAW"
    RESULT_CHOICES = (
        (RESULT_WIN, "Win"),
        (RESULT_LOSS, "Loss"),
        (RESULT_DRAW, "Draw"),
    )

    game_history = models.ForeignKey(
        GameHistory,
        on_delete=models.CASCADE,
        related_name="participant_results",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game_participant_results",
    )
    username_snapshot = models.CharField(max_length=150, db_index=True)
    result = models.CharField(max_length=8, choices=RESULT_CHOICES, default=RESULT_DRAW)
    score_delta = models.IntegerField(default=0)
    total_score_after_game = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-id",)
        unique_together = (("game_history", "username_snapshot"),)

    def __str__(self):
        return f"{self.username_snapshot} {self.result} ({self.score_delta})"


class GameOperation(models.Model):
    game_history = models.ForeignKey(
        GameHistory,
        on_delete=models.CASCADE,
        related_name="operations",
    )
    sequence = models.PositiveIntegerField()
    operation_type = models.CharField(max_length=64)
    actor_username = models.CharField(max_length=150, default="", blank=True)
    payload = models.JSONField(default=dict, blank=True)
    state_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sequence", "id")
        unique_together = (("game_history", "sequence"),)

    def __str__(self):
        return f"Game {self.game_history_id} #{self.sequence} {self.operation_type}"
