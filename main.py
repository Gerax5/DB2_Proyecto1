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
    query = """
    MATCH (u:Usuario {user_name: $user_name})
    MATCH (sugerido:Usuario) WHERE NOT (u)-[:SIGUE_A]->(sugerido) AND sugerido <> u
    RETURN sugerido.user_name AS user_name, sugerido.foto_de_perfil AS foto, sugerido.id_usuario AS id_usuario
    LIMIT 5
    """
    with driver.session(database="neo4j") as session:
        results = session.run(query, user_name=user_name)
        recommendations = [{"user_name": record["user_name"], "foto": record["foto"], "id_usuario": record["id_usuario"]} for record in results]
    
    return recommendations if recommendations else {"message": "No hay recomendaciones disponibles."}


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

def get_all_mensajes(tx):
    query = "MATCH (m:Mensaje) RETURN m.id_mensaje AS id_mensaje, m.texto AS texto, m.fecha_envio AS fecha_envio, m.estado AS estado, m.adjunto AS adjunto"
    return tx.run(query).data()

def get_all_grupos(tx):
    query = "MATCH (g:Grupo) RETURN g.id_grupo AS id_grupo, g.nombre AS nombre, g.fecha_creacion AS fecha_creacion, g.descripcion AS descripcion, g.foto_grupo AS foto_grupo"
    return tx.run(query).data()

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
        user_id = random.randint(1, 1000)  # Asignar un ID único
        session.execute_write(create_user, user_id, user.user_name, user.email, user.password, user.is_influencer, user.age, user.profile_pic)
        return {"message": "Usuario creado exitosamente", "id_usuario": user_id}

@app.get("/users/")
def get_users():
    with driver.session(database="neo4j") as session:
        users = session.execute_read(get_all_users)
        return users

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

@app.get("/grupos/")
def get_grupos():
    with driver.session(database="neo4j") as session:
        grupos = session.execute_read(get_all_grupos)
        return grupos if grupos else {"message": "No hay grupos disponibles."}

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