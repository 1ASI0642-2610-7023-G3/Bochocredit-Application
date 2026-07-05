from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
import json, math, functools, os
import requests

app = Flask(__name__)
app.secret_key = '8EQ9erCMDArSWcaXnAZ6pcP3BMBPc1HXwM5COQNuWiD'

BACKEND_URL = "http://localhost:8080/api"

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("rol") == "ADMIN":
            flash("Acceso denegado: no tiene los permisos adecuados.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated


@app.before_request
def enforce_password_change():
    if session.get("user_id") and session.get("must_change_password", False):
        allowed_endpoints = {"cambiar_password", "logout", "static"}
        current = request.endpoint

        if current not in allowed_endpoints:
            return redirect(url_for("cambiar_password", uid=session["user_id"]))


@app.route("/", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        resp = requests.post(f"{BACKEND_URL}/auth/login", json={"username": u, "password": p})

        if not resp.ok:
            error = "Usuario o contraseña incorrectos."
            return render_template("login.html", error=error)

        data = resp.json()
        session["user_id"] = data["userId"]
        session["username"] = data["username"]
        session["nombre"] = data["nombreCompleto"]
        session["token"] = data["token"]
        session["rol"] = data["rol"]


        # Check if backend requires password change
        r = requests.get(f"{BACKEND_URL}/usuarios/renovar-password/{session['user_id']}", headers=_auth_headers())
        if r.json() == True:
            session["must_change_password"] = True
            flash("Debe cambiar su contraseña antes de continuar.", "warning")
            return redirect(url_for("cambiar_password", uid=session["user_id"]))

        return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def _auth_headers():
    """
    Devuelve cabeceras de autorización si usas token en session.
    Ajusta según tu esquema (Bearer JWT, cookie, etc.).
    """
    headers = {"Accept": "application/json"}
    token = session.get("token")  # TODO: si usas JWT, guarda token en session['token']
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    headers = _auth_headers()
    try:
        stats = {}
        r = requests.get(f"{BACKEND_URL}/dashboard/cantidad-clientes", headers=headers)
        stats["clientes"] = r.json() if r.ok else 0
        r = requests.get(f"{BACKEND_URL}/dashboard/cantidad-creditos", headers=headers)
        stats["creditos"] = r.json() if r.ok else 0
        r = requests.get(f"{BACKEND_URL}/dashboard/cantidad-vehiculos", headers=headers)
        stats["vehiculos"] = r.json() if r.ok else 0

        # recientes: obtener últimas simulaciones/creditos elegidos
        r_rec = requests.get(f"{BACKEND_URL}/dashboard/creditos-recientes", headers=headers)
        recientes = r_rec.json() if r_rec.ok else []

    except requests.exceptions.RequestException as e:
        flash("No se pudo conectar con el backend.", "danger")
        stats = {"clientes": 0, "creditos": 0, "vehiculos": 0}
        recientes = []

    return render_template("dashboard.html", stats=stats, recientes=recientes)


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/clientes", headers=headers)
    try:
        rows = resp.json()


    except ValueError:
        print(resp)
        print(resp.status_code, resp.headers)
        print("Response was not JSON:", resp.text)
        rows = []
    return render_template("clientes.html", clientes=rows)


@app.route("/clientes/nuevo", methods=["GET","POST"])
@login_required
def cliente_nuevo():
    headers = _auth_headers()
    if request.method == "POST":
        f = request.form
        resp = requests.post(f"{BACKEND_URL}/clientes", json=f, headers=headers)  # TODO
        if resp.status_code == 201:
            flash("Cliente registrado exitosamente.", "success")
            return redirect(url_for("clientes"))
        else:
            flash("Error al registrar cliente.", "danger")
    return render_template("cliente_form.html", cliente=None, titulo="Nuevo Cliente")


@app.route("/clientes/<int:cid>/editar", methods=["GET","POST"])
@login_required
def cliente_editar(cid):
    headers = _auth_headers()
    if request.method == "POST":
        f = request.form
        resp = requests.put(f"{BACKEND_URL}/clientes/{cid}", json=f, headers=headers)  # TODO
        flash("Cliente actualizado.", "success")
        return redirect(url_for("clientes"))
    resp = requests.get(f"{BACKEND_URL}/clientes/{cid}", headers=headers)  # TODO
    cliente = resp.json()
    return render_template("cliente_form.html", cliente=cliente, titulo="Editar Cliente")


@app.route("/clientes/<int:cid>/eliminar", methods=["POST"])
@login_required
def cliente_eliminar(cid):
    headers = _auth_headers()
    requests.delete(f"{BACKEND_URL}/clientes/{cid}", headers=headers)  # TODO
    flash("Cliente eliminado.", "warning")
    return redirect(url_for("clientes"))


@app.route("/clientes/<int:cid>")
@login_required
def cliente_detalle(cid):
    headers = _auth_headers()
    try:
        # Cliente
        r_cli = requests.get(f"{BACKEND_URL}/clientes/{cid}", headers=headers)  # TODO: backend path
        if not r_cli.ok:
            flash("Cliente no encontrado.", "warning")
            return redirect(url_for("clientes"))
        cliente = r_cli.json()

    except requests.exceptions.RequestException:
        flash("Error al comunicarse con el backend.", "danger")
        return redirect(url_for("clientes"))

    return render_template("cliente_detalle.html", cliente=cliente, vehiculos=vehiculos, creditos=creditos)




# ─────────────────────────────────────────────
# VEHÍCULOS
# ─────────────────────────────────────────────
@app.route("/vehiculos")
@login_required
def vehiculos():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/vehiculos", headers=headers)
    rows = resp.json()
    return render_template("vehiculos.html", vehiculos=rows)


@app.route("/vehiculos/nuevo", methods=["GET","POST"])
@login_required
def vehiculo_nuevo():
    headers = _auth_headers()
    if request.method == "POST":
        f = request.form
        requests.post(f"{BACKEND_URL}/vehiculos", json=f, headers=headers)
        flash("Vehículo registrado.", "success")
        return redirect(url_for("vehiculos"))
    return render_template("vehiculo_form.html", vehiculo=None, titulo="Nuevo Vehículo")


@app.route("/vehiculos/<int:vid>/editar", methods=["GET","POST"])
@login_required
def vehiculo_editar(vid):
    headers = _auth_headers()
    try:
        if request.method == "POST":
            f = request.form.to_dict()
            # Normalizar/validar campos según backend
            resp = requests.put(f"{BACKEND_URL}/vehiculos/{vid}", json=f, headers=headers)  # TODO
            if resp.ok:
                flash("Vehículo actualizado.", "success")
            else:
                flash("Error al actualizar vehículo.", "danger")
            return redirect(url_for("vehiculos"))

        # GET: obtener vehículo
        r = requests.get(f"{BACKEND_URL}/vehiculos/{vid}", headers=headers)  # TODO
        if not r.ok:
            flash("Vehículo no encontrado.", "warning")
            return redirect(url_for("vehiculos"))
        vehiculo = r.json()

    except requests.exceptions.RequestException:
        flash("Error de conexión con el backend.", "danger")
        return redirect(url_for("vehiculos"))

    return render_template("vehiculo_form.html", vehiculo=vehiculo, clientes=clientes, titulo="Editar Vehículo")


# ─────────────────────────────────────────────
# SIMULADOR / CRÉDITOS
# ─────────────────────────────────────────────
@app.route("/creditos")
@login_required
def creditos():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/creditos", headers=headers)  # TODO
    rows = resp.json()
    return render_template("creditos.html", creditos=rows)


@app.route("/creditos/<int:crid>")
@login_required
def credito_detalle(crid):
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/creditos/{crid}", headers=headers)  # TODO
    credito = resp.json()

    resp = requests.get(f"{BACKEND_URL}/creditos/pagos/{crid}", headers=headers)  # TODO
    pagos = resp.json()

    return render_template("credito_detalle.html", credito=credito, cronograma=pagos)


@app.route("/creditos/<int:crid>/elegir", methods=["POST"])
@login_required
def credito_elegir(crid):
    headers = _auth_headers()
    requests.patch(f"{BACKEND_URL}/creditos/{crid}/elegir", headers=headers)  # TODO
    flash("Crédito elegido.", "success")
    return redirect(url_for("creditos"))


def getCapitalizacion(capi: str) -> int:
    return int(capi)


def getCreditoRequest(f):
    return {
        "moneda": f.get("moneda", "soles"),
        "valorVenta": float(f.get("valorVenta")),
        
        "cuotaInicialPct": float(f.get("cuotaInicialPct")),
        "cuotaFinalPct": float(f.get("cuotaFinalPct")),

        "tipoTasa": f.get("tipoTasa"),
        "capitalizacion": int(getCapitalizacion(f.get("capitalizacion"))),
        "tasaInteres": float(f.get("tasaInteres")),
        
        "plazoMeses": int(f.get("plazoMeses")),
        
        "tipoGracia": f.get("tipoGracia"),
        "periodoGraciaMeses": int(f.get("periodoGraciaMeses")),

        "seguroDesgPct": float(f.get("seguroDesgPct")),
        "seguroVehicularPct": float(f.get("seguroVehicularPct")),

        "gastosIniciales": {
            "NOTARIAL": float(f.get("notariales")),
            "REGISTRAL": float(f.get("registrales"))
        },
        "gastosPeriodicos": {
            "Portes": float(f.get("portes")),
            "Admin": float(f.get("admin")),
            "Gps": float(f.get("gps"))
        },

        "cok": float(f.get("cok")),

        "clienteId": int(f.get("clienteId")),
        "vehiculoId": int(f.get("vehiculoId")),
        "usuarioId": session.get("user_id")
    }



@app.route("/creditos/nuevo", methods=["GET", "POST"])
@login_required
def credito_nuevo():
    headers = _auth_headers()
    try:
        # Obtener clientes para el select (frontend)
        r_clients = requests.get(f"{BACKEND_URL}/clientes", headers=headers)  # TODO
        clientes = r_clients.json() if r_clients.ok else []


        r_vehiculos = requests.get(f"{BACKEND_URL}/vehiculos", headers=headers)
        vehiculos = r_vehiculos.json() if r_vehiculos.ok else []

        if request.method == "POST":
            f = request.form.to_dict()
            # Convertir tipos numéricos si el backend lo requiere
            rBody = getCreditoRequest(f)

            resp = requests.post(f"{BACKEND_URL}/creditos", json=rBody, headers=headers)  # TODO
            
            if resp.status_code in (200, 201):
                flash("Crédito calculado y guardado.", "success")
                return redirect(url_for("creditos"))
            else:
                # si backend devuelve errores, mostrarlos
                try:
                    err = resp.json().get("message", "Error al crear crédito.")
                except Exception:
                    err = "Error al crear crédito."
                flash(err, "danger")

    except requests.exceptions.RequestException:
        flash("No se pudo conectar con el backend.", "danger")
        return redirect(url_for("creditos"))

    return render_template("credito_form.html", clientes=clientes, vehiculos=vehiculos, titulo="Nueva Oferta de Crédito")



@app.route("/creditos/<int:crid>/editar", methods=["GET", "POST"])
@login_required
def credito_editar(crid):
    headers = _auth_headers()
    try:
        # Obtener crédito actual
        r = requests.get(f"{BACKEND_URL}/creditos/{crid}", headers=headers)  # TODO
        if not r.ok:
            flash("Crédito no encontrado.", "warning")
            return redirect(url_for("creditos"))
        credito = r.json()

        # Obtener lista de clientes para el formulario (si aplica)
        r_clients = requests.get(f"{BACKEND_URL}/clientes", headers=headers)  # TODO
        clientes = r_clients.json() if r_clients.ok else []

        if request.method == "POST":
            f = request.form.to_dict()
            payload = getCreditoRequest(f)

            resp = requests.put(f"{BACKEND_URL}/creditos/{crid}", json=payload, headers=headers)  # TODO
            if resp.ok:
                flash("Crédito recalculado y actualizado.", "success")
                return redirect(url_for("credito_detalle", crid=crid))
            else:
                flash("Error al actualizar crédito.", "danger")

    except requests.exceptions.RequestException:
        flash("Error de conexión con el backend.", "danger")
        return redirect(url_for("creditos"))

    return render_template("credito_form.html", clientes=clientes, credito=credito, titulo="Editar Crédito")





# ─────────────────────────────────────────────
# Usuarios
# ─────────────────────────────────────────────
@app.route("/usuarios")
@login_required
@admin_required
def usuarios():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/usuarios", headers=headers)
    rows = resp.json()
    return render_template("usuarios.html", usuarios=rows)



@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def usuario_nuevo():
    headers = _auth_headers()
    if request.method == "POST":
        f = request.form.to_dict()
        f["rol"] = f.get("rol", 2)
        f["nombreCompleto"] = f.get("nombres", "") + " " + f.get("apellidos", "")
        del f["nombres"]
        del f["apellidos"]
        resp = requests.post(f"{BACKEND_URL}/usuarios", json=f, headers=headers)
        if resp.status_code in (200, 201):
            data = resp.json()
            flash(f"Usuario creado exitosamente. Su contraseña es {data.get('password')}", "success")
            return redirect(url_for("usuarios"))
        else:
            flash("Error al crear empleado.", "danger")
    return render_template("usuario_form.html", usuario=None, titulo="Nuevo Empleado")


@app.route("/usuarios/cambiar_password/<int:uid>", methods=["GET", "POST"])
@login_required
def cambiar_password(uid):
    headers = _auth_headers()
    if request.method == "POST":
        f = request.form.to_dict()

        payload = {
            "username": session["username"],
            "passwordAntigua": f.get("passwordAntigua"),
            "passwordNueva": f.get("passwordNueva")
        }

        resp = requests.patch(f"{BACKEND_URL}/usuarios/cambiar-password/{uid}", json=payload, headers=headers)
        if resp.json():
            flash("Contraseña actualizada.", "success")
            session["must_change_password"] = False
            return redirect(url_for("dashboard"))
        else:
            flash("Error al actualizar contraseña.", "danger")

    # GET: show form
    return render_template("password_form.html", usuario_id=uid, titulo="Cambiar Contraseña")


@app.route("/usuarios/<int:uid>/eliminar", methods=["POST"])
@login_required
@admin_required
def usuario_eliminar(uid):
    headers = _auth_headers()
    requests.delete(f"{BACKEND_URL}/usuarios/{uid}", headers=headers)
    flash("Usuario eliminado.", "warning")
    return redirect(url_for("usuarios"))


if __name__ == "__main__":
    app.run(debug=True, port=3000)
