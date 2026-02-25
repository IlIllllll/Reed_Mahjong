# Series of functions to be called when an event happens
# Deals with handoffs and threading for async code

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Max
from django.db.utils import IntegrityError
from django.utils import timezone
import random

from .auth_utils import get_user_from_token
from .models import (
    GameHistory,
    GameOperation,
    GameParticipantResult,
    Player,
    Room,
    UserScoreProfile,
)

numbers = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
suites = ["bamboo", "wan", "circle"]

# convert table for tile suite and number
convert_table = {
    "bamboo1": 1,
    "bamboo2": 2,
    "bamboo3": 3,
    "bamboo4": 4,
    "bamboo5": 5,
    "bamboo6": 6,
    "bamboo7": 7,
    "bamboo8": 8,
    "bamboo9": 9,
    "wan1": 11,
    "wan2": 12,
    "wan3": 13,
    "wan4": 14,
    "wan5": 15,
    "wan6": 16,
    "wan7": 17,
    "wan8": 18,
    "wan9": 19,
    "circle1": 21,
    "circle2": 22,
    "circle3": 23,
    "circle4": 24,
    "circle5": 25,
    "circle6": 26,
    "circle7": 27,
    "circle8": 28,
    "circle9": 29,
}

tile_keys = list(convert_table.keys())


"""
url = ws://localhost:8000/ws/socket-server
"""


class PlayerConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = "test"

    """
    This app  consumer handles websocket connections for chat clients.
    It uses AsyncJsonWebsocketConsumer, which means all the handling functions
    must be async functions, and any sync work (like ORM access) has to be
    behind database_sync_to_async or sync_to_async. For more, read
    http://channels.readthedocs.io/en/latest/topics/consumers.html
    """

    # Called on connection
    async def connect(self):
        # To accept the connection call:
        await self.accept()
        # Add the connection to a named group to enable
        # sending messages to a group of connections at once.

    async def send_json_message(self, event):
        message = event["message"]
        await self.send_json(message)

    async def disconnect(self, close_code):
        # # Called when WebSocket closes
        # print("Disconnected")

        # Remove connection from group
        await self.remove_from_group()

    async def receive_json(self, content):
        # Handles incoming JSON message from client
        print(f"Received JSON message:{content}")

        """
        FORMATTING:
        'type': 'getVariable',
        'player' : 'player_id', //* should be set by backend, put here now for testing
        'tile' : {'suite': 'bamboo', 'number': '1'}, //* should be set by backend, put here now for testing
        'tiles' : {{'suite': 'bamboo', 'number': '1'}, {'suite': 'bamboo', 'number': '2'}, {'suite': 'bamboo', 'number': '3'}}, //* should be set by backend, put here now for testing (start_game)
        'result_type': 'variable', //* should be set by backend, put here now for testing
        'room_id': `000`, //* should be set by backend, put here now for testing
        'status': '202', //* should be set by backend, put here now for testing
        """

        room_id = content.get("room_id")
        event_type = content.get("type")
        if event_type is None:
            await self.send_json({"message": "missing event type", "status": "400"})
            return

        if event_type != "echo":
            user = await self.authenticate_event(content)
            if user is None:
                return
            content["username"] = user.username

        if event_type == "echo":
            await self.send_json(content)
        elif event_type == "create_room":
            await self.create_room(content)
        elif event_type == "discard_tile":
            await self.discard_tile(room_id, content)
        elif event_type == "performing_hu":
            await self.performing_hu(room_id, content)
        elif event_type == "performing_peng":
            await self.performing_peng(room_id, content)
        elif event_type == "performing_chi":
            await self.performing_chi(room_id, content)
        elif event_type == "join_room":
            await self.join_room(room_id, content)
        elif event_type == "start_game":
            await self.start_game(room_id)
        elif event_type == "reset_game":
            await self.reset_game(room_id)
        else:
            await self.send_json({"message": "not an event type"})

    """
    Room Operations
    """

    async def create_room(self, content):
        print("Creating room")
        # creates a room

        try:
            # Generating random_id for room
            while True:
                random_room_id = random.randint(10000000, 99999999)
                qs = await self.filter_room_models(random_room_id)
                if await sync_to_async(qs.count)() == 0:
                    break
                else:
                    continue

            # create room and player models
            player = await self.create_player_model(player_id=content.get("username"))
            room = await self.create_room_model(random_room_id)
            player.room = room
            room.player1 = player.player_id

            # save models
            await sync_to_async(room.save)()
            await sync_to_async(player.save)()

            # set room_name for groups
            self.room_name = "Room" + str(random_room_id)

            # Add the connection to a named group to enable
            # sending messages to a group of connections at once.
            await self.channel_layer.group_add(
                self.room_name, self.channel_name  # Group name
            )

            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "send_json",
                    "message": f"You are now connected to the group {self.room_name}!",
                    "room_id": str(random_room_id),
                    "result_type": "notification",
                    "status": "202",
                },
            )

            await self.send_json(
                {
                    "message": "room_created",
                    "room_id": random_room_id,
                    "result_type": "room_id",
                    "status": "202",
                }
            )

        except IntegrityError:
            await self.send_json(
                {"message": "Player already in a room.", "status": "400"}
            )

    async def join_room(self, room_id, content):
        # test join_room function from front end
        """await self.send_json({
            'message': 'Successfully joined room!',
            'room_id': room_id,
            'result_type': 'room_id',
            'status': '202',
        })
        return"""
        print("Joining room")

        player_result = await self.filter_player_models(
            player_id=content.get("username")
        )
        if await sync_to_async(player_result.count)() == 0:
            player = await self.create_player_model(player_id=content.get("username"))
        else:
            player = await sync_to_async(player_result.first)()
        room_result = await self.filter_room_models(room_id)
        if await sync_to_async(room_result.count)() == 0:
            await self.send_json({"message": "Room does not exist", "status": "400"})
            return
        else:
            room = await sync_to_async(room_result.first)()

        if (
            room.player1 == player.player_id
            or room.player2 == player.player_id
            or room.player3 == player.player_id
            or room.player4 == player.player_id
        ):
            print("Player already in room")
            await self.send_json(
                {"Bad Request": "Player already in room", "status": "400"}
            )
            return

        self.room_name = "Room" + str(room_id)

        # Add the connection to a named group to enable
        # sending messages to a group of connections at once.
        await self.channel_layer.group_add(
            self.room_name, self.channel_name  # `room_id` is the group name
        )

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "send_json",
                "message": f"{content.get('username')} join {self.room_name}!",
                "room_id": str(room_id),
                "result_type": "notification",
                "status": "202",
            },
        )

        if room.player2 == "":
            room.player2 = player.player_id
            player.room = room
            await sync_to_async(player.save)()
            await sync_to_async(room.save)()

        elif room.player3 == "":
            room.player3 = player.player_id
            player.room = room
            await sync_to_async(player.save)()
            await sync_to_async(room.save)()

        elif room.player4 == "":
            room.player4 = player.player_id
            player.room = room

            await sync_to_async(player.save)()
            await sync_to_async(room.save)()
            await self.start_game(room_id)

        else:
            print("Room is full")
            await self.send_json({"Bad Request": "Room is full", "status": "400"})

        await self.send_json(
            {
                "message": "Player joined",
                "room_id": room_id,
                "result_type": "room_id",
                "status": "202",
            }
        )
        return

    """
    
    Game Operations
    
    """

    async def start_game(self, room_id):
        # test start game broadcast to front end
        """print("Starting game")
        await self.send_json(
            {
                "type": "send_json",
                "message": "Temporary message",
                'player': 'placeholder player',
                'tiles': 'placeholder tiles',
                'room_id': str(room_id),
                'result_type': 'start_tiles',
                'status': '202'
            })
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "send_json",
                "message": "Player drawn tiles",
                'player': 'placeholder player',
                'tiles': 'placeholder tiles',
                'room_id': str(room_id),
                'result_type': 'start_tiles',
                'status': '202'
            })
        return"""

        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            if room.game_mode == 0:
                if (
                    room.player1 == ""
                    or room.player2 == ""
                    or room.player3 == ""
                    or room.player4 == ""
                ):
                    await self.send_json(
                        {"message": "Not enough players", "status": "400"}
                    )
                    return

                else:
                    print("Starting game")
                    room.game_mode = 1
                    await sync_to_async(room.save)()
                    players = [room.player1, room.player2,
                               room.player3, room.player4]
                    zhuangjia = random.choice(players)
                    room.current_player = zhuangjia
                    room.zhuangjia = zhuangjia
                    await sync_to_async(room.save)()
                    await self.create_game_history(
                        room_id=str(room_id),
                        participants=players,
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="START_GAME",
                        actor_username=zhuangjia,
                        payload={
                            "zhuangjia": zhuangjia,
                            "players": players,
                        },
                    )

                    # distribute 13 tiles to each player
                    for player in players:
                        print(player)
                        player_result = await self.filter_player_models(player)
                        player1 = await sync_to_async(player_result.first)()

                        tiles = []
                        while len(tiles) < 13:
                            # draw a random tile
                            suite = random.choice(suites)
                            number = random.choice(numbers)
                            new_tile = {"suite": suite, "number": number}
                            key = suite + number
                            # if no more such tile in the room, draw another
                            # tile
                            while room.__dict__[key] == 0:
                                suite = random.choice(suites)
                                number = random.choice(numbers)
                                new_tile = {"suite": suite, "number": number}
                                key = suite + number

                            tiles.append(new_tile)
                            player1.__dict__[key] += 1
                            room.__dict__[key] -= 1

                        await sync_to_async(player1.save)()
                        await sync_to_async(room.save)()

                        await self.channel_layer.group_send(
                            self.room_name,
                            {
                                "type": "send_json",
                                "message": "Player drawn tiles",
                                "player": player,
                                "tiles": tiles,
                                "room_id": str(room_id),
                                "result_type": "start_tiles",
                                "status": "202",
                            },
                        )
                        await self.record_game_operation(
                            room_id=room_id,
                            operation_type="START_TILES",
                            actor_username=player,
                            payload={
                                "tiles": tiles,
                            },
                        )

                    # distribute 1 tiles to first player
                    player_result = await self.filter_player_models(zhuangjia)
                    player1 = await sync_to_async(player_result.first)()

                    suite = random.choice(suites)
                    number = random.choice(numbers)
                    new_tile = {"suite": suite, "number": number}
                    key = suite + number
                    while room.__dict__[key] == 0:
                        suite = random.choice(suites)
                        number = random.choice(numbers)
                        new_tile = {"suite": suite, "number": number}
                        key = suite + number

                    player1.__dict__[key] += 1
                    room.__dict__[key] -= 1

                    await sync_to_async(player1.save)()
                    await sync_to_async(room.save)()

                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "Zhuangjia tile drawn",
                            "player": room.zhuangjia,
                            "tile": new_tile,
                            "room_id": str(room_id),
                            "result_type": "draw_tile",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="DRAW_TILE",
                        actor_username=room.zhuangjia,
                        payload={
                            "tile": new_tile,
                            "is_initial_draw": True,
                        },
                    )

                    # announce start game to all players
                    # ? maybe not necessary?
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "Game started",
                            "current_player": room.current_player,
                            "room_id": str(room_id),
                            "result_type": "start_game",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="GAME_STARTED_BROADCAST",
                        actor_username=room.current_player,
                        payload={
                            "current_player": room.current_player,
                        },
                    )
            else:
                print("Game already started")
                await self.send_json(
                    {"message": "Game already exists", "status": "400"}
                )
        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})

    async def reset_game(self, room_id):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            if room.game_mode == 1:
                finalized_result = await self.finalize_game_result(room_id)
                if finalized_result is not None:
                    await self.record_game_operation_by_game_id(
                        game_history_id=finalized_result["game_id"],
                        room_id=room_id,
                        operation_type="GAME_RESET_DRAW",
                        payload={"score_delta": finalized_result["score_delta"]},
                    )
                """
                more checking condition
                if a player declares a win, the game is over
                we start the game again
                """
                print("Restarting game")
                room.game_mode = 0
                await sync_to_async(room.save)()
                players = [room.player1, room.player2,
                           room.player3, room.player4]

                for player in players:
                    player_result = await self.filter_player_models(player)
                    player1 = await sync_to_async(player_result.first)()

                    for suite in suites:
                        for number in numbers:
                            key = suite + number
                            player1.__dict__[key] = 0
                            room.__dict__[key] = 4

                    await sync_to_async(player1.save)()
                    await sync_to_async(room.save)()

                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "send_json",
                        "message": "Game reset",
                        "room_id": str(room_id),
                        "result_type": "game_reset",
                        "status": "202",
                    },
                )

                await self.start_game(room_id)
            else:
                print("Game already started")
                await self.send_json(
                    {"message": "Game already exists", "status": "400"}
                )
        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})

    """
    Game Logic
    - start game (current player = zhuangjia)
    - current player discard a tile
        - current player discard (player[tile] -= 1)
        - current player = next player (update no matter what)
        - check if there are players can win the game (not implemented yet)
            - if yes, send notification to all players
            - wait for the response
                - if yes, perform win. Then the game ends. Call reset_game() to restart game. (back to step 1)
                - if no, check if there are players can perform peng
                    - if yes, send notification to all players
                    - wait for the response
                        - if yes, perform peng. Then the current player = the player who perform peng. Then the current player discard again (back to step 2)
                        - if no, check if the current player (the next player of who discarded the tile) can peform chi
                            - if yes, send notification to all players
                            - wait for the response
                                - if yes, perform chi. Then the current player discard again (back to step 2)
                                - if no, current player draws tile. Then the current player discard again (back to step 2)
                    
    """

    async def draw_tile(self, room_id, uid):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            count = 0
            for suite in suites:
                for number in numbers:
                    key = suite + number
                    count += room.__dict__[key]
                    break

            if count != 0:
                if room.player1 == uid:
                    room.current_player = uid
                    player_result = await self.filter_player_models(room.player1)
                    player1 = await sync_to_async(player_result.first)()

                elif room.player2 == uid:
                    room.current_player = uid
                    player_result = await self.filter_player_models(room.player2)
                    player1 = await sync_to_async(player_result.first)()

                elif room.player3 == uid:
                    room.current_player = uid
                    player_result = await self.filter_player_models(room.player3)
                    player1 = await sync_to_async(player_result.first)()

                elif room.player4 == uid:
                    room.current_player = uid
                    player_result = await self.filter_player_models(room.player4)
                    player1 = await sync_to_async(player_result.first)()

                suite = random.choice(suites)
                number = random.choice(numbers)
                new_tile = {"suite": suite, "number": number}
                key = suite + number
                while room.__dict__[key] == 0:
                    suite = random.choice(suites)
                    number = random.choice(numbers)
                    new_tile = {"suite": suite, "number": number}
                    key = suite + number

                player1.__dict__[key] += 1
                room.__dict__[key] -= 1

                print(f"{player1.player_id} drew {suite}{number}")

                await sync_to_async(player1.save)()
                await sync_to_async(room.save)()

                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "send_json",
                        "message": "tile drawn",
                        "player": player1.player_id,
                        "current_player": room.current_player,
                        "tile": new_tile,
                        "room_id": str(room_id),
                        "result_type": "draw_tile",
                        "status": "202",
                    },
                )
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="DRAW_TILE",
                    actor_username=player1.player_id,
                    payload={
                        "tile": new_tile,
                        "current_player": room.current_player,
                    },
                )

            else:
                print("Out of tiles")
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="OUT_OF_TILES",
                    payload={"message": "No tiles left in wall."},
                )
                finalized_result = await self.finalize_game_result(room_id)
                if finalized_result is not None:
                    await self.record_game_operation_by_game_id(
                        game_history_id=finalized_result["game_id"],
                        room_id=room_id,
                        operation_type="GAME_DRAW",
                        payload={
                            "score_delta": finalized_result["score_delta"],
                        },
                    )
                await self.reset_game(room_id)
                await self.send_json({"message": "out of tiles", "status": "400"})
        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})

    """
    If a player discards a tile, the tile is removed from the player's hand and added to the discard pile
    The discarded tile will be broadcasted to all players in the room
    Then when the frontend receives the discarded tile, it will perform peng and chi checks (peng > chi as priority-wise)
    """

    async def discard_tile(self, room_id, content):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()
            player_result = await self.filter_player_models(content.get("username"))
            player1 = await sync_to_async(player_result.first)()

            tile = content.get("tile").get("suite") + str(
                content.get("tile").get("number")
            )
            player1.__dict__[tile] -= 1

            if room.player1 == content.get("username"):
                room.current_player = room.player2
            elif room.player2 == content.get("username"):
                room.current_player = room.player3
            elif room.player3 == content.get("username"):
                room.current_player = room.player4
            elif room.player4 == content.get("username"):
                room.current_player = room.player1

            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "send_json",
                    "message": "Discard_tile",
                    "player": content.get("username"),
                    "current_player": room.current_player,
                    "tile": content.get("tile"),
                    "room_id": str(room_id),
                    "result_type": "discard_tile",
                    "status": "202",
                },
            )
            await self.record_game_operation(
                room_id=room_id,
                operation_type="DISCARD_TILE",
                actor_username=content.get("username"),
                payload={
                    "tile": content.get("tile"),
                    "next_player": room.current_player,
                },
            )

            await sync_to_async(player1.save)()
            await sync_to_async(room.save)()

            """
            Check whether can perform hu or peng or chi.
            """

            await self.check_hu(room_id, content)

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    """
    
    check if a player can perform chi or peng.
    If not, then it will do anything
    If yes, it will prompt the player to perform peng or chi and wait for the player's response
    
    """

    async def check_hu(self, room_id, content):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            suite = content.get("tile").get("suite")
            number = str(content.get("tile").get("number"))

            tile = suite + number

            players = [room.player1, room.player2, room.player3, room.player4]
            players.remove(content.get("username"))

            print("\nStart checking wins")
            print("players remaining: ", players)

            # helper function - basic recurssion
            # maybe can be implement as dynamic programming, but haven't thought of a way yet
            def is_win(tiles):
                # checking pair (base case)
                if len(tiles) == 2 and tiles[0] == tiles[1]:
                    return True

                # checking triplet
                for i in range(len(tiles) - 2):
                    if i < len(tiles) - 4 and tiles[i] == tiles[i + 4]:
                        return False

                for i in range(len(tiles) - 2):
                    tmp = tiles[i]
                    # shunzi
                    if (tmp in tiles) and (tmp + 1 in tiles) and (tmp + 2 in tiles):
                        # take out the shunzi
                        this_tiles = tiles.copy()
                        this_tiles.remove(tmp)
                        this_tiles.remove(tmp + 1)
                        this_tiles.remove(tmp + 2)
                        if is_win(this_tiles):
                            return True
                    # kezi
                    elif tmp == tiles[i + 2]:
                        # take out the kezi
                        this_tiles = tiles.copy()
                        if tiles.count(tmp) == 3:
                            this_tiles.remove(tmp)
                            this_tiles.remove(tmp)
                            this_tiles.remove(tmp)
                        elif tiles.count(tmp) == 4:
                            this_tiles.remove(tmp)
                            this_tiles.remove(tmp)
                            this_tiles.remove(tmp)
                            this_tiles.remove(tmp)
                        if is_win(this_tiles):
                            return True
                return False

            for player in players:
                print("checking hu for player: ", player)
                player_result = await self.filter_player_models(player)
                player1 = await sync_to_async(player_result.first)()

                tiles = []
                for keys in convert_table:
                    for _ in range(player1.__dict__[keys]):
                        tiles.append(convert_table[keys])
                tiles.append(convert_table[tile])
                tiles.sort()
                print("tiles: ", tiles)

                if is_win(tiles):
                    print(f"{player} can perform hu")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_hu",
                            "player": player,
                            "tile": content.get("tile"),
                            "room_id": str(room_id),
                            "result_type": "hu_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="HU_PROMPT",
                        actor_username=player,
                        payload={
                            "tile": content.get("tile"),
                            "triggered_by": content.get("username"),
                        },
                    )
                    return "successful"

            print("No one can perform hu")
            await self.check_peng(
                room_id, uid=content.get("username"), suite=suite, number=number
            )

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    """
    

    if the response is yes, then the player can perform peng or chi
    
    """

    async def performing_hu(self, room_id, content):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()
            player_result = await self.filter_player_models(content.get("username"))
            player1 = await sync_to_async(player_result.first)()

            suite = content.get("tile").get("suite")
            number = str(content.get("tile").get("number"))

            tile = suite + number

            if content.get("action") == "1":
                print("Player performing hu")
                player1.__dict__[tile] += 1
                room.current_player = content.get("username")
                await sync_to_async(player1.save)()
                await sync_to_async(room.save)()
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="HU_ACCEPTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )
                finalized_result = await self.finalize_game_result(
                    room_id=room_id, winner_username=content.get("username")
                )
                if finalized_result is not None:
                    await self.record_game_operation_by_game_id(
                        game_history_id=finalized_result["game_id"],
                        room_id=room_id,
                        operation_type="GAME_FINISHED",
                        actor_username=content.get("username"),
                        payload={
                            "winner": content.get("username"),
                            "score_delta": finalized_result["score_delta"],
                        },
                    )

                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "send_json",
                        "message": "game ends",
                        "player": content.get("username"),
                        "current_player": room.current_player,
                        "tile": content.get("tile"),
                        "room_id": str(room_id),
                        "result_type": "game_end",
                        "status": "202",
                    },
                )

                await self.reset_game(room_id)

            else:
                print("Player not performing hu")
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="HU_REJECTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )
                await self.check_peng(
                    room_id, uid=room.current_player, suite=suite, number=number
                )

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    """
    Checking peng and performing peng
    """

    async def check_peng(self, room_id, uid, suite, number):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            tile = suite + number

            players = [room.player1, room.player2, room.player3, room.player4]
            players.remove(uid)

            print("\nStart checking peng")
            print("players remaining: ", players)

            for player in players:
                print("checking peng for player: ", player)
                player_result = await self.filter_player_models(player)
                player1 = await sync_to_async(player_result.first)()
                # check if the player can perform peng or not
                # for testing: send chi to first player
                if player1.__dict__[tile] >= 2:
                    print(f"{player} can perform peng")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_peng",
                            "player": player,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "peng_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="PENG_PROMPT",
                        actor_username=player,
                        payload={
                            "tile": {"suite": suite, "number": str(number)},
                            "triggered_by": uid,
                        },
                    )
                    return "successful"

            print("No one can perform peng")

            await self.check_chi(
                room_id, uid=room.current_player, suite=suite, number=number
            )

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    """
    
    if the response is yes, then the player can perform peng or chi
    
    """

    async def performing_peng(self, room_id, content):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()
            player_result = await self.filter_player_models(content.get("username"))
            player1 = await sync_to_async(player_result.first)()

            suite = content.get("tile").get("suite")
            number = str(content.get("tile").get("number"))

            tile = suite + number

            if content.get("action") == "1":
                # check if the player can perform peng or not
                print("Player performing peng")
                player1.__dict__[tile] += 1
                room.current_player = content.get("username")
                await sync_to_async(player1.save)()
                await sync_to_async(room.save)()
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="PENG_ACCEPTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )

                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "send_json",
                        "message": "peng performed",
                        "player": content.get("username"),
                        "current_player": room.current_player,
                        "tile": content.get("tile"),
                        "room_id": str(room_id),
                        "result_type": "placeholder",
                        "status": "202",
                    },
                )

            else:
                print("Player not performing peng")
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="PENG_REJECTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )

                await self.check_chi(
                    room_id, uid=room.current_player, suite=suite, number=number
                )

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    """
    Checking chi if no pengs are available
    """

    async def check_chi(self, room_id, uid, suite, number):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()

            if room.player1 == uid:
                player_result = await self.filter_player_models(room.player1)
                player1 = await sync_to_async(player_result.first)()

            elif room.player2 == uid:
                player_result = await self.filter_player_models(room.player2)
                player1 = await sync_to_async(player_result.first)()

            elif room.player3 == uid:
                player_result = await self.filter_player_models(room.player3)
                player1 = await sync_to_async(player_result.first)()

            elif room.player4 == uid:
                player_result = await self.filter_player_models(room.player4)
                player1 = await sync_to_async(player_result.first)()

            print("\nStart checking chi")

            print("Checking chi for tile " + suite + str(number))
            print("Checking chi for player: " + player1.player_id)

            # check if the player can perform Chi or not
            if int(number) >= 3 and int(number) <= 7:
                key1 = suite + str(int(number) - 2)
                key2 = suite + str(int(number) - 1)
                key3 = suite + str(int(number) + 1)
                key4 = suite + str(int(number) + 2)

                if (
                    (player1.__dict__[key1] !=
                     0 and player1.__dict__[key2] != 0)
                    or (player1.__dict__[key3] != 0 and player1.__dict__[key4] != 0)
                    or (player1.__dict__[key2] != 0 and player1.__dict__[key3] != 0)
                ):
                    print("Can perform chi")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_chi",
                            "player": player1.player_id,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "chi_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="CHI_PROMPT",
                        actor_username=player1.player_id,
                        payload={"tile": {"suite": suite, "number": str(number)}},
                    )
                    return "successful"

            elif int(number) == 2:
                key1 = suite + str(1)
                key2 = suite + str(3)
                key3 = suite + str(4)

                if (player1.__dict__[key1] != 0 and player1.__dict__[key2] != 0) or (
                    player1.__dict__[key2] != 0 and player1.__dict__[key3] != 0
                ):
                    print("Can perform chi")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_chi",
                            "player": player1.player_id,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "chi_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="CHI_PROMPT",
                        actor_username=player1.player_id,
                        payload={"tile": {"suite": suite, "number": str(number)}},
                    )
                    return "successful"

            elif int(number) == 8:
                key1 = suite + str(6)
                key2 = suite + str(7)
                key3 = suite + str(9)

                if (player1.__dict__[key1] != 0 and player1.__dict__[key2] != 0) or (
                    player1.__dict__[key2] != 0 and player1.__dict__[key3] != 0
                ):
                    print("Can perform chi")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_chi",
                            "player": player1.player_id,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "chi_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="CHI_PROMPT",
                        actor_username=player1.player_id,
                        payload={"tile": {"suite": suite, "number": str(number)}},
                    )
                    return "successful"

            elif int(number) == 1:
                key1 = suite + str(2)
                key2 = suite + str(3)

                if player1.__dict__[key1] != 0 and player1.__dict__[key2] != 0:
                    print("Can perform chi")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_chi",
                            "player": player1.player_id,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "chi_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="CHI_PROMPT",
                        actor_username=player1.player_id,
                        payload={"tile": {"suite": suite, "number": str(number)}},
                    )
                    return "successful"
            elif int(number) == 9:
                key1 = suite + str(7)
                key2 = suite + str(8)
                if player1.__dict__[key1] != 0 and player1.__dict__[key2] != 0:
                    print("Can perform chi")
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "send_json",
                            "message": "can_perform_chi",
                            "player": player1.player_id,
                            "tile": {"suite": suite, "number": str(number)},
                            "room_id": str(room_id),
                            "result_type": "chi_prompt",
                            "status": "202",
                        },
                    )
                    await self.record_game_operation(
                        room_id=room_id,
                        operation_type="CHI_PROMPT",
                        actor_username=player1.player_id,
                        payload={"tile": {"suite": suite, "number": str(number)}},
                    )
                    return "successful"

            print(f"Cannot perform chi, drawing tile for {player1.player_id}")
            await self.draw_tile(room_id, room.current_player)

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    async def performing_chi(self, room_id, content):
        try:
            room_result = await self.filter_room_models(room_id)
            room = await sync_to_async(room_result.first)()
            player_result = await self.filter_player_models(content.get("username"))
            player1 = await sync_to_async(player_result.first)()

            tile = content.get("tile").get("suite") + str(
                content.get("tile").get("number")
            )

            if content.get("action") == "1":
                # check if the player can perform peng or not
                print("Performing chi")
                player1.__dict__[tile] += 1
                room.current_player = content.get("username")
                await sync_to_async(player1.save)()
                await sync_to_async(room.save)()
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="CHI_ACCEPTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )

                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "send_json",
                        "message": "action finished",
                        "player": content.get("username"),
                        "current_player": room.current_player,
                        "tile": content.get("tile"),
                        "room_id": str(room_id),
                        "result_type": "placeholder",
                        "status": "202",
                    },
                )

            else:
                print(
                    "Player not performing chi, drawing tile for "
                    + str(room.current_player)
                )
                await self.record_game_operation(
                    room_id=room_id,
                    operation_type="CHI_REJECTED",
                    actor_username=content.get("username"),
                    payload={"tile": content.get("tile")},
                )
                await self.draw_tile(room_id, room.current_player)

        except Room.DoesNotExist:
            await self.send_json({"message': 'Room doesn't exist" "status": "404"})
            return

        except Player.DoesNotExist:
            await self.send_json({"message': 'Player doesn't exist" "status": "404"})
            return

    async def add_to_group(self):
        await self.channel_layer.group_add(
            self.room_name, self.channel_name  # `room_id` is the group name
        )

    async def remove_from_group(self):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    # methods to access player and room model databases:
    @database_sync_to_async
    def get_room_model(self, room_id):
        return Room.objects.get(room_id=room_id)

    @database_sync_to_async
    def create_room_model(self, room_id):
        return Room.objects.create(room_id=room_id)

    @database_sync_to_async
    def filter_room_models(self, room_id):
        return Room.objects.filter(room_id=room_id)

    @database_sync_to_async
    def get_player_model(self, player_id):
        return Player.objects.get(player_id=player_id)

    @database_sync_to_async
    def create_player_model(self, player_id):
        return Player.objects.create(player_id=player_id)

    @database_sync_to_async
    def filter_player_models(self, player_id):
        return Player.objects.filter(player_id=player_id)

    @database_sync_to_async
    def filter_player_models_room(self, room_id):
        return Player.objects.filter(room__room_id=room_id)

    async def authenticate_event(self, content):
        token = content.get("auth_token")
        if token is None:
            await self.send_json({"message": "Authentication required.", "status": "401"})
            return None

        user = await self.get_authenticated_user(token)
        if user is None:
            await self.send_json({"message": "Invalid or expired token.", "status": "401"})
            return None
        return user

    @database_sync_to_async
    def get_authenticated_user(self, token):
        return get_user_from_token(token)

    @database_sync_to_async
    def create_game_history(self, room_id, participants):
        room = Room.objects.filter(room_id=room_id).first()
        game_history = GameHistory.objects.create(
            room=room,
            room_id_snapshot=str(room_id),
            participants=[player for player in participants if player],
            status=GameHistory.STATUS_IN_PROGRESS,
        )
        return game_history.id

    @database_sync_to_async
    def get_active_game_history_id(self, room_id):
        game_history = (
            GameHistory.objects.filter(
                room_id_snapshot=str(room_id),
                status=GameHistory.STATUS_IN_PROGRESS,
            )
            .order_by("-id")
            .first()
        )
        if game_history is None:
            return None
        return game_history.id

    @database_sync_to_async
    def build_room_state_snapshot(self, room_id):
        room = Room.objects.filter(room_id=room_id).first()
        if room is None:
            return {}

        players = [room.player1, room.player2, room.player3, room.player4]
        player_state = {}
        for player_id in players:
            if not player_id:
                continue
            player_obj = Player.objects.filter(player_id=player_id).first()
            if player_obj is None:
                continue
            player_state[player_id] = {key: player_obj.__dict__[key] for key in tile_keys}

        return {
            "room_id": room.room_id,
            "game_mode": room.game_mode,
            "current_player": room.current_player,
            "zhuangjia": room.zhuangjia,
            "players": [player for player in players if player],
            "room_tiles": {key: room.__dict__[key] for key in tile_keys},
            "player_tiles": player_state,
        }

    @database_sync_to_async
    def create_game_operation(
        self,
        game_history_id,
        operation_type,
        actor_username,
        payload,
        state_snapshot,
    ):
        with transaction.atomic():
            current_max_sequence = (
                GameOperation.objects.select_for_update()
                .filter(game_history_id=game_history_id)
                .aggregate(max_seq=Max("sequence"))
                .get("max_seq")
            ) or 0
            operation = GameOperation.objects.create(
                game_history_id=game_history_id,
                sequence=current_max_sequence + 1,
                operation_type=operation_type,
                actor_username=actor_username or "",
                payload=payload or {},
                state_snapshot=state_snapshot or {},
            )
        return operation.sequence

    async def record_game_operation(
        self,
        room_id,
        operation_type,
        actor_username="",
        payload=None,
    ):
        game_history_id = await self.get_active_game_history_id(room_id)
        if game_history_id is None:
            return
        await self.record_game_operation_by_game_id(
            game_history_id=game_history_id,
            room_id=room_id,
            operation_type=operation_type,
            actor_username=actor_username,
            payload=payload,
        )

    async def record_game_operation_by_game_id(
        self,
        game_history_id,
        room_id,
        operation_type,
        actor_username="",
        payload=None,
    ):
        snapshot = await self.build_room_state_snapshot(room_id)
        await self.create_game_operation(
            game_history_id=game_history_id,
            operation_type=operation_type,
            actor_username=actor_username,
            payload=payload or {},
            state_snapshot=snapshot,
        )

    @database_sync_to_async
    def finalize_game_result(self, room_id, winner_username=None):
        game_history = (
            GameHistory.objects.filter(
                room_id_snapshot=str(room_id),
                status=GameHistory.STATUS_IN_PROGRESS,
            )
            .order_by("-id")
            .first()
        )
        if game_history is None:
            return None

        participants = [name for name in game_history.participants if name]
        if not participants:
            room = Room.objects.filter(room_id=room_id).first()
            if room is not None:
                participants = [
                    player_name
                    for player_name in [room.player1, room.player2, room.player3, room.player4]
                    if player_name
                ]

        if winner_username and winner_username in participants:
            game_history.status = GameHistory.STATUS_FINISHED
            score_delta = {
                username: 15 if username == winner_username else -5
                for username in participants
            }
        else:
            winner_username = None
            game_history.status = GameHistory.STATUS_DRAW
            score_delta = {username: 0 for username in participants}

        winner_user = (
            User.objects.filter(username=winner_username).first()
            if winner_username
            else None
        )

        game_history.winner = winner_user
        game_history.ended_at = timezone.now()
        game_history.score_delta = score_delta
        game_history.save()

        for username in participants:
            user = User.objects.filter(username=username).first()
            result = GameParticipantResult.RESULT_DRAW
            if winner_username is not None:
                result = (
                    GameParticipantResult.RESULT_WIN
                    if username == winner_username
                    else GameParticipantResult.RESULT_LOSS
                )

            score_change = score_delta.get(username, 0)
            total_score_after_game = score_change

            if user is not None:
                profile, _ = UserScoreProfile.objects.get_or_create(user=user)
                profile.games_played += 1
                if result == GameParticipantResult.RESULT_WIN:
                    profile.wins += 1
                elif result == GameParticipantResult.RESULT_LOSS:
                    profile.losses += 1
                else:
                    profile.draws += 1
                profile.total_score += score_change
                profile.save()
                total_score_after_game = profile.total_score

            GameParticipantResult.objects.create(
                game_history=game_history,
                user=user,
                username_snapshot=username,
                result=result,
                score_delta=score_change,
                total_score_after_game=total_score_after_game,
            )

        return {
            "game_id": game_history.id,
            "score_delta": score_delta,
            "status": game_history.status,
        }
