import { useEffect, useState } from "react";

const Home = () => {
  const [following, setFollowing] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [search, setSearch] = useState("");
  const userName = localStorage.getItem("userName");

  useEffect(() => {
    if (userName) {
      // Obtener lista de seguidos
      fetch(`http://localhost:8000/follows/${userName}`)
        .then((response) => response.json())
        .then((data) => {
          if (Array.isArray(data)) {
            setFollowing(data);
          } else {
            setFollowing([]);
          }
        })
        .catch((error) => console.error("Error al obtener la lista:", error));

      // Obtener recomendaciones
      fetch(`http://localhost:8000/recommendations/${userName}`)
        .then((response) => response.json())
        .then((data) => {
          if (Array.isArray(data)) {
            setRecommendations(data);
          } else {
            setRecommendations([]);
          }
        })
        .catch((error) =>
          console.error("Error al obtener recomendaciones:", error)
        );
    }
  }, [userName]);

  const handleFollow = (followedUser, userName) => {
    const userId = localStorage.getItem("userId");
    fetch("http://localhost:8000/relations/sigue_a/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id1: userId,
        id2: followedUser,
        recomendado_por_algoritmo: true,
        notificaciones_activas: false,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        alert(`Ahora sigues a ${followedUser}`);
        setRecommendations(
          recommendations.filter((user) => user.user_name !== followedUser)
        );
        setFollowing([...following, { user_name: userName, foto: "" }]);
      })
      .catch((error) => console.error("Error al seguir usuario:", error));
  };

  const filteredUsers = following.filter((user) =>
    user.user_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "20px",
      }}
    >
      <h1>Personas que sigues</h1>

      {/* Barra de búsqueda */}
      <input
        type="text"
        placeholder="Buscar usuario..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          padding: "10px",
          width: "300px",
          marginBottom: "20px",
          borderRadius: "5px",
          border: "1px solid #ccc",
        }}
      />

      {/* Lista de usuarios seguidos */}
      <div style={{ width: "100%", maxWidth: "400px" }}>
        {filteredUsers.length > 0 ? (
          filteredUsers.map((user) => (
            <div
              key={user.user_name}
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#f0f0f0",
                padding: "10px",
                borderRadius: "5px",
                marginBottom: "10px",
              }}
            >
              <img
                src={user.foto || "https://via.placeholder.com/50"}
                alt={user.user_name}
                style={{
                  width: "50px",
                  height: "50px",
                  borderRadius: "50%",
                  marginRight: "10px",
                }}
              />
              <p style={{ fontSize: "18px" }}>{user.user_name}</p>
            </div>
          ))
        ) : (
          <p>No sigues a nadie aún.</p>
        )}
      </div>

      {/* Recomendaciones de usuarios */}
      <h2>Personas que podrías seguir</h2>
      <div style={{ width: "100%", maxWidth: "400px" }}>
        {recommendations.length > 0 ? (
          recommendations.map((user) => (
            <div
              key={user.user_name}
              style={{
                display: "flex",
                alignItems: "center",
                backgroundColor: "#e0e0e0",
                padding: "10px",
                borderRadius: "5px",
                marginBottom: "10px",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center" }}>
                <img
                  src={user.foto || "https://via.placeholder.com/50"}
                  alt={user.user_name}
                  style={{
                    width: "50px",
                    height: "50px",
                    borderRadius: "50%",
                    marginRight: "10px",
                  }}
                />
                <p style={{ fontSize: "18px" }}>{user.user_name}</p>
              </div>
              <button
                onClick={() => handleFollow(user.id_usuario, user.user_name)}
                style={{
                  padding: "8px 12px",
                  backgroundColor: "blue",
                  color: "white",
                  border: "none",
                  borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                Seguir
              </button>
            </div>
          ))
        ) : (
          <p>No hay recomendaciones por ahora.</p>
        )}
      </div>
    </div>
  );
};

export default Home;
