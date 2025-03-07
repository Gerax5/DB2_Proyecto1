import random
import pandas as pd
import csv
from neo4j import GraphDatabase
from datetime import date, timedelta
from neo4j import GraphDatabase
from faker import Faker
import datetime

fake = Faker()

URI = "neo4j+s://9b937ef7.databases.neo4j.io"
AUTH = ("neo4j", "bsHJmEb5iRs55WLgztwslEYYOSJaiFMvTXUnzuFvpvc")


def DELETE_DATABASE(tx):
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    tx.run(query)

def get_next_id(tx, label, id_field):
    query = f"""
    MATCH (n:{label})
    RETURN COALESCE(MAX(n.{id_field}), 0) + 1 AS next_id
    """
    result = tx.run(query).single()
    return result["next_id"]


def create_user(tx, id_usuario, userName, isInfluencer = False, edad = random.randint(18, 60), password="1234"):

    if isInfluencer:
        verificado = random.random() < 0.5
    else:
        verificado = random.random() < 0.2

    # next_id = get_next_id(tx, "Usuario", "id_usuario")

    query =  f"""
    CREATE (u:Usuario{":Influecer" if isInfluencer else ""}
      {{
        id_usuario: {id_usuario},
        correo: "correousuario{id_usuario}@gmail.com",
        edad: {edad},
        fecha_registro: date("{date.today() - timedelta(days=random.randint(1, 365))}"),
        foto_de_perfil: "https://thispersondoesnotexist.com/",
        user_name: "{userName}",
        verificado: {verificado},
        pass: "{password}"
      }}      
    )
    RETURN u
    """
    tx.run(query)

def create_mensaje(tx, id_mensaje, texto):
    # next_id = get_next_id(tx, "Mensaje", "id_mensaje")
    fecha_envio = f"date('{date.today() - timedelta(days=random.randint(1, 30))}')"
    estado = random.choice(["enviado", "entregado"])
    adjunto = "" if random.random() < 0.7 else "https://example.com/attachment.jpg"

    query = f"""
    CREATE (m:Mensaje {{
        id_mensaje: {id_mensaje},
        texto: "{texto}",
        fecha_envio: {fecha_envio},
        estado: "{estado}",
        adjunto: "{adjunto}"
    }})
    RETURN m
    """
    tx.run(query)


def create_grupo(tx, id_grupo, nombre):
    # next_id = get_next_id(tx, "Grupo", "id_grupo")
    fecha_creacion = f"date('{date.today() - timedelta(days=random.randint(1, 365))}')"
    descripcion = fake.sentence()
    foto_grupo = "https://example.com/group.jpg"

    query = f"""
    CREATE (g:Grupo {{
        id_grupo: {id_grupo},
        nombre: "{nombre}",
        fecha_creacion: {fecha_creacion},
        descripcion: "{descripcion}",
        foto_grupo: "{foto_grupo}"
    }})
    RETURN g
    """
    tx.run(query)


def create_comentario(tx, id_comentario, titulo, contenido, fecha, likes):
    query = f"""
    CREATE (c:Comentario {{
        id_comentario: {id_comentario},
        titulo: "{titulo}",
        contenido: "{contenido}",
        fecha: date("{fecha}"),
        likes: {likes}
    }})
    RETURN c
    """
    tx.run(query)


def create_publicacion(tx, id_publicacion, texto, fecha, reacciones):
    # next_id = get_next_id(tx, "Publicacion", "id_publicacion")
    query = f"""
    CREATE (p:Publicacion {{
        id_publicacion: {id_publicacion},
        texto: "{texto}",
        fecha: date("{fecha}"),
        reacciones: {reacciones}
    }})
    RETURN p
    """
    tx.run(query)


def create_relation_SIGUE_A(tx):
    # Obtener solo 200 usuarios aleatorios con sus etiquetas
    query = """
    MATCH (u:Usuario)

    WITH u ORDER BY rand() LIMIT 200
    RETURN u.id_usuario AS id_usuario, labels(u) AS labels
    """
    users = tx.run(query).data()
    
    relaciones = []  # Lista para almacenar las relaciones a crear

    for user in users:
        id_usuario = user["id_usuario"]
        labels = user["labels"]
        
        # Probabilidad de seguir a otro usuario
        probabilidad_seguir = 0.1 if "Influencer" in labels else 0.3

        # Seleccionar usuarios aleatorios a seguir
        posibles_seguidos = [u["id_usuario"] for u in users if u["id_usuario"] != id_usuario]
        seguidos = random.sample(posibles_seguidos, min(len(posibles_seguidos), int(len(posibles_seguidos) * probabilidad_seguir)))

        for seguido in seguidos:
            fecha_inicio = (date.today() - timedelta(days=random.randint(1, 365))).isoformat()
            notificaciones_activas = random.choice([True, False])
            recomendado_por_algoritmo = random.choice([True, False])

            relaciones.append({
                "id1": id_usuario,
                "id2": seguido,
                "fecha_inicio": fecha_inicio,
                "notificaciones_activas": notificaciones_activas,
                "recomendado_por_algoritmo": recomendado_por_algoritmo
            })

    # Crear todas las relaciones en un solo batch de consulta para mejorar el rendimiento
    query = """
    UNWIND $relaciones AS rel
    MATCH (u1:Usuario {id_usuario: rel.id1}), (u2:Usuario {id_usuario: rel.id2})
    MERGE (u1)-[:SIGUE_A {
        fecha_inicio: date(rel.fecha_inicio),
        notificaciones_activas: rel.notificaciones_activas,
        recomendado_por_algoritmo: rel.recomendado_por_algoritmo
    }]->(u2)
    """
    tx.run(query, relaciones=relaciones)


def create_relation_BLOQUEA(tx):
    # Obtener todos los usuarios
    query = """
    MATCH (u:Usuario)
    RETURN u.id_usuario AS id_usuario
    """
    users = tx.run(query).data()

    for user in users:
        id_usuario = user["id_usuario"]

        if random.random() < 0.05:
            posibles_bloqueados = [u["id_usuario"] for u in users if u["id_usuario"] != id_usuario]
            if posibles_bloqueados:
                bloqueado = random.choice(posibles_bloqueados)

                # Generar propiedades de la relación
                fecha_bloqueo = f"date('{date.today() - timedelta(days=random.randint(1, 365))}')"
                razones = ["Contenido ofensivo", "Acoso", "Spam", "Cuenta falsa", "Otra razón"]
                razon = random.choice(razones)
                tiempos_bloqueo = ["Temporal (7 días)", "Temporal (30 días)", "Permanente"]
                tiempo_bloqueo = random.choice(tiempos_bloqueo)  # Selecciona tiempo aleatorio

                query = f"""
                MATCH (u1:Usuario {{id_usuario: $id1}}), (u2:Usuario {{id_usuario: $id2}})
                
                MERGE (u1)-[:BLOQUEA {{
                    fecha_bloqueo: {fecha_bloqueo}, 
                    razon: "{razon}", 
                    tiempo_bloqueo: "{tiempo_bloqueo}"
                }}]->(u2)
            
                """
                tx.run(query, id1=id_usuario, id2=bloqueado)

                query_verificar_siguiendo = """
                    MATCH (u1:Usuario {id_usuario: $id1}), (u2:Usuario {id_usuario: $id2})
                    OPTIONAL MATCH (u1)-[s1:SIGUE_A]->(u2)
                    OPTIONAL MATCH (u2)-[s2:SIGUE_A]->(u1)
                    RETURN COUNT(s1) AS sigue_A_B, COUNT(s2) AS sigue_B_A
                """
    
                result = tx.run(query_verificar_siguiendo, id1=id_usuario, id2=bloqueado).single()

                if result and result["sigue_A_B"] > 0:
                    query_eliminar_sigue_A_B = """
                    MATCH (u1:Usuario {id_usuario: $id1})-[s:SIGUE_A]->(u2:Usuario {id_usuario: $id2})
                    DELETE s
                    """
                    tx.run(query_eliminar_sigue_A_B, id1=id_usuario, id2=bloqueado)

                if result and result["sigue_B_A"] > 0:
                    query_eliminar_sigue_B_A = """
                    MATCH (u2:Usuario {id_usuario: $id2})-[s:SIGUE_A]->(u1:Usuario {id_usuario: $id1})
                    DELETE s
                    """
                    tx.run(query_eliminar_sigue_B_A, id1=id_usuario, id2=bloqueado)


def create_relation_ESCRIBIO_MENSAJE(tx):
    query = """
    MATCH (m:Mensaje)  
    WITH m, rand() AS r  
    ORDER BY r  
    MATCH (u:Usuario)  
    WITH m, u, rand() AS r2  
    ORDER BY r2  
    WITH m, collect(u)[0] AS user  
    MERGE (user)-[:ESCRIBIO_MENSAJE {
        escrito_a_las: COALESCE(m.fecha_envio, date()),
        enviado: true,
        editado: rand() < 0.3
    }]->(m)
    """
    tx.run(query)



def create_relation_FUE_ENVIADO_A(tx):
    query = """
    MATCH (m:Mensaje)  
    WITH m, rand() AS r  
    ORDER BY r  
    MATCH (u:Usuario)  
    WITH m, u, rand() AS r2  
    ORDER BY r2  
    WITH m, collect(u)[0] AS user  
    MERGE (m)-[r:FUE_ENVIADO_A]->(user)  
    SET r.Fecha_envio = COALESCE(m.fecha_envio, date()),  
        r.Leido = rand() < 0.6  
    WITH r, rand() < 0.6 AS has_read  
    FOREACH (_ IN CASE WHEN has_read THEN [1] ELSE [] END |  
        SET r.fecha_de_lectura = COALESCE(r.Fecha_envio  , date())
    )
    """
    tx.run(query)

def create_relation_ES_INTEGRANTE_DE(tx):
    query = """
    MATCH (u:Usuario)  
    WITH u, rand() AS r  
    ORDER BY r  
    MATCH (g:Grupo)  
    WITH u, g, rand() AS r2  
    ORDER BY r2  
    WITH u, collect(g)[0] AS group  
    MERGE (u)-[:ES_INTEGRANTE_DE {
        Fecha_de_ingreso: date(),
        Rol: CASE WHEN rand() < 0.1 THEN "Admin" ELSE "Miembro" END,
        Silenciado: rand() < 0.3
    }]->(group)
    """
    tx.run(query)


def create_relation_COMPARTE(tx):
    query = """
    MATCH (p:Publicacion)  
    WITH p, rand() AS r  
    ORDER BY r  
    MATCH (u:Usuario)  
    WITH p, u, rand() AS r2  
    ORDER BY r2  
    WITH p, collect(u)[0] AS user  
    MERGE (user)-[:COMPARTE {
        fecha_compartido: date()
    }]->(p)
    """
    tx.run(query)


def create_relation_COMENTA(tx):
    query = """
    MATCH (c:Comentario)  
    WITH c, rand() AS r  
    ORDER BY r  
    MATCH (u:Usuario)  
    WITH c, u, rand() AS r2  
    ORDER BY r2  
    WITH c, collect(u)[0] AS user  
    MERGE (user)-[:COMENTA {
        fecha_comentario: date()
    }]->(c)
    """
    tx.run(query)


def create_relation_PERTENECE_A(tx):
    query = """
    MATCH (c:Comentario)  
    WITH c, rand() AS r  
    ORDER BY r  
    MATCH (p:Publicacion)  
    WITH c, p, rand() AS r2  
    ORDER BY r2  
    WITH c, collect(p)[0] AS post  
    MERGE (c)-[:PERTENECE_A]->(post)
    """
    tx.run(query)

def getAllUsers(tx):
    query = """
    MATCH (u:Usuario) RETURN u.user_name, u.id_usuario
    """
    result = tx.run(query)
    return [record.data() for record in result]

def create_relation_PUBLICA(tx, id_publicacion, id_user, fecha_de_publicacion, ubicacion, hashtags):
    query = """
    MATCH (u:Usuario), (p:Publicacion)
    WHERE u.id_usuario = $id_user AND p.id_publicacion = $id_publicacion
    MERGE (u)-[r:PUBLICA]->(p)
    SET r.fecha_de_publicacion = date($fecha_de_publicacion),
        r.ubicacion = $ubicacion,
        r.hashtags = $hashtags
    """
    tx.run(query, 
           id_user=id_user, 
           id_publicacion=id_publicacion, 
           fecha_de_publicacion=fecha_de_publicacion, 
           ubicacion=ubicacion, 
           hashtags=hashtags)

def create_random_data():
    def randomDate():
        start_date = datetime.date.today() - datetime.timedelta(days=5*365)
        random_days = random.randint(0, 5*365)
        return (start_date + datetime.timedelta(days=random_days)).isoformat()
    
    ubicaciones = ["Ciudad de México", "Nueva York", "Londres", "Tokio", "París", "Buenos Aires", "Berlín", "Madrid"]

    hashtags_posibles = ["#travel", "#food", "#nature", "#fitness", "#love", "#fashion", "#music", "#art", "#photography", "#sports"]

    hastags = random.sample(hashtags_posibles, random.randint(2, 5))
    fecha_de_publicacion = randomDate()
    ubicacion = random.choice(ubicaciones)

    return hastags, fecha_de_publicacion, ubicacion

  
def create_relation_CONTIENE_PUBLICACION(tx):
    def random_date():
        start_date = datetime.date.today() - datetime.timedelta(days=5*365)
        random_days = random.randint(0, 5*365)
        return (start_date + datetime.timedelta(days=random_days)).isoformat()

    categorias_posibles = ["anuncio", "evento", "noticia", "debate", "oferta"]
    # Obtener todos los grupos
    query_grupos = "MATCH (g:Grupo) RETURN g.id_grupo"
    grupos = [record["g.id_grupo"] for record in tx.run(query_grupos)]
    
    # Obtener todas las publicaciones
    query_publicaciones = "MATCH (p:Publicacion) RETURN p.id_publicacion"
    publicaciones = [record["p.id_publicacion"] for record in tx.run(query_publicaciones)]
    
    if not grupos or not publicaciones:
        print("No hay suficientes grupos o publicaciones en la base de datos.")
        return

    # Asignar publicaciones aleatorias a grupos
    for grupo_id in grupos:
        # Obtener los usuarios que son miembros del grupo
        query_usuarios_grupo = """
        MATCH (u:Usuario)-[:ES_INTEGRANTE_DE]->(g:Grupo)
        WHERE g.id_grupo = $grupo_id
        RETURN u.id_usuario
        """
        usuarios_grupo = [record["u.id_usuario"] for record in tx.run(query_usuarios_grupo, grupo_id=grupo_id)]
        
        if not usuarios_grupo:
            print(f"El grupo {grupo_id} no tiene integrantes, se omite.")
            continue  # Salta este grupo si no tiene integrantes

        # Elegir una publicación aleatoria
        publicacion_id = random.choice(publicaciones)
        
        # Elegir un usuario del grupo para ser el "agregado_por"
        agregado_por = random.choice(usuarios_grupo)

        # Generar datos aleatorios
        fecha_agregado = random_date()
        categoria = random.choice(categorias_posibles)
        relevancia = round(random.uniform(0.1, 1.0), 2)  # Valor entre 0.1 y 1.0

        # Crear relación en Neo4j
        query = """
        MATCH (g:Grupo), (p:Publicacion)
        WHERE g.id_grupo = $grupo_id AND p.id_publicacion = $publicacion_id
        MERGE (g)-[r:CONTIENE_PUBLICACION]->(p)
        SET r.fecha_agregado = date($fecha_agregado),
            r.agregado_por = $agregado_por,
            r.categoria = $categoria,
            r.relevancia = $relevancia
        """
        tx.run(query, 
               grupo_id=grupo_id, 
               publicacion_id=publicacion_id, 
               fecha_agregado=fecha_agregado, 
               agregado_por=agregado_por, 
               categoria=categoria, 
               relevancia=relevancia)


def upload_csv_to_neo4j(file_path, tx):
    import csv

    with open(file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["type"] == "node":
                query = f"""
                MERGE (n:{row['start_label']} {{id: $start_id}})
                SET n += $properties
                """
                properties = {k: v for k, v in row.items() if k not in ["type", "start_label", "start_id"]}
                tx.run(query, start_id=row["start_id"], properties=properties)

            elif row["type"] == "relationship":
                # Validate node labels to prevent syntax errors
                start_label = row["start_label"]
                end_label = row["end_label"]

                if not start_label.isidentifier() or not end_label.isidentifier():
                    raise ValueError(f"Invalid node label: {start_label}, {end_label}")

                query = f"""
                MATCH (a:{start_label} {{id: $start_id}}), (b:{end_label} {{id: $end_id}})
                MERGE (a)-[r:{row['relationship']}]->(b)
                SET r += $properties
                """
                properties = {k: v for k, v in row.items() if k not in ["type", "start_label", "start_id", "relationship", "end_label", "end_id"]}
                tx.run(query, start_id=row["start_id"], end_id=row["end_id"], properties=properties)


#Usage Example:
# file_path = "test.csv"
# driver = GraphDatabase.driver(URI, auth=AUTH)
# with driver.session(database="neo4j") as session:
#     session.execute_write(lambda tx: upload_csv_to_neo4j(file_path, tx))
# driver.close()



driver = GraphDatabase.driver(URI, auth=AUTH)

with driver.session(database="neo4j") as session:

    # Descomentar si se quiere borrar la base de datos
    # session.execute_write(DELETE_DATABASE)

    next_userID = session.execute_write(lambda tx: get_next_id(tx, "Usuario", "id_usuario"))
    next_mensajeID = session.execute_write(lambda tx: get_next_id(tx, "Mensaje", "id_mensaje"))
    next_grupoID = session.execute_write(lambda tx: get_next_id(tx, "Grupo", "id_grupo"))
    next_publicacionID = session.execute_write(lambda tx: get_next_id(tx, "Publicacion", "id_publicacion"))
    next_comentarioID = session.execute_write(lambda tx: get_next_id(tx, "Comentario", "id_comentario"))

    # print("ENTRANDO A CREAR USUARIO")
    # for i in range(1+next_userID, 200+next_userID):
    #     nombre = fake.name()
    #     isInfluencer = random.random() < 0.3
    #     session.execute_write(lambda tx: create_user(tx, i, nombre.replace(" ", ""), isInfluencer))

    users = session.execute_write(getAllUsers)


    print("ENTRANDO A CREAR RELACIONES")
    # session.execute_write(create_relation_SIGUE_A)
    session.execute_write(create_relation_BLOQUEA)

    print("ENTRANDO A MENSAJES")
    for i in range(1+next_mensajeID, 150+next_mensajeID):
        texto = fake.sentence()
        session.execute_write(lambda tx: create_mensaje(tx, i, texto))

    print("ENTRANDO A GRUPO")
    for i in range(1+next_grupoID, 20+next_grupoID):
        nombre = fake.company()
        session.execute_write(lambda tx: create_grupo(tx, i, nombre))

    print("ENTRANDO A OTRAS RELACIONES")
    session.execute_write(create_relation_ESCRIBIO_MENSAJE)
    session.execute_write(create_relation_FUE_ENVIADO_A)
    session.execute_write(create_relation_ES_INTEGRANTE_DE)

    # Creación de Publicaciones y Comentarios
    print("ENTRANDO A OTRAS PUBLICACIONES y PUBLICA")
    for i in range(1+next_publicacionID, 150+next_publicacionID):
        texto_publicacion = fake.sentence()
        fecha_publicacion = date.today() - timedelta(days=random.randint(1, 30))
        reacciones = random.randint(0, 100)
        session.execute_write(
            lambda tx: create_publicacion(tx, i, texto_publicacion, fecha_publicacion, reacciones)
        )

        hastags, fecha_de_publicacion, ubicacion = create_random_data()

        session.execute_write(
            lambda tx: create_relation_PUBLICA(tx, i, random.choice(users)["u.id_usuario"], fecha_de_publicacion, ubicacion, hastags)
        )


    

    print("ENTRANDO A OTRAS COMENTARIOS")
    for i in range(1+next_comentarioID, 20+next_comentarioID):
        titulo_comentario = fake.sentence(nb_words=3)
        contenido_comentario = fake.paragraph(nb_sentences=2)
        fecha_comentario = date.today() - timedelta(days=random.randint(1, 30))
        likes = random.randint(0, 50)

        session.execute_write(
            lambda tx: create_comentario(
                tx, 
                i, 
                titulo_comentario, 
                contenido_comentario, 
                fecha_comentario, 
                likes
            )
        )


    print("ENTRANDO A ULTIMAS RELACIONES")
    # Relaciones para publicaciones y comentarios
    session.execute_write(create_relation_COMPARTE)
    session.execute_write(create_relation_COMENTA)
    session.execute_write(create_relation_PERTENECE_A)
    session.execute_write(create_relation_CONTIENE_PUBLICACION)

driver.close()