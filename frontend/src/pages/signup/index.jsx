import { useState } from "react";
import { useNavigate } from "react-router-dom";

const SignUp = () => {
  const [userName, setUserName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isInfluencer, setIsInfluencer] = useState(false);
  const [age, setAge] = useState("");
  const [profilePic, setProfilePic] = useState(
    "https://thispersondoesnotexist.com/"
  );
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleSignUp = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch("http://localhost:8000/signup/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_name: userName,
          email: email,
          password: password,
          is_influencer: isInfluencer,
          age: parseInt(age),
          profile_pic: profilePic,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage("Registro exitoso. Redirigiendo al login...");
        setTimeout(() => navigate("/"), 2000);
      } else {
        setMessage(data.detail || "Error en el registro");
      }
    } catch (e) {
      setMessage("Error al conectar con la API");
    }
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
      <h1 style={{ color: "white" }}>Registro</h1>
      <form
        onSubmit={handleSignUp}
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
          />
        </label>
        <label>
          Email:
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Contraseña:
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <label>
          Edad:
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            required
          />
        </label>
        <label>
          Influencer:
          <input
            type="checkbox"
            checked={isInfluencer}
            onChange={(e) => setIsInfluencer(e.target.checked)}
          />
        </label>
        <button type="submit">Registrarse</button>
      </form>
      {message && (
        <p style={{ color: "white", marginTop: "10px" }}>{message}</p>
      )}
    </div>
  );
};

export default SignUp;
