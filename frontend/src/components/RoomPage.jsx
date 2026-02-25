import { Link, useParams } from "react-router-dom";
import GameBoard from "./GameBoard";
import { useAuth } from "./UsernameProvider";

export default function RoomPage() {
  // Get roomid from url
  let { roomid } = useParams();
  const { user } = useAuth();

  return (
    <div className="page roomPage">
      <div className="mainPageTopBar">
        <div>
          用户：<b>{user?.username}</b>
        </div>
        <div className="mainPageActions">
          <Link className="button" to="/">
            返回大厅
          </Link>
          <Link className="button" to="/history">
            用户历史
          </Link>
        </div>
      </div>
      <h1>Room {roomid} </h1>
      <GameBoard room_id={roomid} />
    </div>
  );
}
