import { useState } from "react";
import { useNavigate } from "react-router-dom";

const Login = () => {
  const [userName, setUserName] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch("http://localhost:8000/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_name: userName, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`Bienvenido, ${data.user_name}!`);

        // Guardamos `id_usuario` y `user_name` en localStorage
        localStorage.setItem("userId", data.id_usuario);
        localStorage.setItem("userName", data.user_name);

        navigate("/home");
      } else {
        setMessage(data.detail || "Error en la autenticación");
      }
    } catch (e) {
      setMessage("Error al conectar con la API", e);
    }
  };

  const handleSingup = () => {
    navigate("/signup");
  };

  return (
    <div
      style={{
        backgroundColor: "blue",
        width: "100%",
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      <h1 style={{ color: "white" }}>Social NET</h1>
      <form
        onSubmit={handleLogin}
        style={{
          display: "flex",
          flexDirection: "column",
          backgroundColor: "white",
          padding: "20px",
          borderRadius: "10px",
          boxShadow: "0px 0px 10px rgba(0,0,0,0.3)",
        }}
      >
        <label>
          Usuario:
          <input
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            required
            style={{ margin: "5px", padding: "8px", width: "100%" }}
          />
        </label>

        <label>
          Contraseña:
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ margin: "5px", padding: "8px", width: "100%" }}
          />
        </label>

        <button
          type="submit"
          style={{
            marginTop: "10px",
            padding: "10px",
            backgroundColor: "blue",
            color: "white",
            border: "none",
            cursor: "pointer",
          }}
        >
          Iniciar sesión
        </button>
      </form>

      {message && (
        <p style={{ color: "white", marginTop: "10px" }}>{message}</p>
      )}

      <p style={{ color: "white", marginTop: "10px" }}>
        ¿No tienes una cuenta?{" "}
        <p
          onClick={handleSingup}
          style={{ color: "yellow", cursor: "pointer" }}
        >
          Regístrate aquí
        </p>
      </p>
    </div>
  );
};

export default Login;
