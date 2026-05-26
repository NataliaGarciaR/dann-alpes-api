from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
import certifi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

client = MongoClient(
    os.environ["MONGO_URI"],
    tls=True,
    tlsCAFile=certifi.where()
)

db = client["dann_alpes_nosql"]
resenas = db["reseñas"]


def convertir_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/")
def inicio():
    return {"estado": "API Dann-Alpes funcionando"}


# RF1 - Crear reseña
@app.post("/hoteles/{hotel_id}/resenas")
def crear_resena(hotel_id: int, datos: dict):

    if datos.get("estado_reserva") != "completada":
        return {
            "error": "La reserva no está completada"
        }

    existe = resenas.find_one({
        "hotel_id": hotel_id,
        "cliente_id": datos["cliente_id"],
        "reserva_id": datos["reserva_id"]
    })

    if existe:
        return {
            "error": "Ya existe una reseña para esta estadía"
        }

    nueva = {
        "hotel_id": hotel_id,
        "cliente_id": datos["cliente_id"],
        "reserva_id": datos["reserva_id"],
        "calificacion": datos["calificacion"],
        "texto": datos["texto"],
        "fecha_creacion": datetime.now().isoformat(),
        "fecha_actualizacion": datetime.now().isoformat(),
        "estado": "publicada",
        "utiles": 0,
        "destacada": False
    }

    resultado = resenas.insert_one(nueva)

    return {
        "mensaje": "Reseña creada",
        "id": str(resultado.inserted_id)
    }


# RF2 - Editar reseña
@app.put("/resenas/{resena_id}")
def editar_resena(resena_id: str, datos: dict):

    datos["fecha_actualizacion"] = datetime.now().isoformat()

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {"$set": datos}
    )

    return {"mensaje": "Reseña actualizada"}


# RF3 - Eliminar reseña
@app.delete("/resenas/{resena_id}")
def eliminar_resena(resena_id: str):

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {"$set": {"estado": "eliminada"}}
    )

    return {"mensaje": "Reseña eliminada"}


# RF4 - Consultar reseñas de un hotel
@app.get("/hoteles/{hotel_id}/resenas")
def consultar_resenas_hotel(hotel_id: int):

    datos = list(
        resenas.find({
            "hotel_id": hotel_id,
            "estado": "publicada"
        }).sort([
            ("destacada", -1),
            ("utiles", -1),
            ("fecha_creacion", -1)
        ])
    )

    return [convertir_id(r) for r in datos]


# RF5 - Marcar reseña como útil
@app.post("/resenas/{resena_id}/util")
def marcar_util(resena_id: str):

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {"$inc": {"utiles": 1}}
    )

    return {"mensaje": "Reseña marcada como útil"}


# RF6 - Consultar historial de reseñas propias
@app.get("/clientes/{cliente_id}/resenas")
def historial_resenas(cliente_id: int):

    datos = list(
        resenas.find(
            {"cliente_id": cliente_id}
        ).sort([
            ("fecha_creacion", -1),
            ("hotel_id", 1)
        ])
    )

    return [convertir_id(r) for r in datos]


# RF7 - Responder reseña
@app.post("/resenas/{resena_id}/respuesta")
def responder_resena(resena_id: str, datos: dict):

    respuesta = {
        "admin_id": datos["admin_id"],
        "texto": datos["texto"],
        "fecha": datetime.now().isoformat()
    }

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {"$set": {"respuesta_admin": respuesta}}
    )

    return {"mensaje": "Respuesta registrada"}


# RF8 - Eliminar reseña por administrador
@app.delete("/admin/resenas/{resena_id}")
def eliminar_resena_admin(resena_id: str):

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {
            "$set": {
                "estado": "eliminada_por_admin"
            }
        }
    )

    return {"mensaje": "Reseña eliminada por administrador"}


# RF9 - Destacar reseña
@app.post("/resenas/{resena_id}/destacar")
def destacar_resena(resena_id: str):

    resena = resenas.find_one(
        {"_id": ObjectId(resena_id)}
    )

    hotel_id = resena["hotel_id"]

    resenas.update_many(
        {"hotel_id": hotel_id},
        {"$set": {"destacada": False}}
    )

    resenas.update_one(
        {"_id": ObjectId(resena_id)},
        {"$set": {"destacada": True}}
    )

    return {"mensaje": "Reseña destacada"}