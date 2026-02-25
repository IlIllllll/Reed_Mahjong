import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./UsernameProvider";

export default function AuthPage() {
  const { login, register, isLoading, isAuthenticated } = useAuth();
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  const fromPath = location.state?.from?.pathname || "/";

  useEffect(() => {
    if (isAuthenticated) {
      navigate(fromPath, { replace: true });
    }
  }, [fromPath, isAuthenticated, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMessage("");
    const normalizedUsername = username.trim();
    if (!normalizedUsername || !password) {
      setErrorMessage("请输入用户名和密码。");
      return;
    }

    const action = mode === "login" ? login : register;
    const result = await action(normalizedUsername, password);
    if (!result.ok) {
      setErrorMessage(result.message);
    }
  }

  return (
    <div className="page authPage">
      <div className="authCard">
        <h2>{mode === "login" ? "登录" : "注册"} Reedies' Mahjong</h2>
        <form onSubmit={handleSubmit}>
          <label>
            用户名
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              maxLength={32}
            />
          </label>
          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="button authSubmitButton" type="submit" disabled={isLoading}>
            {isLoading ? "提交中..." : mode === "login" ? "登录并进入大厅" : "注册并进入大厅"}
          </button>
        </form>

        {errorMessage && <p className="authError">{errorMessage}</p>}

        <button
          className="button authSwitchButton"
          type="button"
          onClick={() => setMode((prevMode) => (prevMode === "login" ? "register" : "login"))}
          disabled={isLoading}
        >
          {mode === "login" ? "没有账号？去注册" : "已有账号？去登录"}
        </button>
      </div>
    </div>
  );
}
