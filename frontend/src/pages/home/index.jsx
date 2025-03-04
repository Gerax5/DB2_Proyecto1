import { useEffect, useState } from "react";
import "./home.css"; // Importamos los estilos

const Home = () => {
  const [feed, setFeed] = useState([]);
  const userName = localStorage.getItem("userName");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  // Buscar usuarios
  const handleSearch = (e) => {
    if (e.key === "Enter" && search.trim() !== "") {
      fetch(`http://localhost:8000/search_user/${search}`)
        .then((response) => response.json())
        .then((data) => {
          if (Array.isArray(data)) {
            const filteredResults = data.filter(
              (user) => user.user_name !== userName
            );
            setSearchResults(filteredResults);
          } else {
            setSearchResults([]);
          }
        })
        .catch((error) => console.error("Error en la búsqueda:", error));
    }
  };

  const handleLike = (id_publicacion) => {
    fetch(`http://localhost:8000/like_post/${id_publicacion}`, {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.nuevas_reacciones !== undefined) {
          // ✅ Actualizar el estado del feed con la nueva cantidad de reacciones
          setFeed((prevFeed) =>
            prevFeed.map((post) =>
              post.id_publicacion === id_publicacion
                ? { ...post, reacciones: data.nuevas_reacciones }
                : post
            )
          );
        }
      })
      .catch((error) => console.error("Error al dar like:", error));
  };

  // Obtener el feed
  useEffect(() => {
    const userId = localStorage.getItem("userId");

    if (userId) {
      fetch(`http://localhost:8000/feed/${userId}`)
        .then((response) => response.json())
        .then((data) => {
          if (Array.isArray(data)) {
            setFeed(data);
          } else {
            setFeed([]);
          }
        })
        .catch((error) => console.error("Error al obtener el feed:", error));
    }
  }, []);

  return (
    <div className="home-container">
      <h1>Buscar Usuarios</h1>

      {/* Barra de búsqueda */}
      <div className="search-bar">
        <input
          type="text"
          placeholder="Buscar usuario..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleSearch}
        />
      </div>

      {/* Resultados de búsqueda */}
      <div className="search-results">
        {searchResults.length > 0 ? (
          searchResults.map((user) => (
            <div key={user.user_name} className="user-card">
              <img
                src={user.foto || "https://via.placeholder.com/50"}
                alt={user.user_name}
              />
              <p>{user.user_name}</p>
            </div>
          ))
        ) : (
          <p>No se encontraron usuarios.</p>
        )}
      </div>

      <h1>Publicaciones de personas que sigues</h1>

      {/* Lista de publicaciones */}
      <div className="feed-container">
        {feed.length > 0 ? (
          feed.map((post, index) => (
            <div key={index} className="post-card">
              <p className="post-header">
                {post.tipo === "COMPARTE"
                  ? `🔄 ${post.autor} compartió`
                  : `📝 ${post.autor} publicó`}
              </p>

              <p className="post-text">{post.texto}</p>

              <p className="post-footer">
                📅 {post.fecha} |
                <span
                  className="like-button"
                  onClick={() => handleLike(post.id_publicacion)}
                >
                  ❤️ {post.reacciones}
                </span>
              </p>
            </div>
          ))
        ) : (
          <p>No hay publicaciones recientes de las personas que sigues.</p>
        )}
      </div>
    </div>
  );
};

export default Home;
