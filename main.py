from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase
from datetime import date, timedelta
import random
from faker import Faker

# Instancia de FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen (puedes cambiarlo a ["http://localhost:5173"] si solo es React)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

# Configuración de Neo4j
URI = "neo4j+s://6e796de7.databases.neo4j.io"
AUTH = ("neo4j", "sgmvLP0_IuV6rNHxSaTR0sTYqAumzrCUAwhl3ZsjvcE")
driver = GraphDatabase.driver(URI, auth=AUTH)

fake = Faker()

# ----------------- MODELOS PARA LA API -----------------

class LoginRequest(BaseModel):
    user_name: str
    password: str

class UserCreate(BaseModel):
    user_name: str
    is_influencer: bool
    email: str
    password: str
    age: int
    profile_pic: str

class RelationCreate(BaseModel):
    id1: int
    id2: int

class RelationSIGUEA(BaseModel):
    id1: int
    id2: int
    notificaciones_activas: bool = True
    recomendado_por_algoritmo: bool = False

class MensajeCreate(BaseModel):
    id_mensaje: int
    texto: str
    fecha_envio: date
    estado: str
    adjunto: str = None

class GrupoCreate(BaseModel):
    id_grupo: int
    nombre: str
    fecha_creacion: date
    miembros: list
    descripcion: str
    foto_grupo: str

class RelationEscribioMensaje(BaseModel):
    id_usuario: int
    id_mensaje: int
    escrito_a_las: date
    enviado: bool
    editado: bool

class GrupoPublicacionRelation(BaseModel):
    id_grupo: int
    id_publicacion: int
    fecha_agregado: date
    agregado_por: int
    categoria: str
    relevancia: float

class RelationFueEnviadoA(BaseModel):
    id_mensaje: int
    id_usuario: int
    fecha_envio: date
    leido: bool
    fecha_de_lectura: date = None

class RelationEsIntegranteDe(BaseModel):
    id_usuario: int
    id_grupo: int
    fecha_de_ingreso: date
    rol: str
    silenciado: bool

class PublicacionCreate(BaseModel):
    id_publicacion: int
    texto: str
    fecha: date
    reacciones: int

class ComentarioCreate(BaseModel):
    id_comentario: int
    titulo: str
    contenido: str
    fecha: date
    likes: int

class RelationComparte(BaseModel):
    id_usuario: int
    id_publicacion: int
    fecha_compartido: date = date.today()

class RelationComenta(BaseModel):
    id_usuario: int
    id_comentario: int
    fecha_comentario: date = date.today()

class RelationPerteneceA(BaseModel):
    id_comentario: int
    id_publicacion: int


# ----------------- FUNCIONES PARA NEO4J -----------------
def create_relation_contiene_publicacion(tx, id_grupo, id_publicacion, fecha_agregado, agregado_por, categoria, relevancia):
    """Crea una relación CONTIENE_PUBLICACION entre Grupo y Publicación"""
    query = """
    MATCH (g:Grupo {id_grupo: $id_grupo}), (p:Publicacion {id_publicacion: $id_publicacion})
    MERGE (g)-[r:CONTIENE_PUBLICACION]->(p)
    SET r.fecha_agregado = $fecha_agregado,
        r.agregado_por = $agregado_por,
        r.categoria = $categoria,
        r.relevancia = $relevancia
    RETURN g, p, r
    """
    tx.run(query, id_grupo=id_grupo, id_publicacion=id_publicacion, fecha_agregado=fecha_agregado, agregado_por=agregado_por, categoria=categoria, relevancia=relevancia)

def check_user(tx, user_name, password):
    query = """
    MATCH (u:Usuario {user_name: $user_name, pass: $password})
    RETURN u.id_usuario AS id_usuario, u.user_name AS user_name
    """
    result = tx.run(query, user_name=user_name, password=password).single()
    return result if result else None

@app.post("/login/")
def login(user: LoginRequest):
    with driver.session(database="neo4j") as session:
        user_found = session.execute_read(check_user, user.user_name, user.password)
        if user_found:
            return {
                "message": "Login exitoso",
                "id_usuario": user_found["id_usuario"],
                "user_name": user_found["user_name"]
            }
        else:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")


@app.get("/follows/{user_name}")
def get_following(user_name: str):
    query = """
    MATCH (u:Usuario {user_name: $user_name})-[:SIGUE_A]->(seguido)
    RETURN seguido.user_name AS user_name, seguido.foto_de_perfil AS foto
    """
    with driver.session(database="neo4j") as session:
        results = session.run(query, user_name=user_name)
        following = [{"user_name": record["user_name"], "foto": record["foto"]} for record in results]

    if not following:
        return {"message": "No sigues a nadie."}
    
    return following

@app.get("/recommendations/{user_name}")
def get_recommendations(user_name: str):
    with driver.session(database="neo4j") as session:
        # Verificar si el usuario sigue a alguien
        query_following = """
        MATCH (u:Usuario {user_name: $user_name})-[:SIGUE_A]->(s:Usuario)
        RETURN s.id_usuario AS id_usuario
        """
        following_users = [record["id_usuario"] for record in session.run(query_following, user_name=user_name)]

        if following_users:
            # Buscar usuarios seguidos por las personas que sigo (pero que yo no sigo aún)
            query = """
            MATCH (me:Usuario {user_name: $user_name})-[:SIGUE_A]->(s:Usuario)-[:SIGUE_A]->(rec:Usuario)
            WHERE NOT (me)-[:SIGUE_A]->(rec) AND rec <> me
            RETURN DISTINCT rec.user_name AS user_name, rec.foto_de_perfil AS foto, rec.id_usuario AS id_usuario
            LIMIT 5
            """
        else:
            # Si no sigue a nadie, mostrar recomendaciones aleatorias
            query = """
            MATCH (rec:Usuario) WHERE rec.user_name <> $user_name
            RETURN rec.user_name AS user_name, rec.foto_de_perfil AS foto, rec.id_usuario AS id_usuario
            ORDER BY rand() LIMIT 5
            """

        results = session.run(query, user_name=user_name)
        recommendations = [{"user_name": record["user_name"], "foto": record["foto"], "id_usuario": record["id_usuario"]} for record in results]

        return recommendations if recommendations else {"message": "No hay recomendaciones disponibles."}


# Users
def create_user(tx, id_usuario, user_name, email, password, is_influencer, age, profile_pic):
    verificado = random.random() < (0.5 if is_influencer else 0.2)
    
    query = f"""
    CREATE (u:Usuario{":Influencer" if is_influencer else ""} {{
        id_usuario: {id_usuario},
        correo: "{email}",
        edad: {age},
        fecha_registro: date("{date.today()}"),
        foto_de_perfil: "{profile_pic}",
        user_name: "{user_name}",
        verificado: {verificado},
        pass: "{password}"
    }})
    RETURN u
    """
    tx.run(query)

def get_all_users(tx):
    query = "MATCH (u:Usuario) RETURN u.id_usuario AS id, u.user_name AS user_name, labels(u) AS labels"
    return tx.run(query).data()

def get_user(tx, user_id: int):
    query = """
    MATCH (u:Usuario {id_usuario: $user_id})
    RETURN u
    """
    result = tx.run(query, user_id=user_id).data()
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result[0]

def add_user_properties(tx, user_id: int, properties: dict):
    query = """
    MATCH (u:Usuario {id_usuario: $user_id})
    SET u += $properties
    RETURN u
    """
    tx.run(query, user_id=user_id, properties=properties)

def update_user_properties(tx, user_id: int, properties: dict):
    query = """
    MATCH (u:Usuario {id_usuario: $user_id})
    SET u += $properties
    RETURN u
    """
    tx.run(query, user_id=user_id, properties=properties)

def delete_user(tx, user_id: int):
    query = "MATCH (u:Usuario {id: $user_id}) DETACH DELETE u"
    tx.run(query, user_id=user_id)

def delete_all_users(tx):
    query = "MATCH (u:Usuario) DETACH DELETE u"
    tx.run(query)


def create_relation_sigue_a(tx, id1, id2, notificaciones_activas=False, recomendado_por_algoritmo=False):
    query = """
    MATCH (u1:Usuario {id_usuario: $id1}), (u2:Usuario {id_usuario: $id2})
    MERGE (u1)-[:SIGUE_A {fecha_inicio: date(), notificaciones_activas: $notificaciones_activas, recomendado_por_algoritmo: $recomendado_por_algoritmo}]->(u2)
    RETURN u1, u2
    """
    tx.run(query, id1=id1, id2=id2, notificaciones_activas=notificaciones_activas, recomendado_por_algoritmo=recomendado_por_algoritmo)

def create_relation_bloquea(tx, id1, id2):
    query = """
    MATCH (u1:Usuario {id_usuario: $id1}), (u2:Usuario {id_usuario: $id2})
    MERGE (u1)-[:BLOQUEA {fecha_bloqueo: date()}]->(u2)
    RETURN u1, u2
    """
    tx.run(query, id1=id1, id2=id2)

def create_mensaje(tx, id_mensaje, texto, fecha_envio, estado, adjunto):
    query = """
    CREATE (m:Mensaje {
        id_mensaje: $id_mensaje,
        texto: $texto,
        fecha_envio: $fecha_envio,
        estado: $estado,
        adjunto: $adjunto
    })
    RETURN m
    """
    tx.run(query, id_mensaje=id_mensaje, texto=texto, fecha_envio=fecha_envio, estado=estado, adjunto=adjunto)

def get_all_mensajes(tx):
    query = "MATCH (m:Mensaje) RETURN m.id_mensaje AS id_mensaje, m.texto AS texto, m.fecha_envio AS fecha_envio, m.estado AS estado, m.adjunto AS adjunto"
    return tx.run(query).data()

def get_message(tx, message_id: int):
    query = """
    MATCH (m:Mensaje {id_mensaje: $message_id})
    RETURN m
    """
    result = tx.run(query, message_id=message_id).data()
    if not result:
        raise HTTPException(status_code=404, detail="Message not found")
    return result[0]

def add_message_properties(tx, message_id: int, properties: dict):
    query = """
    MATCH (m:Mensaje {id_mensaje: $message_id})
    SET m += $properties
    RETURN m
    """
    tx.run(query, message_id=message_id, properties=properties)

def update_message_properties(tx, message_id: int, properties: dict):
    query = """
    MATCH (m:Mensaje {id_mensaje: $message_id})
    SET m += $properties
    RETURN m
    """
    tx.run(query, message_id=message_id, properties=properties)

def delete_message(tx, message_id: int):
    query = "MATCH (m:Mensaje {id_mensaje: $message_id}) DETACH DELETE m"
    tx.run(query, message_id=message_id)

def delete_all_messages(tx):
    query = "MATCH (m:Mensaje) DETACH DELETE m"
    tx.run(query)


def create_grupo(tx, id_grupo, nombre, fecha_creacion, miembros, descripcion, foto_grupo):
    query = """
    CREATE (g:Grupo {
        id_grupo: $id_grupo,
        nombre: $nombre,
        fecha_creacion: $fecha_creacion,
        miembros: $miembros,
        descripcion: $descripcion,
        foto_grupo: $foto_grupo
    })
    RETURN g
    """
    tx.run(query, id_grupo=id_grupo, nombre=nombre, fecha_creacion=fecha_creacion, miembros=miembros, descripcion=descripcion, foto_grupo=foto_grupo)

def get_all_grupos(tx):
    query = "MATCH (g:Grupo) RETURN g.id_grupo AS id_grupo, g.nombre AS nombre, g.fecha_creacion AS fecha_creacion, g.descripcion AS descripcion, g.foto_grupo AS foto_grupo"
    return tx.run(query).data()

def get_group(tx, group_id: int):
    query = """
    MATCH (g:Grupo {id_grupo: $group_id})
    RETURN g
    """
    result = tx.run(query, group_id=group_id).data()
    if not result:
        raise HTTPException(status_code=404, detail="Group not found")
    return result[0]

def add_group_properties(tx, group_id: int, properties: dict):
    query = """
    MATCH (g:Grupo {id_grupo: $group_id})
    SET g += $properties
    RETURN g
    """
    tx.run(query, group_id=group_id, properties=properties)

def update_group_properties(tx, group_id: int, properties: dict):
    query = """
    MATCH (g:Grupo {id_grupo: $group_id})
    SET g += $properties
    RETURN g
    """
    tx.run(query, group_id=group_id, properties=properties)

def delete_group(tx, group_id: int):
    query = "MATCH (g:Grupo {id_grupo: $group_id}) DETACH DELETE g"
    tx.run(query, group_id=group_id)

def delete_all_groups(tx):
    query = "MATCH (g:Grupo) DETACH DELETE g"
    tx.run(query)


def create_relation_escribio_mensaje(tx, id_usuario, id_mensaje, escrito_a_las, enviado, editado):
    query = """
    MATCH (u:Usuario {id_usuario: $id_usuario}), (m:Mensaje {id_mensaje: $id_mensaje})
    MERGE (u)-[:ESCRIBIO_MENSAJE {escrito_a_las: $escrito_a_las, enviado: $enviado, editado: $editado}]->(m)
    RETURN u, m
    """
    tx.run(query, id_usuario=id_usuario, id_mensaje=id_mensaje, escrito_a_las=escrito_a_las, enviado=enviado, editado=editado)

def create_relation_fue_enviado_a(tx, id_mensaje, id_usuario, fecha_envio, leido, fecha_de_lectura):
    query = """
    MATCH (m:Mensaje {id_mensaje: $id_mensaje}), (u:Usuario {id_usuario: $id_usuario})
    MERGE (m)-[:FUE_ENVIADO_A {fecha_envio: $fecha_envio, leido: $leido, fecha_de_lectura: $fecha_de_lectura}]->(u)
    RETURN m, u
    """
    tx.run(query, id_mensaje=id_mensaje, id_usuario=id_usuario, fecha_envio=fecha_envio, leido=leido, fecha_de_lectura=fecha_de_lectura)

def create_relation_es_integrante_de(tx, id_usuario, id_grupo, fecha_de_ingreso, rol, silenciado):
    query = """
    MATCH (u:Usuario {id_usuario: $id_usuario}), (g:Grupo {id_grupo: $id_grupo})
    MERGE (u)-[:ES_INTEGRANTE_DE {fecha_de_ingreso: $fecha_de_ingreso, rol: $rol, silenciado: $silenciado}]->(g)
    RETURN u, g
    """
    tx.run(query, id_usuario=id_usuario, id_grupo=id_grupo, fecha_de_ingreso=fecha_de_ingreso, rol=rol, silenciado=silenciado)

def create_publicacion_func(tx, id_publicacion, texto, fecha, reacciones):
    query = """
    CREATE (p:Publicacion {
        id_publicacion: $id_publicacion,
        texto: $texto,
        fecha: $fecha,
        reacciones: $reacciones
    })
    RETURN p
    """
    tx.run(query,
           id_publicacion=id_publicacion,
           texto=texto,
           fecha=fecha,
           reacciones=reacciones)

def get_publication(tx, publication_id: int):
    query = """
    MATCH (p:Publicacion {id_publicacion: $publication_id})
    RETURN p
    """
    result = tx.run(query, publication_id=publication_id).data()
    if not result:
        raise HTTPException(status_code=404, detail="Publication not found")
    return result[0]

def add_publication_properties(tx, publication_id: int, properties: dict):
    query = """
    MATCH (p:Publicacion {id_publicacion: $publication_id})
    SET p += $properties
    RETURN p
    """
    tx.run(query, publication_id=publication_id, properties=properties)

def update_publication_properties(tx, publication_id: int, properties: dict):
    query = """
    MATCH (p:Publicacion {id_publicacion: $publication_id})
    SET p += $properties
    RETURN p
    """
    tx.run(query, publication_id=publication_id, properties=properties)

def delete_publication(tx, publication_id: int):
    query = "MATCH (p:Publicacion {id_publicacion: $publication_id}) DETACH DELETE p"
    tx.run(query, publication_id=publication_id)

def delete_all_publications(tx):
    query = "MATCH (p:Publicacion) DETACH DELETE p"
    tx.run(query)


def create_comentario_func(tx, id_comentario, titulo, contenido, fecha, likes):
    query = """
    CREATE (c:Comentario {
        id_comentario: $id_comentario,
        titulo: $titulo,
        contenido: $contenido,
        fecha: $fecha,
        likes: $likes
    })
    RETURN c
    """
    tx.run(query,
           id_comentario=id_comentario,
           titulo=titulo,
           contenido=contenido,
           fecha=fecha,
           likes=likes)

def get_comment(tx, id_comentario: int):
    query = """
    MATCH (c:Comentario {id_comentario: $id_comentario})
    RETURN c
    """
    result = tx.run(query, id_comentario=id_comentario).data()
    if not result:
        raise HTTPException(status_code=404, detail="Comment not found")
    return result[0]

def add_comment_properties(tx, id_comentario: int, properties: dict):
    query = """
    MATCH (c:Comentario {id_comentario: $id_comentario})
    SET c += $properties
    RETURN c
    """
    tx.run(query, id_comentario=id_comentario, properties=properties)

def update_comment_properties(tx, id_comentario: int, properties: dict):
    query = """
    MATCH (c:Comentario {id_comentario: $id_comentario})
    SET c += $properties
    RETURN c
    """
    tx.run(query, id_comentario=id_comentario, properties=properties)

def delete_comment(tx, id_comentario: int):
    query = "MATCH (c:Comentario {id_comentario: $id_comentario}) DETACH DELETE c"
    tx.run(query, id_comentario=id_comentario)

def delete_all_comments(tx):
    query = "MATCH (c:Comentario) DETACH DELETE c"
    tx.run(query)


def create_relation_comparte(tx, id_usuario, id_publicacion, fecha_compartido):
    query = """
    MATCH (u:Usuario {id_usuario: $id_usuario}), (p:Publicacion {id_publicacion: $id_publicacion})
    MERGE (u)-[:COMPARTE {
        fecha_compartido: $fecha_compartido
    }]->(p)
    RETURN u, p
    """
    tx.run(query, 
           id_usuario=id_usuario,
           id_publicacion=id_publicacion,
           fecha_compartido=fecha_compartido)

def create_relation_comenta(tx, id_usuario, id_comentario, fecha_comentario):
    query = """
    MATCH (u:Usuario {id_usuario: $id_usuario}), (c:Comentario {id_comentario: $id_comentario})
    MERGE (u)-[:COMENTA {
        fecha_comentario: $fecha_comentario
    }]->(c)
    RETURN u, c
    """
    tx.run(query, 
           id_usuario=id_usuario,
           id_comentario=id_comentario,
           fecha_comentario=fecha_comentario)

def get_relation_comenta(tx, relation_id: int):
    query = """
    MATCH ()-[r:COMENTA]->() WHERE id(r) = $relation_id
    RETURN r
    """
    result = tx.run(query, relation_id=relation_id).data()
    if not result:
        raise HTTPException(status_code=404, detail="RelationComenta not found")
    return result[0]

def add_relation_comenta_properties(tx, relation_id: int, properties: dict):
    query = """
    MATCH ()-[r:COMENTA]->() WHERE id(r) = $relation_id
    SET r += $properties
    RETURN r
    """
    tx.run(query, relation_id=relation_id, properties=properties)

def update_relation_comenta_properties(tx, relation_id: int, properties: dict):
    query = """
    MATCH ()-[r:COMENTA]->() WHERE id(r) = $relation_id
    SET r += $properties
    RETURN r
    """
    tx.run(query, relation_id=relation_id, properties=properties)

def create_relation_pertenece_a(tx, id_comentario, id_publicacion):
    query = """
    MATCH (c:Comentario {id_comentario: $id_comentario}), (p:Publicacion {id_publicacion: $id_publicacion})
    MERGE (c)-[:PERTENECE_A]->(p)
    RETURN c, p
    """
    tx.run(query, 
           id_comentario=id_comentario,
           id_publicacion=id_publicacion)

# ----------------- ENDPOINTS -----------------

@app.post("/users/")
def create_user_api(user: UserCreate):
    with driver.session(database="neo4j") as session:
        user_id = random.randint(1, 1000)  # Asignar un ID único
        session.execute_write(create_user, user_id, user.user_name, user.is_influencer)
        return {"message": "Usuario creado", "id_usuario": user_id}

@app.post("/signup/")
def signup(user: UserCreate):
    with driver.session(database="neo4j") as session:
        # Obtener el último ID de usuario registrado
        result = session.run("MATCH (u:Usuario) RETURN COALESCE(MAX(u.id_usuario), 0) AS last_id")
        last_id = result.single()["last_id"]
        user_id = last_id + 1

        # Crear usuario en la base de datos
        session.execute_write(create_user, user_id, user.user_name, user.email, user.password, user.is_influencer, user.age, user.profile_pic)
        
        return {"message": "Usuario creado exitosamente", "id_usuario": user_id}

@app.get("/users/")
def get_users():
    with driver.session(database="neo4j") as session:
        users = session.execute_read(get_all_users)
        return users
    
@app.get("/users/{user_id}")
def get_user_api(user_id: int):
    with driver.session(database="neo4j") as session:
        user = session.execute_read(get_user, user_id)
        return user if user else {"message": "User not found"}
    
@app.post("/users/{user_id}/add_properties")
def add_user_properties_api(user_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(add_user_properties, user_id, properties)
        return {"message": f"Properties added to user {user_id}", "properties": properties}
    
@app.put("/users/{user_id}/update_properties")
def update_user_properties_api(user_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(update_user_properties, user_id, properties)
        return {"message": f"Properties updated for user {user_id}", "properties": properties}

@app.delete("/users/{user_id}")
def delete_user_api(user_id: int):
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_user, user_id)
        return {"message": f"User {user_id} deleted"}

@app.delete("/users")
def delete_all_users_api():
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_all_users)
        return {"message": "All users deleted"}


@app.post("/relations/sigue_a/")
def follow_user(relation: RelationSIGUEA):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_relation_sigue_a,
            relation.id1,
            relation.id2,
            relation.notificaciones_activas,
            relation.recomendado_por_algoritmo
        )
        return {"message": f"Usuario {relation.id1} ahora sigue a {relation.id2}", 
                "notificaciones_activas": relation.notificaciones_activas,
                "recomendado_por_algoritmo": relation.recomendado_por_algoritmo}

@app.post("/relations/bloquea/")
def block_user(relation: RelationCreate):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_relation_bloquea, relation.id1, relation.id2)
        return {"message": f"Usuario {relation.id1} bloqueó a {relation.id2}"}
    
@app.get("/mensajes/")
def get_mensajes():
    with driver.session(database="neo4j") as session:
        mensajes = session.execute_read(get_all_mensajes)
        return mensajes if mensajes else {"message": "No hay mensajes disponibles."}
    
@app.get("/mensajes/{message_id}")
def get_message_api(message_id: int):
    with driver.session(database="neo4j") as session:
        message = session.execute_read(get_message, message_id)
        return message if message else {"message": "Message not found"}

@app.post("/mensajes/{message_id}/add_properties")
def add_message_properties_api(message_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(add_message_properties, message_id, properties)
        return {"message": f"Properties added to message {message_id}", "properties": properties}

@app.put("/mensajes/{message_id}/update_properties")
def update_message_properties_api(message_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(update_message_properties, message_id, properties)
        return {"message": f"Properties updated for message {message_id}", "properties": properties}

@app.delete("/messages/{message_id}")
def delete_message_api(message_id: int):
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_message, message_id)
        return {"message": f"Message {message_id} deleted"}

@app.delete("/messages")
def delete_all_messages_api():
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_all_messages)
        return {"message": "All messages deleted"}


@app.post("/mensajes/")
def create_mensaje_api(mensaje: MensajeCreate):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_mensaje, mensaje.id_mensaje, mensaje.texto, mensaje.fecha_envio, mensaje.estado, mensaje.adjunto)
        return {"message": "Mensaje creado", "id_mensaje": mensaje.id_mensaje}

@app.post("/grupos/")
def create_grupo_api(grupo: GrupoCreate):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_grupo, grupo.id_grupo, grupo.nombre, grupo.fecha_creacion, grupo.miembros, grupo.descripcion, grupo.foto_grupo)
        return {"message": "Grupo creado", "id_grupo": grupo.id_grupo}
    
@app.get("/grupos/")
def get_grupos():
    with driver.session(database="neo4j") as session:
        grupos = session.execute_read(get_all_grupos)
        return grupos if grupos else {"message": "No hay grupos disponibles."}

@app.get("/grupos/{group_id}")
def get_group_api(group_id: int):
    with driver.session(database="neo4j") as session:
        group = session.execute_read(get_group, group_id)
        return group if group else {"message": "Group not found"}

@app.post("/grupos/{group_id}/add_properties")
def add_group_properties_api(group_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(add_group_properties, group_id, properties)
        return {"message": f"Properties added to group {group_id}", "properties": properties}

@app.put("/grupos/{group_id}/update_properties")
def update_group_properties_api(group_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(update_group_properties, group_id, properties)
        return {"message": f"Properties updated for group {group_id}", "properties": properties}

@app.delete("/groups/{group_id}")
def delete_group_api(group_id: int):
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_group, group_id)
        return {"message": f"Group {group_id} deleted"}

@app.delete("/groups")
def delete_all_groups_api():
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_all_groups)
        return {"message": "All groups deleted"}


@app.post("/relations/escribio_mensaje/")
def escribio_mensaje(relation: RelationEscribioMensaje):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_relation_escribio_mensaje, relation.id_usuario, relation.id_mensaje, relation.escrito_a_las, relation.enviado, relation.editado)
        return {"message": f"Usuario {relation.id_usuario} escribió el mensaje {relation.id_mensaje}"}

@app.post("/relations/fue_enviado_a/")
def fue_enviado_a(relation: RelationFueEnviadoA):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_relation_fue_enviado_a, relation.id_mensaje, relation.id_usuario, relation.fecha_envio, relation.leido, relation.fecha_de_lectura)
        return {"message": f"Mensaje {relation.id_mensaje} fue enviado a usuario {relation.id_usuario}"}

@app.post("/relations/es_integrante_de/")
def es_integrante_de(relation: RelationEsIntegranteDe):
    with driver.session(database="neo4j") as session:
        session.execute_write(create_relation_es_integrante_de, relation.id_usuario, relation.id_grupo, relation.fecha_de_ingreso, relation.rol, relation.silenciado)
        return {"message": f"Usuario {relation.id_usuario} se unió al grupo {relation.id_grupo} como {relation.rol}"}

@app.get("/search_user/{user_name}")
def search_user(user_name: str):
    with driver.session(database="neo4j") as session:
        query = """
        MATCH (u:Usuario)
        WHERE toLower(u.user_name) CONTAINS toLower($user_name)
        RETURN u.user_name AS user_name, u.foto_de_perfil AS foto, u.id_usuario AS id_usuario
        """
        results = session.run(query, user_name=user_name)
        users = [{"user_name": record["user_name"], "foto": record["foto"], "id_usuario": record["id_usuario"]} for record in results]

        return users if users else {"message": "No se encontraron usuarios."}

@app.get("/feed/{id_usuario}")
def get_feed(id_usuario: int):
    with driver.session(database="neo4j") as session:
        query = """
        MATCH (u:Usuario {id_usuario: $id_usuario})-[:SIGUE_A]->(seguido:Usuario)
        OPTIONAL MATCH (seguido)-[pub:PUBLICA]->(p:Publicacion)
        OPTIONAL MATCH (seguido)-[comp:COMPARTE]->(p)
        WITH seguido, p, 
             COLLECT(DISTINCT pub)[0] AS pub_rel, 
             COLLECT(DISTINCT comp)[0] AS comp_rel
        WITH seguido, p, pub_rel, comp_rel, toString(p.fecha) AS fecha
        ORDER BY fecha DESC
        RETURN DISTINCT 
               p.id_publicacion AS id_publicacion, 
               p.texto AS texto, 
               fecha,
               p.reacciones AS reacciones,
               seguido.user_name AS autor,
               CASE 
                   WHEN pub_rel IS NOT NULL THEN 'PUBLICA' 
                   ELSE 'COMPARTE' 
               END AS tipo
        """
        results = session.run(query, id_usuario=id_usuario)
        publicaciones = [
            {
                "id_publicacion": record["id_publicacion"],
                "texto": record["texto"],
                "fecha": record["fecha"],
                "reacciones": record["reacciones"],
                "autor": record["autor"],
                "tipo": record["tipo"]
            }
            for record in results
        ]

        return publicaciones if publicaciones else {"message": "No hay publicaciones de personas que sigues."}



@app.post("/like_post/{id_publicacion}")
def like_post(id_publicacion: int):
    with driver.session(database="neo4j") as session:
        # Actualizar reacciones en Neo4j
        query = """
        MATCH (p:Publicacion {id_publicacion: $id_publicacion})
        SET p.reacciones = COALESCE(p.reacciones, 0) + 1
        RETURN p.reacciones AS nuevas_reacciones
        """
        result = session.run(query, id_publicacion=id_publicacion).single()
        
        if result:
            return {"message": "Reacción añadida", "nuevas_reacciones": result["nuevas_reacciones"]}
        else:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        


@app.post("/publicaciones/")
def create_publicacion_api(pub: PublicacionCreate):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_publicacion_func,
            pub.id_publicacion,
            pub.texto,
            pub.fecha,
            pub.reacciones
        )
        return {"message": "Publicación creada", "id_publicacion": pub.id_publicacion}
    
@app.get("/publicaciones/{publication_id}")
def get_publication_api(publication_id: int):
    with driver.session(database="neo4j") as session:
        publication = session.execute_read(get_publication, publication_id)
        return publication if publication else {"message": "Publication not found"}
    
@app.post("/publicaciones/{publication_id}/add_properties")
def add_publication_properties_api(publication_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(add_publication_properties, publication_id, properties)
        return {"message": f"Properties added to publication {publication_id}", "properties": properties}
    
@app.put("/publicaciones/{publication_id}/update_properties")
def update_publication_properties_api(publication_id: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(update_publication_properties, publication_id, properties)
        return {"message": f"Properties updated for publication {publication_id}", "properties": properties}

@app.delete("/publicaciones/{publication_id}")
def delete_publication_api(publication_id: int):
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_publication, publication_id)
        return {"message": f"Publication {publication_id} deleted"}

@app.delete("/publicaciones")
def delete_all_publications_api():
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_all_publications)
        return {"message": "All publications deleted"}


@app.post("/comentarios/")
def create_comentario_api(comment: ComentarioCreate):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_comentario_func,
            comment.id_comentario,
            comment.titulo,
            comment.contenido,
            comment.fecha,
            comment.likes
        )
        return {"message": "Comentario creado", "id_comentario": comment.id_comentario}
    
@app.get("/comentarios/{id_comentario}")
def get_comment_api(id_comentario: int):
    with driver.session(database="neo4j") as session:
        comment = session.execute_read(get_comment, id_comentario)
        return comment if comment else {"message": "Comment not found"}
    
@app.post("/comentarios/{id_comentario}/add_properties")
def add_comment_properties_api(id_comentario: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(add_comment_properties, id_comentario, properties)
        return {"message": f"Properties added to comment {id_comentario}", "properties": properties}
    
@app.put("/comentarios/{id_comentario}/update_properties")
def update_comment_properties_api(id_comentario: int, properties: dict):
    with driver.session(database="neo4j") as session:
        session.execute_write(update_comment_properties, id_comentario, properties)
        return {"message": f"Properties updated for comment {id_comentario}", "properties": properties}

@app.delete("/comments/{id_comentario}")
def delete_comment_api(id_comentario: int):
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_comment, id_comentario)
        return {"message": f"Comment {id_comentario} deleted"}

@app.delete("/comments")
def delete_all_comments_api():
    with driver.session(database="neo4j") as session:
        session.execute_write(delete_all_comments)
        return {"message": "All comments deleted"}


@app.post("/relations/contiene_publicacion/")
def create_contiene_publicacion_api(rel: GrupoPublicacionRelation):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_relation_contiene_publicacion,
            rel.id_grupo,
            rel.id_publicacion,
            rel.fecha_agregado,
            rel.agregado_por,
            rel.categoria,
            rel.relevancia
        )
        return {"message": f"Grupo {rel.id_grupo} ahora contiene la publicación {rel.id_publicacion}"}

@app.post("/relations/comparte/")
def create_comparte_api(rel: RelationComparte):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_relation_comparte,
            rel.id_usuario,
            rel.id_publicacion,
            rel.fecha_compartido
        )
        return {"message": f"Usuario {rel.id_usuario} compartió la publicación {rel.id_publicacion}"}
    
@app.post("/relations/comenta/")
def create_comenta_api(rel: RelationComenta):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_relation_comenta,
            rel.id_usuario,
            rel.id_comentario,
            rel.fecha_comentario
        )
        return {"message": f"Usuario {rel.id_usuario} comentó el comentario {rel.id_comentario}"}

@app.post("/relations/pertenece_a/")
def create_pertenece_a_api(rel: RelationPerteneceA):
    with driver.session(database="neo4j") as session:
        session.execute_write(
            create_relation_pertenece_a,
            rel.id_comentario,
            rel.id_publicacion
        )
        return {"message": f"Comentario {rel.id_comentario} pertenece a la publicación {rel.id_publicacion}"}
    
