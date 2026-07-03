from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
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

        data = resp.json()
        session["user_id"] = data["userId"]
        session["username"] = data["username"]
        session["nombre"] = data["nombreCompleto"]
        session["token"] = data["token"]
        session["rol"] = data["rol"]

        if not resp.ok:
            error = "Usuario o contraseña incorrectos."
            return render_template("login.html", error=error)

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


def _map_cronograma(c_list):
    if not c_list:
        return []
    res = []
    for f in c_list:
        res.append({
            "periodo": f.get("periodo"),
            "pg": str(f.get("pg", "S")).upper(),
            "saldo_inicial_cf": f.get("saldoInicialCf", 0),
            "interes_cf": f.get("interesCf", 0),
            "amort_cf": f.get("amortCf", 0),
            "seg_desgrav_cf": f.get("segDesgravCf", 0),
            "saldo_final_cf": f.get("saldoFinalCf", 0),
            "saldo_inicial": f.get("saldoInicial", 0),
            "interes": f.get("interes", 0),
            "amort": f.get("amort", 0),
            "cuota_capital": f.get("cuotaCapital", 0),
            "seg_desgrav": f.get("segDesgrav", 0),
            "seg_veh": f.get("segVeh", 0),
            "portes": f.get("portes", 0),
            "gastos_admin": f.get("gastosAdmin", 0),
            "gps": f.get("gps", 0),
            "cuota_total": f.get("cuotaTotal", 0),
            "saldo_final": f.get("saldoFinal", 0),
        })
    return res

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
        recientes_raw = r_rec.json() if r_rec.ok else []
        recientes = []
        for r in recientes_raw:
            recientes.append({
                "id": r.get("id"),
                "cliente": r.get("cliente"),
                "moneda": r.get("moneda"),
                "saldo_financiado": r.get("saldoFinanciado"),
                "tcea": r.get("tcea"),
                "created_at": r.get("creadoEn") if r.get("creadoEn") else ""
            })

    except requests.exceptions.RequestException as e:
        flash("No se pudo conectar con el backend.", "danger")
        stats = {"clientes": 0, "creditos": 0, "vehiculos": 0}
        recientes = []

    return render_template("dashboard.html", stats=stats, recientes=recientes, metodos_data=[], montos_data=[])


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/clientes", headers=headers)
    rows = resp.json() if resp.ok else []
    for r in rows:
        r["nombre_completo"] = r.get("nombreCompleto")
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

    # Obtain credits for client
    r_creditos = requests.get(f"{BACKEND_URL}/clientes/{cid}/creditos", headers=headers)
    creditos_raw = r_creditos.json() if r_creditos.ok else []
    creditos = []
    for r in creditos_raw:
        creditos.append({
            "id": r.get("id"),
            "cliente": r.get("cliente"),
            "vehiculo": r.get("vehiculo"),
            "moneda": r.get("moneda"),
            "saldo_financiado": r.get("saldoFinanciado"),
            "plazo_meses": r.get("plazoMeses"),
            "tcea": r.get("tcea"),
            "van": r.get("van"),
            "tir": r.get("tir"),
            "created_at": r.get("creadoEn") if r.get("creadoEn") else "",
            "es_elegido": "SI" if r.get("esElegido") else "NO"
        })

    r_vehiculos = requests.get(f"{BACKEND_URL}/vehiculos", headers=headers)
    vehiculos = []
    if r_vehiculos.ok:
        nombres_vehiculos = {c["vehiculo"] for c in creditos}
        for v in r_vehiculos.json():
            nombre = f"{v.get('marca')} {v.get('modelo')}"
            if nombre in nombres_vehiculos:
                vehiculos.append(v)

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

    return render_template("vehiculo_form.html", vehiculo=vehiculo, titulo="Editar Vehículo")


# ─────────────────────────────────────────────
# SIMULADOR / CRÉDITOS
# ─────────────────────────────────────────────
@app.route("/creditos")
@login_required
def creditos():
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/creditos", headers=headers)
    if not resp.ok:
        return render_template("creditos.html", creditos=[])
    
    rows = resp.json()
    mapped = []
    for r in rows:
        mapped.append({
            "id": r.get("id"),
            "cliente": r.get("cliente"),
            "vehiculo": r.get("vehiculo"),
            "tipo_moneda": r.get("moneda"),
            "saldo_financiado": r.get("saldoFinanciado"),
            "plazo_meses": r.get("plazoMeses"),
            "tcea": r.get("tcea"),
            "van": r.get("van"),
            "tir": r.get("tir"),
            "created_at": r.get("creadoEn") if r.get("creadoEn") else "",
            "es_elegido": "SI" if r.get("esElegido") else "NO"
        })
    return render_template("creditos.html", creditos=mapped)


@app.route("/creditos/<int:crid>")
@login_required
def credito_detalle(crid):
    headers = _auth_headers()
    resp = requests.get(f"{BACKEND_URL}/creditos/{crid}", headers=headers)
    if not resp.ok:
        return redirect(url_for("creditos"))
    
    r = resp.json()
    credito = {
        "id": r.get("id"),
        "es_elegido": "SI" if r.get("esElegido") else "NO",
        "cliente_nombre": r.get("clienteNombre"),
        "marca": r.get("vehiculoMarca"),
        "modelo": r.get("vehiculoModelo"),
        "anio": r.get("vehiculoAnio"),
        "tcea": r.get("tcea"),
        "van": r.get("van"),
        "tir": r.get("tir"),
        "saldo_financiado": r.get("saldoFinanciado"),
        "moneda": r.get("moneda"),
        "dni": r.get("clienteDni"),
        "email": r.get("clienteEmail"),
        "telefono": r.get("clienteTelefono"),
        "precio_vehiculo": r.get("precioVehiculo"),
        "cuota_inicial_pct": r.get("porcCuotaInicial"),
        "metodo_pago": r.get("metodoPago", "regular"),
        "pct_cuota_final": r.get("pctCuotaFinal", 0),
        "cok": r.get("cok", 0),
        "tipo_tasa": r.get("tipoTasa", ""),
        "tasa_valor": r.get("tasaValor"),
        "tem": r.get("tem"),
        "gracia_tipo": r.get("graciaTipo"),
        "gracia_meses": r.get("graciaMeses")
    }
    return render_template("credito_detalle.html", credito=credito, cronograma=_map_cronograma(r.get("cronograma", [])))


@app.route("/creditos/<int:crid>/elegir", methods=["POST"])
@login_required
def credito_elegir(crid):
    headers = _auth_headers()
    requests.patch(f"{BACKEND_URL}/creditos/{crid}/elegir", headers=headers)  # TODO
    flash("Crédito elegido.", "success")
    return redirect(url_for("creditos"))


@app.route("/creditos/nuevo", methods=["GET", "POST"])
@login_required
def credito_nuevo():
    headers = _auth_headers()
    try:
        # Obtener clientes para el select (frontend)
        r_clients = requests.get(f"{BACKEND_URL}/clientes", headers=headers)
        clientes = r_clients.json() if r_clients.ok else []
        for c in clientes:
            c["nombre"] = c.get("nombreCompleto")


        r_vehiculos = requests.get(f"{BACKEND_URL}/vehiculos", headers=headers)
        vehiculos = r_vehiculos.json() if r_vehiculos.ok else []

        if request.method == "POST":
            f = request.form.to_dict()
            # Convertir tipos numéricos si el backend lo requiere
            payload = {
                "clienteId": int(f.get("cliente_id")),
                "vehiculoId": int(f.get("vehiculo_id")),
                "precioVehiculo": float(f.get("precio_vehiculo")),
                "cuotaInicialPct": float(f.get("cuota_inicial_pct")),
                "tipoTasa": f.get("tipo_tasa"),
                "tasaValor": float(f.get("tasa_valor")),
                "capitalizacion": f.get("capitalizacion", "mensual"),
                "plazoMeses": int(f.get("plazo_meses")),
                "graciaTipo": f.get("gracia_tipo"),
                "graciaMeses": int(f.get("gracia_meses", 0)),
                "tsd": float(f.get("tsd")) / 100,
                "tsv": float(f.get("tsv")) / 100,
                "portes": float(f.get("portes", 0)),
                "gastosAdmin": float(f.get("gastos_admin", 0)),
                "gps": float(f.get("gps", 0)),
                "metodoPago": f.get("metodo_pago", "regular"),
                "pctCuotaFinal": float(f.get("pct_cuota_final", 40)) / 100 if f.get("metodo_pago") == "compra_inteligente" else 0,
                "cok": float(f.get("cok", 50)) / 100 if f.get("metodo_pago") == "compra_inteligente" else 0,
                "moneda": f.get("moneda", "soles")
            }
            # TODO: endpoint backend para crear simulación/crédito
            resp = requests.post(f"{BACKEND_URL}/creditos", json=payload, headers=headers)  # TODO
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
        r_clients = requests.get(f"{BACKEND_URL}/clientes", headers=headers)
        clientes = r_clients.json() if r_clients.ok else []
        for c in clientes:
            c["nombre"] = c.get("nombreCompleto")

        if request.method == "POST":
            f = request.form.to_dict()
            payload = {
                "clienteId": int(f.get("cliente_id")),
                "vehiculoId": int(f.get("vehiculo_id")),
                "precioVehiculo": float(f.get("precio_vehiculo")),
                "cuotaInicialPct": float(f.get("cuota_inicial_pct")),
                "tipoTasa": f.get("tipo_tasa"),
                "tasaValor": float(f.get("tasa_valor")),
                "capitalizacion": f.get("capitalizacion", "mensual"),
                "plazoMeses": int(f.get("plazo_meses")),
                "graciaTipo": f.get("gracia_tipo"),
                "graciaMeses": int(f.get("gracia_meses", 0)),
                "tsd": float(f.get("tsd")) / 100,
                "tsv": float(f.get("tsv")) / 100,
                "portes": float(f.get("portes", 0)),
                "gastosAdmin": float(f.get("gastos_admin", 0)),
                "gps": float(f.get("gps", 0)),
                "metodoPago": f.get("metodo_pago", "regular"),
                "pctCuotaFinal": float(f.get("pct_cuota_final", 40)) / 100 if f.get("metodo_pago") == "compra_inteligente" else 0,
                "cok": float(f.get("cok", 50)) / 100 if f.get("metodo_pago") == "compra_inteligente" else 0,
                "moneda": f.get("moneda", "soles")
            }
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


@app.route("/api/vehiculos/<int:cid>")
@login_required
def api_vehiculos(cid):
    headers = _auth_headers()
    # The Java backend has an endpoint for this: GET /api/clientes/{cid}/vehiculos or GET /api/vehiculos ?
    # Let's check SimulacionController or VehiculoController. 
    # For now I will fetch all and filter, or fetch from backend endpoint.
    resp = requests.get(f"{BACKEND_URL}/vehiculos", headers=headers)
    if resp.ok:
        vehiculos = resp.json()
        filtered = vehiculos
        res = []
        for v in filtered:
            res.append({
                "id": v["id"],
                "nombre": f"{v['marca']} {v['modelo']}",
                "precio": v["precio"],
                "bloqueado": v.get("bloqueado", False)
            })
        return jsonify(res)
    return jsonify([])

@app.route("/api/calcular", methods=["POST"])
@login_required
def api_calcular():
    headers = _auth_headers()
    d = request.get_json()
    payload = {
        "clienteId": 1, # dummy, backend /calcular doesn't strictly need real id for math but requires NotNull
        "vehiculoId": 1,
        "precioVehiculo": float(d["precio_vehiculo"]),
        "cuotaInicialPct": float(d["cuota_inicial_pct"]),
        "tipoTasa": d["tipo_tasa"],
        "tasaValor": float(d["tasa_valor"]),
        "capitalizacion": d.get("capitalizacion", "mensual"),
        "plazoMeses": int(d["plazo_meses"]),
        "graciaTipo": d.get("gracia_tipo", "ninguno"),
        "graciaMeses": int(d.get("gracia_meses", 0)),
        "tsd": float(d["tsd"]) / 100,
        "tsv": float(d["tsv"]) / 100,
        "portes": float(d["portes"]),
        "gastosAdmin": float(d.get("gastos_admin", 0)),
        "gps": float(d.get("gps", 0)),
        "metodoPago": d.get("metodo_pago", "regular"),
        "pctCuotaFinal": float(d.get("pct_cuota_final", 40)) / 100 if d.get("metodo_pago") == "compra_inteligente" else 0,
        "cok": float(d.get("cok", 50)) / 100 if d.get("metodo_pago") == "compra_inteligente" else 0,
        "moneda": d.get("moneda", "soles")
    }
    resp = requests.post(f"{BACKEND_URL}/calcular", json=payload, headers=headers)
    if resp.ok:
        data = resp.json()
        # The frontend JS expects: { sf, ci_monto, tem, tea, van, tir, tcea, cronograma }
        # The Java backend /calcular returns SimulacionDtos.CalculoPreview which has these fields
        # Let's map it to what the JS expects
        return jsonify({
            "sf": data.get("saldoFinanciado"),
            "ci_monto": data.get("cuotaInicialMonto", 0), # Java might not return this, we can calc it
            "tem": data.get("tem"),
            "tea": data.get("tea", 0),
            "van": data.get("van"),
            "tir": data.get("tir"),
            "tcea": data.get("tcea"),
            "cronograma": _map_cronograma(data.get("cronograma", []))
        })
    return jsonify({"error": "Error al calcular"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=3000)
