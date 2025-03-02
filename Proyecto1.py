import random
from datetime import date, timedelta
from neo4j import GraphDatabase
from faker import Faker

fake = Faker()

URI = "neo4j+s://6e796de7.databases.neo4j.io"
AUTH = ("neo4j", "sgmvLP0_IuV6rNHxSaTR0sTYqAumzrCUAwhl3ZsjvcE")


def DELETE_DATABASE(tx):
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    tx.run(query)

def create_user(tx, id_usuario, userName, isInfluencer = False, edad = random.randint(18, 60), password="1234"):

    if isInfluencer:
        verificado = random.random() < 0.5
    else:
        verificado = random.random() < 0.2

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

import random
from datetime import date, timedelta

def create_relation_SIGUE_A(tx):
    # Obtener todos los usuarios y verificar sus etiquetas
    query = """
    MATCH (u:Usuario)
    RETURN u.id_usuario AS id_usuario, labels(u) AS labels
    """
    users = tx.run(query).data()
    
    for user in users:
        id_usuario = user["id_usuario"]
        labels = user["labels"]
        
        # Probabilidad diferente si el usuario es Influencer o no
        probabilidad_seguir = 0.2 if "Influencer" in labels else 0.4

        # Seleccionar usuarios a seguir
        posibles_seguidos = [u["id_usuario"] for u in users if u["id_usuario"] != id_usuario]
        seguidos = [uid for uid in posibles_seguidos if random.random() < probabilidad_seguir]

        for seguido in seguidos:
            # Generar valores para las propiedades
            fecha_inicio = f"date('{date.today() - timedelta(days=random.randint(1, 365))}')"  # Fecha aleatoria en el último año
            notificaciones_activas = random.choice([True, False])
            recomendado_por_algoritmo = random.choice([True, False])  # Si fue sugerido por el sistema

            query = f"""
            MATCH (u1:Usuario {{id_usuario: $id1}}), (u2:Usuario {{id_usuario: $id2}})
            MERGE (u1)-[:SIGUE_A {{
                fecha_inicio: {fecha_inicio}, 
                notificaciones_activas: {notificaciones_activas}, 
                recomendado_por_algoritmo: {recomendado_por_algoritmo}
            }}]->(u2)
            """
            tx.run(query, id1=id_usuario, id2=seguido)

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
    MATCH (u:Usuario), (m:Mensaje)
    WHERE rand() < 0.7
    MERGE (u)-[:ESCRIBIO_MENSAJE {
        escrito_a_las: m.fecha_envio,
        enviado: true,
        editado: rand() < 0.3
    }]->(m)
    """
    tx.run(query)


def create_relation_FUE_ENVIADO_A(tx):
    query = """
    MATCH (m:Mensaje), (u:Usuario)
    WHERE rand() < 0.5
    MERGE (m)-[r:FUE_ENVIADO_A]->(u)
    SET r.Fecha_envio = m.fecha_envio,
        r.Leido = rand() < 0.6
    WITH r, rand() < 0.6 AS has_read
    FOREACH (_ IN CASE WHEN has_read THEN [1] ELSE [] END |
        SET r.fecha_de_lectura = r.Fecha_envio
    )
    """
    tx.run(query)

def create_relation_ES_INTEGRANTE_DE(tx):
    query = """
    MATCH (u:Usuario), (g:Grupo)
    WHERE rand() < 0.5
    MERGE (u)-[:ES_INTEGRANTE_DE {
        Fecha_de_ingreso: date(),
        Rol: CASE WHEN rand() < 0.1 THEN "Admin" ELSE "Miembro" END,
        Silenciado: rand() < 0.3
    }]->(g)
    """
    tx.run(query)

driver = GraphDatabase.driver(URI, auth=AUTH)

with driver.session(database="neo4j") as session:

    # Descomentar si se quiere borrar la base de datos
    session.execute_write(DELETE_DATABASE)

    for i in range(1, 20):
        nombre = fake.name()
        isInfluencer = random.random() < 0.3
        session.execute_write(lambda tx: create_user(tx, i, nombre.replace(" ", ""), isInfluencer))

    session.execute_write(create_relation_SIGUE_A)
    session.execute_write(create_relation_BLOQUEA)

    for i in range(1, 50):
        texto = fake.sentence()
        session.execute_write(lambda tx: create_mensaje(tx, i, texto))

    for i in range(1, 10):
        nombre = fake.company()
        session.execute_write(lambda tx: create_grupo(tx, i, nombre))

    session.execute_write(create_relation_ESCRIBIO_MENSAJE)
    session.execute_write(create_relation_FUE_ENVIADO_A)
    session.execute_write(create_relation_ES_INTEGRANTE_DE)

driver.close()