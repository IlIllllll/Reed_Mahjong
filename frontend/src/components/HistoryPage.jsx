import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./UsernameProvider";

const API_BASE_URL = "http://localhost:8000/api";

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

export default function HistoryPage() {
  const { token, user, stats, logout } = useAuth();
  const [historyStats, setHistoryStats] = useState(stats || null);
  const [history, setHistory] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [selectedOperationSequence, setSelectedOperationSequence] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let isActive = true;

    async function loadHistory() {
      setLoadingList(true);
      setErrorMessage("");
      try {
        const response = await fetch(`${API_BASE_URL}/history/`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await response.json();
        if (!response.ok) {
          if (response.status === 401) {
            logout();
            navigate("/auth", { replace: true });
            return;
          }
          throw new Error(data.message || "历史记录加载失败。");
        }
        if (isActive) {
          setHistory(data.games || []);
          setHistoryStats(data.stats || null);
        }
      } catch (error) {
        if (isActive) {
          setErrorMessage(error.message);
        }
      } finally {
        if (isActive) {
          setLoadingList(false);
        }
      }
    }

    loadHistory();
    return () => {
      isActive = false;
    };
  }, [logout, navigate, token]);

  async function handleSelectGame(gameId) {
    setLoadingDetail(true);
    setErrorMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/history/${gameId}/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || "对局详情加载失败。");
      }
      setSelectedGame(data.game);
      const operations = data.game?.operations || [];
      setSelectedOperationSequence(operations.length ? operations[operations.length - 1].sequence : null);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setLoadingDetail(false);
    }
  }

  const selectedOperation = useMemo(() => {
    if (!selectedGame?.operations || selectedOperationSequence === null) {
      return null;
    }
    return (
      selectedGame.operations.find(
        (operation) => operation.sequence === selectedOperationSequence
      ) || null
    );
  }, [selectedGame, selectedOperationSequence]);

  return (
    <div className="page historyPage">
      <div className="historyHeader">
        <div>
          <h2>用户历史</h2>
          <p>
            当前用户：<b>{user?.username}</b>
          </p>
        </div>
        <div className="historyNavActions">
          <Link className="button" to="/">
            返回大厅
          </Link>
        </div>
      </div>

      <div className="historyStats">
        <div className="historyStatCard">总分：{historyStats?.total_score ?? "-"}</div>
        <div className="historyStatCard">胜场：{historyStats?.wins ?? "-"}</div>
        <div className="historyStatCard">负场：{historyStats?.losses ?? "-"}</div>
        <div className="historyStatCard">总场次：{historyStats?.games_played ?? "-"}</div>
      </div>

      {errorMessage && <p className="historyError">{errorMessage}</p>}

      <div className="historyBody">
        <div className="historyListPanel">
          <h3>历史对局</h3>
          {loadingList ? (
            <p>加载中...</p>
          ) : history.length === 0 ? (
            <p>暂无历史对局。</p>
          ) : (
            <table className="historyTable">
              <thead>
                <tr>
                  <th>房间</th>
                  <th>结果</th>
                  <th>分数变化</th>
                  <th>操作数</th>
                  <th>结束时间</th>
                  <th>详情</th>
                </tr>
              </thead>
              <tbody>
                {history.map((game) => (
                  <tr key={game.game_id}>
                    <td>{game.room_id}</td>
                    <td>{game.result}</td>
                    <td>{game.score_delta}</td>
                    <td>{game.operations_count}</td>
                    <td>{formatDateTime(game.ended_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="button"
                        onClick={() => handleSelectGame(game.game_id)}
                        disabled={loadingDetail}
                      >
                        查看
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="historyDetailPanel">
          <h3>对局回放</h3>
          {!selectedGame ? (
            <p>请选择一局对局查看详情。</p>
          ) : (
            <>
              <p>
                房间 {selectedGame.room_id}，状态 {selectedGame.status}，赢家{" "}
                {selectedGame.winner || "无（流局）"}
              </p>
              <p>
                开始：{formatDateTime(selectedGame.started_at)}；结束：
                {formatDateTime(selectedGame.ended_at)}
              </p>

              <div className="historyParticipants">
                <h4>参与者结果</h4>
                <ul>
                  {selectedGame.participants.map((participant) => (
                    <li key={participant.username}>
                      {participant.username} - {participant.result} ({participant.score_delta >= 0 ? "+" : ""}
                      {participant.score_delta})，总分 {participant.total_score_after_game}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="historyOperationsSection">
                <h4>操作时间线（点击可查看当时状态）</h4>
                <div className="historyOperationList">
                  {selectedGame.operations.map((operation) => (
                    <button
                      type="button"
                      key={operation.sequence}
                      className={`historyOperationItem ${
                        selectedOperationSequence === operation.sequence ? "active" : ""
                      }`}
                      onClick={() => setSelectedOperationSequence(operation.sequence)}
                    >
                      <span>#{operation.sequence}</span>
                      <span>{operation.operation_type}</span>
                      <span>{operation.actor_username || "-"}</span>
                      <span>{formatDateTime(operation.created_at)}</span>
                    </button>
                  ))}
                </div>
                {selectedOperation && (
                  <div className="historyOperationSnapshot">
                    <h5>
                      当前步骤：#{selectedOperation.sequence} {selectedOperation.operation_type}
                    </h5>
                    <p>操作载荷：</p>
                    <pre>{JSON.stringify(selectedOperation.payload, null, 2)}</pre>
                    <p>当时牌局状态快照：</p>
                    <pre>{JSON.stringify(selectedOperation.state_snapshot, null, 2)}</pre>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
