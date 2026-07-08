import json, math, functools, os
import requests


BACKEND_URL = "http://localhost:8080/api"



def login():
    resp = requests.post(f"{BACKEND_URL}/auth/login", json={"username": "administrador", "password": "admin123"})

    if resp.status_code == 200:
        data = resp.json()
        return data["token"]
    return None


def _auth_headers(token):
    """
    Devuelve cabeceras de autorización si usas token en session.
    Ajusta según tu esquema (Bearer JWT, cookie, etc.).
    """
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def crearCronograma(token):
    request = {
        "clienteId": 1,
        "vehiculoId": 2,
        "moneda": "soles",
        "precioVehiculo": 30000.00,
        "cuotaInicialPct": 20.0,
        "plazoMeses": 36,
        "tipoTasa": "nominal_anual",
        "tasaValor": 12.5,
        "capitalizacion": "mensual",
        "graciaTipo": "parcial",
        "graciaMeses": 3,

        "tsd": 0.0051,
        "tsv": 0.02,
        "portes": 50.00,
        "gastosAdmin": 100.00,
        "gps": 25.00,

        "metodoPago": "compra_inteligente",

        "pctCuotaFinal": 35.0,
        "cok": 25.0
        }
    
    auth_headers = _auth_headers(token)
    r = requests.post(f"{BACKEND_URL}/creditos", json=request, headers=auth_headers)

    print(r.status_code)
    print(r.json())


resp = requests.get(f"{BACKEND_URL}/vehiculos", headers=_auth_headers(login()))

#print(f"Response: {resp}\nStatus Code: {resp.status_code}\nHeaders: {resp.headers}\nContent: {resp.text}")


#crearCronograma(login())


#resp = requests.get(f"{BACKEND_URL}/creditos/1", headers=_auth_headers(login()))

for vehicule in resp.json():
    for k, v in vehicule.items():
        print(f"{k}: {v}")


#print("\n\n\n")
#resp = requests.get(f"{BACKEND_URL}/pagos/1", headers=_auth_headers(login()))


#for k, v in resp.json().items():
#    print(f"{k}: {v}")
#
