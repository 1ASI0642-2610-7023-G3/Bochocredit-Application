from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, json, math, functools, os

app = Flask(__name__)
app.secret_key = "bochocredit_secret_2026"

DB = "bochocredit.db"

# ─────────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT,
            rol TEXT DEFAULT 'asesor'
        );
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            dni TEXT UNIQUE NOT NULL,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            anio INTEGER,
            precio REAL NOT NULL,
            descripcion TEXT,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        );
        CREATE TABLE IF NOT EXISTS creditos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            vehiculo_id INTEGER NOT NULL,
            moneda TEXT NOT NULL,
            precio_vehiculo REAL NOT NULL,
            cuota_inicial_pct REAL NOT NULL,
            cuota_inicial_monto REAL NOT NULL,
            saldo_financiado REAL NOT NULL,
            tipo_tasa TEXT NOT NULL,
            tasa_valor REAL NOT NULL,
            capitalizacion TEXT,
            tem REAL NOT NULL,
            plazo_meses INTEGER NOT NULL,
            gracia_tipo TEXT NOT NULL,
            gracia_meses INTEGER NOT NULL,
            tsd REAL NOT NULL,
            tsv REAL NOT NULL,
            portes REAL NOT NULL,
            tcea REAL,
            van REAL,
            tir REAL,
            cronograma TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id)
        );
        """)
        # seed admin user
        try:
            db.execute("INSERT INTO users(username,password,nombre,rol) VALUES(?,?,?,?)",
                ("admin", generate_password_hash("admin123"), "Administrador", "admin"))
            db.commit()
        except:
            pass

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

@app.route("/", methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user["password"], p):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["nombre"] = user["nombre"]
            return redirect(url_for("dashboard"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "clientes": db.execute("SELECT COUNT(*) as c FROM clientes").fetchone()["c"],
        "creditos": db.execute("SELECT COUNT(*) as c FROM creditos").fetchone()["c"],
        "vehiculos": db.execute("SELECT COUNT(*) as c FROM vehiculos").fetchone()["c"],
    }
    recientes = db.execute("""
        SELECT cr.id, cl.nombres||' '||cl.apellidos as cliente,
               cr.moneda, cr.saldo_financiado, cr.tcea, cr.created_at
        FROM creditos cr JOIN clientes cl ON cr.cliente_id=cl.id
        ORDER BY cr.created_at DESC LIMIT 5
    """).fetchall()
    return render_template("dashboard.html", stats=stats, recientes=recientes)

# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    db = get_db()
    rows = db.execute("SELECT * FROM clientes ORDER BY created_at DESC").fetchall()
    return render_template("clientes.html", clientes=rows)

@app.route("/clientes/nuevo", methods=["GET","POST"])
@login_required
def cliente_nuevo():
    if request.method == "POST":
        f = request.form
        try:
            db = get_db()
            db.execute("INSERT INTO clientes(nombres,apellidos,dni,telefono,email,direccion) VALUES(?,?,?,?,?,?)",
                (f["nombres"], f["apellidos"], f["dni"], f["telefono"], f["email"], f["direccion"]))
            db.commit()
            flash("Cliente registrado exitosamente.", "success")
            return redirect(url_for("clientes"))
        except sqlite3.IntegrityError:
            flash("El DNI ya está registrado.", "danger")
    return render_template("cliente_form.html", cliente=None, titulo="Nuevo Cliente")

@app.route("/clientes/<int:cid>/editar", methods=["GET","POST"])
@login_required
def cliente_editar(cid):
    db = get_db()
    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cid,)).fetchone()
    if not cliente:
        return redirect(url_for("clientes"))
    if request.method == "POST":
        f = request.form
        db.execute("UPDATE clientes SET nombres=?,apellidos=?,dni=?,telefono=?,email=?,direccion=? WHERE id=?",
            (f["nombres"], f["apellidos"], f["dni"], f["telefono"], f["email"], f["direccion"], cid))
        db.commit()
        flash("Cliente actualizado.", "success")
        return redirect(url_for("clientes"))
    return render_template("cliente_form.html", cliente=cliente, titulo="Editar Cliente")

@app.route("/clientes/<int:cid>/eliminar", methods=["POST"])
@login_required
def cliente_eliminar(cid):
    db = get_db()
    db.execute("DELETE FROM clientes WHERE id=?", (cid,))
    db.commit()
    flash("Cliente eliminado.", "warning")
    return redirect(url_for("clientes"))

@app.route("/clientes/<int:cid>")
@login_required
def cliente_detalle(cid):
    db = get_db()
    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cid,)).fetchone()
    vehiculos = db.execute("SELECT * FROM vehiculos WHERE cliente_id=?", (cid,)).fetchall()
    creditos = db.execute("""
        SELECT cr.*, v.marca||' '||v.modelo as vehiculo
        FROM creditos cr JOIN vehiculos v ON cr.vehiculo_id=v.id
        WHERE cr.cliente_id=?
        ORDER BY cr.created_at DESC
    """, (cid,)).fetchall()
    return render_template("cliente_detalle.html", cliente=cliente, vehiculos=vehiculos, creditos=creditos)

# ─────────────────────────────────────────────
# VEHÍCULOS
# ─────────────────────────────────────────────
@app.route("/vehiculos")
@login_required
def vehiculos():
    db = get_db()
    rows = db.execute("""
        SELECT v.*, c.nombres||' '||c.apellidos as cliente
        FROM vehiculos v JOIN clientes c ON v.cliente_id=c.id
        ORDER BY v.id DESC
    """).fetchall()
    return render_template("vehiculos.html", vehiculos=rows)

@app.route("/vehiculos/nuevo", methods=["GET","POST"])
@login_required
def vehiculo_nuevo():
    db = get_db()
    clientes = db.execute("SELECT id, nombres||' '||apellidos as nombre FROM clientes ORDER BY nombres").fetchall()
    if request.method == "POST":
        f = request.form
        db.execute("INSERT INTO vehiculos(cliente_id,marca,modelo,anio,precio,descripcion) VALUES(?,?,?,?,?,?)",
            (f["cliente_id"], f["marca"], f["modelo"], f["anio"], f["precio"], f["descripcion"]))
        db.commit()
        flash("Vehículo registrado.", "success")
        return redirect(url_for("vehiculos"))
    return render_template("vehiculo_form.html", vehiculo=None, clientes=clientes, titulo="Nuevo Vehículo")

@app.route("/vehiculos/<int:vid>/editar", methods=["GET","POST"])
@login_required
def vehiculo_editar(vid):
    db = get_db()
    vehiculo = db.execute("SELECT * FROM vehiculos WHERE id=?", (vid,)).fetchone()
    clientes = db.execute("SELECT id, nombres||' '||apellidos as nombre FROM clientes ORDER BY nombres").fetchall()
    if request.method == "POST":
        f = request.form
        db.execute("UPDATE vehiculos SET cliente_id=?,marca=?,modelo=?,anio=?,precio=?,descripcion=? WHERE id=?",
            (f["cliente_id"], f["marca"], f["modelo"], f["anio"], f["precio"], f["descripcion"], vid))
        db.commit()
        flash("Vehículo actualizado.", "success")
        return redirect(url_for("vehiculos"))
    return render_template("vehiculo_form.html", vehiculo=vehiculo, clientes=clientes, titulo="Editar Vehículo")

# ─────────────────────────────────────────────
# CÁLCULO FINANCIERO
# ─────────────────────────────────────────────
def calcular_tem(tipo_tasa, tasa_valor, capitalizacion):
    tasa = tasa_valor / 100
    if tipo_tasa == "efectiva_anual":
        return (1 + tasa) ** (1/12) - 1
    elif tipo_tasa == "efectiva_mensual":
        return tasa
    elif tipo_tasa == "nominal_anual":
        m_map = {"diaria":360,"quincenal":24,"mensual":12,"bimestral":6,"trimestral":4,"cuatrimestral":3,"semestral":2,"anual":1}
        m = m_map.get(capitalizacion, 12)
        return (1 + tasa/m) ** (m/12) - 1
    return tasa

def calcular_tir(flujos, tol=1e-7, max_iter=1000):
    # Newton-Raphson
    r = 0.01
    for _ in range(max_iter):
        f = sum(flujos[t] / (1+r)**t for t in range(len(flujos)))
        df = sum(-t * flujos[t] / (1+r)**(t+1) for t in range(1, len(flujos)))
        if abs(df) < 1e-15:
            break
        r_new = r - f/df
        if abs(r_new - r) < tol:
            return r_new
        r = r_new
    return r

def generar_cronograma(sf, tem, n, gracia_tipo, gracia_meses, tsd, tsv, vv, portes):
    filas = []
    saldo = sf

    # Cuota base para período activo
    n_activo = n - gracia_meses
    if gracia_tipo == "total":
        sc = sf * (1 + tem) ** gracia_meses
        cuota_base = (sc * tem) / (1 - (1+tem)**(-n_activo))
    else:
        sc = sf
        cuota_base = (sf * tem) / (1 - (1+tem)**(-n_activo)) if n_activo > 0 else 0

    flujos = [sf]  # flujo inicial positivo (desembolso recibido)

    for k in range(1, n+1):
        interes = saldo * tem
        seg_desgrav = saldo * tsd
        seg_veh = vv * tsv

        if gracia_tipo == "total" and k <= gracia_meses:
            amort = 0
            cuota_capital = 0
            saldo = saldo * (1 + tem)  # capitalización
            cuota_total = 0  # no paga nada
        elif gracia_tipo == "parcial" and k <= gracia_meses:
            amort = 0
            cuota_capital = interes
            cuota_total = interes + seg_desgrav + seg_veh + portes
            saldo = saldo  # saldo no cambia
        else:
            amort = cuota_base - interes
            cuota_capital = cuota_base
            saldo = saldo - amort
            cuota_total = cuota_base + seg_desgrav + seg_veh + portes

        if saldo < 0.001:
            saldo = 0

        filas.append({
            "periodo": k,
            "saldo_inicial": round(saldo + amort if gracia_tipo != "total" else saldo / (1+tem) if k <= gracia_meses else saldo + amort, 4),
            "interes": round(interes, 4),
            "amort": round(amort, 4),
            "cuota_capital": round(cuota_capital, 4),
            "seg_desgrav": round(seg_desgrav, 4),
            "seg_veh": round(seg_veh, 4),
            "portes": round(portes, 4),
            "cuota_total": round(cuota_total, 4),
            "saldo_final": round(saldo, 4),
        })
        flujos.append(-cuota_total)

    # Recalcular saldo_inicial correctamente
    s = sf
    for f in filas:
        f["saldo_inicial"] = round(s, 4)
        if f["period"] if False else True:
            k = f["periodo"]
            if gracia_tipo == "total" and k <= gracia_meses:
                s = s * (1 + tem)
            else:
                s = f["saldo_final"]

    # Indicadores
    van = sum(flujos[t] / (1+tem)**t for t in range(len(flujos)))
    tir_mensual = calcular_tir(flujos)
    tcea = (1 + tir_mensual) ** 12 - 1

    return filas, round(van, 2), round(tir_mensual * 100, 6), round(tcea * 100, 4)

def generar_cronograma_v2(sf, tem, n, gracia_tipo, gracia_meses, tsd, tsv, vv, portes):
    """Clean reimplementation"""
    filas = []
    flujos = [sf]

    n_activo = n - gracia_meses

    if gracia_tipo == "total":
        sc = sf * (1 + tem) ** gracia_meses
    else:
        sc = sf

    if n_activo > 0:
        cuota_base = (sc * tem) / (1 - (1+tem)**(-n_activo))
    else:
        cuota_base = 0

    saldo = sf

    for k in range(1, n+1):
        s_ini = saldo
        interes = s_ini * tem
        seg_desgrav = s_ini * tsd
        seg_veh = vv * tsv

        if gracia_tipo == "total" and k <= gracia_meses:
            amort = 0
            cuota_capital = 0
            cuota_total = 0
            saldo = s_ini * (1 + tem)
        elif gracia_tipo == "parcial" and k <= gracia_meses:
            amort = 0
            cuota_capital = interes
            cuota_total = interes + seg_desgrav + seg_veh + portes
            saldo = s_ini
        else:
            amort = cuota_base - interes
            cuota_capital = cuota_base
            cuota_total = cuota_base + seg_desgrav + seg_veh + portes
            saldo = s_ini - amort

        if saldo < 0.01:
            saldo = 0

        filas.append({
            "periodo": k,
            "saldo_inicial": round(s_ini, 2),
            "interes": round(interes, 2),
            "amort": round(amort, 2),
            "cuota_capital": round(cuota_capital, 2),
            "seg_desgrav": round(seg_desgrav, 2),
            "seg_veh": round(seg_veh, 2),
            "portes": round(portes, 2),
            "cuota_total": round(cuota_total, 2),
            "saldo_final": round(saldo, 2),
        })
        flujos.append(-cuota_total)

    van = sum(flujos[t] / (1+tem)**t for t in range(len(flujos)))
    tir_mensual = calcular_tir(flujos)
    tcea = (1 + tir_mensual) ** 12 - 1

    return filas, round(van, 2), round(tir_mensual * 100, 6), round(tcea * 100, 4)

# ─────────────────────────────────────────────
# SIMULADOR / CRÉDITOS
# ─────────────────────────────────────────────
@app.route("/creditos/nuevo", methods=["GET","POST"])
@login_required
def credito_nuevo():
    db = get_db()
    clientes = db.execute("SELECT id, nombres||' '||apellidos as nombre FROM clientes ORDER BY nombres").fetchall()
    if request.method == "POST":
        f = request.form
        cid = int(f["cliente_id"])
        vid = int(f["vehiculo_id"])
        vv = float(f["precio_vehiculo"])
        ci_pct = float(f["cuota_inicial_pct"])
        ci_monto = vv * ci_pct / 100
        sf = vv - ci_monto
        tipo_tasa = f["tipo_tasa"]
        tasa_valor = float(f["tasa_valor"])
        cap = f.get("capitalizacion", "mensual")
        tem = calcular_tem(tipo_tasa, tasa_valor, cap)
        plazo = int(f["plazo_meses"])
        gracia_tipo = f["gracia_tipo"]
        gracia_meses = int(f["gracia_meses"])
        tsd = float(f["tsd"]) / 100
        tsv = float(f["tsv"]) / 100
        portes = float(f["portes"])
        moneda = f["moneda"]

        cronograma, van, tir, tcea = generar_cronograma_v2(
            sf, tem, plazo, gracia_tipo, gracia_meses, tsd, tsv, vv, portes
        )

        db.execute("""
            INSERT INTO creditos(cliente_id,vehiculo_id,moneda,precio_vehiculo,cuota_inicial_pct,
            cuota_inicial_monto,saldo_financiado,tipo_tasa,tasa_valor,capitalizacion,tem,
            plazo_meses,gracia_tipo,gracia_meses,tsd,tsv,portes,tcea,van,tir,cronograma)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (cid, vid, moneda, vv, ci_pct, ci_monto, sf, tipo_tasa, tasa_valor, cap,
              tem, plazo, gracia_tipo, gracia_meses, tsd*100, tsv*100, portes, tcea, van, tir,
              json.dumps(cronograma)))
        db.commit()
        flash("Crédito calculado y guardado.", "success")
        return redirect(url_for("creditos"))

    return render_template("credito_form.html", clientes=clientes, titulo="Nueva Oferta de Crédito")

@app.route("/api/vehiculos/<int:cid>")
@login_required
def api_vehiculos(cid):
    db = get_db()
    rows = db.execute("SELECT id, marca||' '||modelo as nombre, precio FROM vehiculos WHERE cliente_id=?", (cid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/calcular", methods=["POST"])
@login_required
def api_calcular():
    d = request.get_json()
    vv = float(d["precio_vehiculo"])
    ci_pct = float(d["cuota_inicial_pct"])
    ci_monto = vv * ci_pct / 100
    sf = vv - ci_monto
    tem = calcular_tem(d["tipo_tasa"], float(d["tasa_valor"]), d.get("capitalizacion","mensual"))
    plazo = int(d["plazo_meses"])
    gracia_tipo = d.get("gracia_tipo","ninguno")
    gracia_meses = int(d.get("gracia_meses", 0))
    tsd = float(d["tsd"]) / 100
    tsv = float(d["tsv"]) / 100
    portes = float(d["portes"])

    cronograma, van, tir, tcea = generar_cronograma_v2(
        sf, tem, plazo, gracia_tipo, gracia_meses, tsd, tsv, vv, portes
    )
    tea = round(((1+tem)**12 - 1)*100, 4)
    return jsonify({
        "sf": round(sf, 2),
        "ci_monto": round(ci_monto, 2),
        "tem": round(tem*100, 6),
        "tea": tea,
        "van": van,
        "tir": tir,
        "tcea": tcea,
        "cronograma": cronograma
    })

@app.route("/creditos")
@login_required
def creditos():
    db = get_db()
    rows = db.execute("""
        SELECT cr.id, cl.nombres||' '||cl.apellidos as cliente,
               v.marca||' '||v.modelo as vehiculo,
               cr.moneda, cr.saldo_financiado, cr.plazo_meses,
               cr.tcea, cr.van, cr.tir, cr.created_at
        FROM creditos cr
        JOIN clientes cl ON cr.cliente_id=cl.id
        JOIN vehiculos v ON cr.vehiculo_id=v.id
        ORDER BY cr.created_at DESC
    """).fetchall()
    return render_template("creditos.html", creditos=rows)

@app.route("/creditos/<int:crid>")
@login_required
def credito_detalle(crid):
    db = get_db()
    credito = db.execute("""
        SELECT cr.*, cl.nombres||' '||cl.apellidos as cliente_nombre,
               cl.dni, cl.email, cl.telefono,
               v.marca, v.modelo, v.anio
        FROM creditos cr
        JOIN clientes cl ON cr.cliente_id=cl.id
        JOIN vehiculos v ON cr.vehiculo_id=v.id
        WHERE cr.id=?
    """, (crid,)).fetchone()
    if not credito:
        return redirect(url_for("creditos"))
    cron = json.loads(credito["cronograma"])
    return render_template("credito_detalle.html", credito=credito, cronograma=cron)

@app.route("/creditos/<int:crid>/editar", methods=["GET","POST"])
@login_required
def credito_editar(crid):
    db = get_db()
    credito = db.execute("SELECT * FROM creditos WHERE id=?", (crid,)).fetchone()
    clientes = db.execute("SELECT id, nombres||' '||apellidos as nombre FROM clientes ORDER BY nombres").fetchall()
    if request.method == "POST":
        f = request.form
        vv = float(f["precio_vehiculo"])
        ci_pct = float(f["cuota_inicial_pct"])
        ci_monto = vv * ci_pct / 100
        sf = vv - ci_monto
        tipo_tasa = f["tipo_tasa"]
        tasa_valor = float(f["tasa_valor"])
        cap = f.get("capitalizacion","mensual")
        tem = calcular_tem(tipo_tasa, tasa_valor, cap)
        plazo = int(f["plazo_meses"])
        gracia_tipo = f["gracia_tipo"]
        gracia_meses = int(f["gracia_meses"])
        tsd = float(f["tsd"]) / 100
        tsv = float(f["tsv"]) / 100
        portes = float(f["portes"])
        moneda = f["moneda"]

        cronograma, van, tir, tcea = generar_cronograma_v2(
            sf, tem, plazo, gracia_tipo, gracia_meses, tsd, tsv, vv, portes
        )
        db.execute("""
            UPDATE creditos SET moneda=?,precio_vehiculo=?,cuota_inicial_pct=?,cuota_inicial_monto=?,
            saldo_financiado=?,tipo_tasa=?,tasa_valor=?,capitalizacion=?,tem=?,plazo_meses=?,
            gracia_tipo=?,gracia_meses=?,tsd=?,tsv=?,portes=?,tcea=?,van=?,tir=?,cronograma=?
            WHERE id=?
        """, (moneda, vv, ci_pct, ci_monto, sf, tipo_tasa, tasa_valor, cap, tem, plazo,
              gracia_tipo, gracia_meses, tsd*100, tsv*100, portes, tcea, van, tir,
              json.dumps(cronograma), crid))
        db.commit()
        flash("Crédito recalculado y actualizado.", "success")
        return redirect(url_for("credito_detalle", crid=crid))

    return render_template("credito_form.html", clientes=clientes, credito=credito, titulo="Editar Crédito")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
