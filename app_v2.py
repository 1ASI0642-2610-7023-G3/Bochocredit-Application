from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, json, math, functools, os

app = Flask(__name__)
app.secret_key = "bochocredit_secret_2026"

DB = "bochocredit_db.db"

# ─────────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        # Clean recreate tables that might have wrong schemas or are empty and need seeding
        db.executescript("""
        DROP TABLE IF EXISTS simulaciones;
        DROP TABLE IF EXISTS pagos;
        DROP TABLE IF EXISTS usuarios;
        DROP TABLE IF EXISTS roles;
        """)
        db.executescript("""
        pragma foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_rol TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo TEXT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1,
            id_rol INTEGER,
            FOREIGN KEY (id_rol) REFERENCES roles (id)
        );
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo TEXT NOT NULL,
            dni TEXT UNIQUE NOT NULL,
            telefono TEXT NOT NULL,
            email TEXT NOT NULL,
            direccion TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            anio INTEGER NOT NULL,
            precio REAL NOT NULL,
            descripcion TEXT,
            disponibilidad TEXT NOT NULL DEFAULT 'DISPONIBLE'
        );
        CREATE TABLE IF NOT EXISTS bancos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            razon_social TEXT NOT NULL,
            ruc TEXT NOT NULL,
            direccion TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS tasas_interes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_tasa TEXT NOT NULL,
            tasa_interes REAL DEFAULT 0.1,
            dias_capitalizacion INTEGER NOT NULL DEFAULT 1,
            dias_tasa INTEGER NOT NULL DEFAULT 360
        );
        CREATE TABLE IF NOT EXISTS simulaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tcea REAL NOT NULL,
            van REAL NOT NULL,
            tir REAL NOT NULL,
            saldo_financiado REAL NOT NULL,
            
            plazo_meses INTEGER NOT NULL,
            cantidad_cuotas INTEGER NOT NULL,
            porc_cuota_inicial REAL NOT NULL,
            tipo_periodo_gracia TEXT NOT NULL,
            periodo_gracia_meses REAL NOT NULL DEFAULT 0,
            tipo_moneda TEXT NOT NULL,
            es_elegido TEXT NOT NULL DEFAULT 'NO',
            creado_en TEXT DEFAULT (datetime('now','localtime')),
            id_usuario INTEGER NOT NULL,
            id_cliente INTEGER NOT NULL,
            id_vehiculo INTEGER NOT NULL,
            id_banco INTEGER NOT NULL,
            id_tasa INTEGER NOT NULL,
            
            moneda TEXT,
            precio_vehiculo REAL,
            cuota_inicial_pct REAL,
            cuota_inicial_monto REAL,
            tipo_tasa TEXT,
            tasa_valor REAL,
            capitalizacion TEXT,
            tem REAL,
            gracia_tipo TEXT,
            gracia_meses INTEGER,
            tsd REAL,
            tsv REAL,
            portes REAL,
            cronograma TEXT,
            
            FOREIGN KEY(id_cliente) REFERENCES clientes(id),
            FOREIGN KEY(id_usuario) REFERENCES usuarios(id),
            FOREIGN KEY(id_vehiculo) REFERENCES vehiculos(id),
            FOREIGN KEY(id_banco) REFERENCES bancos(id),
            FOREIGN KEY(id_tasa) REFERENCES tasas_interes(id)
        );
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_cuota INTEGER NOT NULL DEFAULT 0,
            tipo_tasa TEXT NOT NULL,
            tasa_interes REAL DEFAULT 0.1,
            dias_capitalizacion INTEGER NOT NULL DEFAULT 1,
            dias_tasa INTEGER NOT NULL DEFAULT 360,
            fecha_pago TEXT DEFAULT (datetime('now','localtime')),
            tipo_gracia TEXT NOT NULL DEFAULT 'S',
            esta_pagado INTEGER NOT NULL DEFAULT 0,
            
            saldo_inicial_cf REAL NOT NULL,
            interes_cf REAL NOT NULL,
            amortizacion_cf REAL NOT NULL,
            seguro_desgravamen_cf REAL NOT NULL,
            saldo_final_cf REAL NOT NULL,
            
            saldo_inicial REAL NOT NULL,
            interes REAL NOT NULL,
            amortizacion REAL NOT NULL,
            seguro_desgravamen REAL NOT NULL,
            
            seguro_riesgo REAL NOT NULL,
            portes REAL NOT NULL,
            gastos_admin REAL NOT NULL,
            
            saldo_final REAL NOT NULL,
            flujo REAL NOT NULL,
            id_simulacion INTEGER NOT NULL,
            FOREIGN KEY(id_simulacion) REFERENCES simulaciones(id)
        );
        """)
        # seed data
        try:
            db.execute("INSERT OR IGNORE INTO roles(id, nombre_rol) VALUES(?,?)", (1, "ADMIN"))
            db.execute("INSERT OR IGNORE INTO roles(id, nombre_rol) VALUES(?,?)", (2, "USER"))
            db.execute("INSERT OR IGNORE INTO usuarios(id, username, password, nombre_completo, email, id_rol) VALUES(?,?,?,?,?,?)",
                (1, "admin", generate_password_hash("admin123"), "Administrador", "admin@bochocredit.com", 1))
            db.execute("INSERT OR IGNORE INTO bancos(id, nombre, razon_social, ruc, direccion, activo) VALUES(?,?,?,?,?,?)",
                (1, "Banco General", "Banco General S.A.", "20123456789", "Av. Principal 123", 1))
            db.execute("INSERT OR IGNORE INTO tasas_interes(id, tipo_tasa, tasa_interes, dias_capitalizacion, dias_tasa) VALUES(?,?,?,?,?)",
                (1, "efectiva_anual", 15.0, 30, 360))
            db.commit()
        except Exception as e:
            print("Error seeding database:", e)

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
        user = db.execute("SELECT * FROM usuarios WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user["password"], p):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["nombre"] = user["nombre_completo"]
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
        "creditos": db.execute("SELECT COUNT(*) as c FROM simulaciones WHERE es_elegido = 'SI'").fetchone()["c"],
        "vehiculos": db.execute("SELECT COUNT(*) as c FROM vehiculos").fetchone()["c"],
    }
    recientes = db.execute("""
        SELECT sim.id, REPLACE(cl.nombre_completo, ';', ' ') as cliente,
               sim.moneda, sim.saldo_financiado, sim.tcea, sim.creado_en as created_at
        FROM simulaciones sim JOIN clientes cl ON sim.id_cliente = cl.id
        WHERE es_elegido = 'SI'
        ORDER BY sim.creado_en DESC LIMIT 5
    """).fetchall()
    return render_template("dashboard.html", stats=stats, recientes=recientes)

# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────
@app.route("/clientes")
@login_required
def clientes():
    db = get_db()
    rows = db.execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()
    return render_template("clientes.html", clientes=rows)

@app.route("/clientes/nuevo", methods=["GET","POST"])
@login_required
def cliente_nuevo():
    if request.method == "POST":
        f = request.form
        try:
            db = get_db()
            db.execute("INSERT INTO clientes(nombre_completo, dni,telefono,email,direccion) VALUES(?,?,?,?,?)",
                (f["nombres"] + ';' + f["apellidos"], f["dni"], f["telefono"], f["email"], f["direccion"]))
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
        nombre_completo = f["nombres"] + ';' + f["apellidos"]
        db.execute("UPDATE clientes SET nombre_completo=?,dni=?,telefono=?,email=?,direccion=? WHERE id=?",
            (nombre_completo, f["dni"], f["telefono"], f["email"], f["direccion"], cid))
        db.commit()
        flash("Cliente actualizado.", "success")
        return redirect(url_for("clientes"))
    
    # Convert Row to dict and unpack nombres/apellidos for the template
    cliente_dict = dict(cliente)
    nombres = ""
    apellidos = ""
    if cliente["nombre_completo"] and ";" in cliente["nombre_completo"]:
        parts = cliente["nombre_completo"].split(";")
        nombres = parts[0]
        apellidos = parts[1] if len(parts) > 1 else ""
    else:
        nombres = cliente["nombre_completo"] or ""
    cliente_dict["nombres"] = nombres
    cliente_dict["apellidos"] = apellidos
    
    return render_template("cliente_form.html", cliente=cliente_dict, titulo="Editar Cliente")

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
    if not cliente:
        return redirect(url_for("clientes"))
    
    cliente_dict = dict(cliente)
    nombres = ""
    apellidos = ""
    if cliente["nombre_completo"] and ";" in cliente["nombre_completo"]:
        parts = cliente["nombre_completo"].split(";")
        nombres = parts[0]
        apellidos = parts[1] if len(parts) > 1 else ""
    else:
        nombres = cliente["nombre_completo"] or ""
    cliente_dict["nombres"] = nombres
    cliente_dict["apellidos"] = apellidos

    vehiculos = db.execute("""
        SELECT DISTINCT v.*
        FROM vehiculos v
        JOIN simulaciones sim ON sim.id_vehiculo = v.id
        WHERE sim.id_cliente = ?
    """, (cid,)).fetchall()

    creditos = db.execute("""
        SELECT sim.id, v.marca||' '||v.modelo as vehiculo,
               sim.moneda, sim.saldo_financiado, sim.tcea
        FROM simulaciones sim
        JOIN vehiculos v ON sim.id_vehiculo = v.id
        WHERE sim.id_cliente = ?
        ORDER BY sim.creado_en DESC
    """, (cid,)).fetchall()
    return render_template("cliente_detalle.html", cliente=cliente_dict, vehiculos=vehiculos, creditos=creditos)











# ─────────────────────────────────────────────
# VEHÍCULOS
# ─────────────────────────────────────────────
@app.route("/vehiculos")
@login_required
def vehiculos():
    db = get_db()
    rows = db.execute("""
        SELECT *
        FROM vehiculos
        ORDER BY id DESC
    """).fetchall()
    return render_template("vehiculos.html", vehiculos=rows)


@app.route("/vehiculos/nuevo", methods=["GET","POST"])
@login_required
def vehiculo_nuevo():
    db = get_db()
    if request.method == "POST":
        f = request.form
        db.execute("INSERT INTO vehiculos(marca,modelo,anio,precio,descripcion) VALUES(?,?,?,?,?)",
            (f["marca"], f["modelo"], f["anio"], f["precio"], f["descripcion"]))
        db.commit()
        flash("Vehículo registrado.", "success")
        return redirect(url_for("vehiculos"))
    return render_template("vehiculo_form.html", vehiculo=None, titulo="Nuevo Vehículo")

@app.route("/vehiculos/<int:vid>/editar", methods=["GET","POST"])
@login_required
def vehiculo_editar(vid):
    db = get_db()
    vehiculo = db.execute("SELECT * FROM vehiculos WHERE id=?", (vid,)).fetchone()
    if request.method == "POST":
        f = request.form
        db.execute("UPDATE vehiculos SET marca=?,modelo=?,anio=?,precio=?,descripcion=?, disponibilidad=? WHERE id=?",
            (f["marca"], f["modelo"], f["anio"], f["precio"], f["descripcion"], f["disponibilidad"], vid))
        db.commit()
        flash("Vehículo actualizado.", "success")
        return redirect(url_for("vehiculos"))
    return render_template("vehiculo_form.html", vehiculo=vehiculo, titulo="Editar Vehículo")




# ─────────────────────────────────────────────
# CÁLCULO FINANCIERO
# ─────────────────────────────────────────────
def calcular_tem(tipo_tasa, tasa_valor, capitalizacion, dias_tasa=360):
    tasa = tasa_valor / 100
    
    # Map capitalizacion string to days if it's a string
    cap_days = 30
    if isinstance(capitalizacion, str):
        cap_map = {
            "diaria": 1,
            "quincenal": 15,
            "mensual": 30,
            "bimestral": 60,
            "trimestral": 90,
            "cuatrimestral": 120,
            "semestral": 180,
            "anual": 360
        }
        cap_days = cap_map.get(capitalizacion, 30)
    else:
        cap_days = capitalizacion
        
    n = 30 / cap_days

    if 'efectiva_mensual' in tipo_tasa:
        return tasa
    elif 'efectiva_anual' in tipo_tasa:
        return (1 + tasa) ** (1/12) - 1
    else:
        # nominal_anual
        m = dias_tasa / cap_days
        return (1 + tasa / m) ** n - 1


# revisar por si acaso
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



# borrar si no se usa
def generar_cronograma(sf, tem, n_cuotas, gracia_tipo, gracia_meses, tsd, tsv, vv, portes):
    filas = []
    saldo = sf

    # Cuota base para período activo
    n_activo = n_cuotas - gracia_meses
    if gracia_tipo == "total":
        sc = sf * (1 + tem) ** gracia_meses
        cuota_base = (sc * tem) / (1 - (1+tem)**(-n_activo))
    else:
        sc = sf
        cuota_base = (sf * tem) / (1 - (1+tem)**(-n_activo)) if n_activo > 0 else 0

    flujos = [sf]  # flujo inicial positivo (desembolso recibido)

    for k in range(0, n_cuotas+1):
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


# deprecado, borrar cuando lo migren al otro (el de abajo)
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


def generar_cronograma_compra_inteligente(sf, tem, n, gracia_tipo, gracia_meses,
                                          tsd, tsv, vv, gastos, pct_cuota_final, cok):
    # Método francés vencido + Compra Inteligente con cuota final y costo de oportunidad.

    filas = []
    flujos = [sf]

    # Cuotón (porcentaje del saldo financiado)
    cuoton = sf * pct_cuota_final

    # Saldo regular (para cuotas mensuales)
    saldo_regular = sf - cuoton

    # Ajuste por gracia
    n_activo = n - gracia_meses
    if gracia_tipo == "total":
        sc = saldo_regular * (1 + tem) ** gracia_meses
    else:
        sc = saldo_regular

    # Cuota base (francés vencido sobre saldo regular)
    cuota_base = (sc * tem) / (1 - (1 + tem) ** (-n_activo)) if n_activo > 0 else 0

    saldo = saldo_regular
    saldo_cf = cuoton  # saldo de la cuota final

    for k in range(1, n + 1):
        # Regular
        s_ini = saldo
        interes = s_ini * tem
        seg_desgrav = s_ini * tsd
        seg_veh = vv * tsv
        portes = gastos.get("portes", 0)
        g_admin = gastos.get("gastos_admin", 0)
        g_period = gastos.get("gastos_periodicos", 0)

        # Cuota final (se acumula interés y seguros, amortización=0 hasta el último periodo)
        interes_cf = saldo_cf * tem
        seg_desgrav_cf = saldo_cf * tsd
        saldo_cf = saldo_cf * (1 + tem)  # se capitaliza interés

        if gracia_tipo == "total" and k <= gracia_meses:
            amort = 0
            cuota_total = 0
            saldo = s_ini * (1 + tem)
            pg = "T"
        elif gracia_tipo == "parcial" and k <= gracia_meses:
            amort = 0
            cuota_total = interes + seg_desgrav + seg_veh + portes + g_admin + g_period
            saldo = s_ini
            pg = "P"
        else:
            amort = cuota_base - interes
            cuota_total = cuota_base + seg_desgrav + seg_veh + portes + g_admin + g_period
            saldo = s_ini - amort
            pg = "S"

        if saldo < 0.01:
            saldo = 0

        filas.append({
            "periodo": k,
            "PG": pg,

            # Cronograma cuota final
            "saldo_inicial_cf": round(cuoton, 4),
            "interes_cf": round(interes_cf, 4),
            "amortizacion_cf": 0,
            "seguro_desgravamen_cf": round(seg_desgrav_cf, 4),
            "saldo_final_cf": round(saldo_cf, 4),

            # Cronograma regular
            "saldo_inicial": round(s_ini, 4),
            "interes": round(interes, 4),
            "amortizacion": round(amort, 4),
            "seguro_desgravamen": round(seg_desgrav, 4),
            "seguro_riesgo": round(seg_veh, 4),
            "portes": round(portes, 4),
            "gastos_admin": round(g_admin, 4),
            "gastos_periodicos": round(g_period, 4),
            "cuota_total": round(cuota_total, 4),
            "saldo_final": round(saldo, 4),
        })
        flujos.append(-cuota_total)

    # Cuotón final (periodo n+1)
    filas.append({
        "periodo": n + 1,
        "PG": "S",

        # Cronograma cuota final (se paga todo aquí)
        "saldo_inicial_cf": round(saldo_cf, 4),
        "interes_cf": 0,
        "amortizacion_cf": round(saldo_cf, 4),
        "seguro_desgravamen_cf": 0,
        "saldo_final_cf": 0,

        # Cronograma regular (no aplica)
        "saldo_inicial": 0,
        "interes": 0,
        "amortizacion": 0,
        "seguro_desgravamen": 0,
        "seguro_riesgo": 0,
        "portes": 0,
        "gastos_admin": 0,
        "gastos_periodicos": 0,
        "cuota_total": round(saldo_cf, 4),
        "saldo_final": 0,
    })
    flujos.append(-saldo_cf)

    # Conversión del COK anual a TEM
    tem_cok = (1 + cok) ** (1 / 12) - 1

    # VAN con costo de oportunidad
    van = sum(flujos[t] / (1 + tem_cok) ** t for t in range(len(flujos)))

    # TIR y TCEA
    tir_mensual = calcular_tir(flujos)
    tcea = (1 + tir_mensual) ** 12 - 1

    return filas, round(van, 4), round(tir_mensual * 100, 6), round(tcea * 100, 4)


# ─────────────────────────────────────────────
# SIMULADOR / CRÉDITOS
# ─────────────────────────────────────────────
@app.route("/creditos/nuevo", methods=["GET","POST"])
@login_required
def credito_nuevo():
    db = get_db()
    c_rows = db.execute("SELECT id, nombre_completo FROM clientes ORDER BY nombre_completo").fetchall()
    clientes = []
    for r in c_rows:
        nombre = r["nombre_completo"].replace(";", " ") if r["nombre_completo"] else ""
        clientes.append({"id": r["id"], "nombre": nombre})

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

        cursor = db.execute("""
            INSERT INTO simulaciones(
                tcea, van, tir, saldo_financiado, plazo_meses, cantidad_cuotas,
                porc_cuota_inicial, tipo_periodo_gracia, periodo_gracia_meses,
                tipo_moneda, es_elegido, id_usuario, id_cliente, id_vehiculo,
                id_banco, id_tasa, moneda, precio_vehiculo, cuota_inicial_pct,
                cuota_inicial_monto, tipo_tasa, tasa_valor, capitalizacion, tem,
                gracia_tipo, gracia_meses, tsd, tsv, portes, cronograma
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            tcea, van, tir, sf, plazo, plazo,
            ci_pct, gracia_tipo, gracia_meses, moneda, 'SI',
            session["user_id"], cid, vid, 1, 1,
            moneda, vv, ci_pct, ci_monto, tipo_tasa, tasa_valor, cap, tem,
            gracia_tipo, gracia_meses, tsd*100, tsv*100, portes, json.dumps(cronograma)
        ))
        sim_id = cursor.lastrowid

        for row in cronograma:
            db.execute("""
                INSERT INTO pagos(
                    num_cuota, tipo_tasa, tasa_interes, dias_capitalizacion, dias_tasa,
                    tipo_gracia, esta_pagado, saldo_inicial_cf, interes_cf, amortizacion_cf,
                    seguro_desgravamen_cf, saldo_final_cf, saldo_inicial, interes, amortizacion,
                    seguro_desgravamen, seguro_riesgo, portes, gastos_admin, saldo_final, flujo,
                    id_simulacion
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["periodo"], tipo_tasa, tasa_valor, 30, 360,
                gracia_tipo, 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                row["saldo_inicial"], row["interes"], row["amort"],
                row["seg_desgrav"], row["seg_veh"], row["portes"], 0.0,
                row["saldo_final"], -row["cuota_total"], sim_id
            ))
        db.commit()
        flash("Crédito calculado y guardado.", "success")
        return redirect(url_for("creditos"))

    return render_template("credito_form.html", clientes=clientes, titulo="Nueva Oferta de Crédito")

@app.route("/api/vehiculos/<int:cid>")
@login_required
def api_vehiculos(cid):
    db = get_db()
    rows = db.execute("SELECT id, marca||' '||modelo as nombre, precio FROM vehiculos").fetchall()
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
        SELECT sim.id, cl.nombre_completo as cliente,
               v.marca||' '||v.modelo as vehiculo,
               sim.moneda, sim.saldo_financiado, sim.plazo_meses,
               sim.tcea, sim.van, sim.tir, sim.creado_en as created_at
        FROM simulaciones sim
        JOIN clientes cl ON sim.id_cliente=cl.id
        JOIN vehiculos v ON sim.id_vehiculo=v.id
        ORDER BY sim.creado_en DESC
    """).fetchall()
    
    creditos_list = []
    for r in rows:
        c_dict = dict(r)
        if c_dict["cliente"]:
            c_dict["cliente"] = c_dict["cliente"].replace(";", " ")
        creditos_list.append(c_dict)
        
    return render_template("creditos.html", creditos=creditos_list)

@app.route("/creditos/<int:crid>")
@login_required
def credito_detalle(crid):
    db = get_db()
    row = db.execute("""
        SELECT sim.*, sim.creado_en as created_at,
               cl.nombre_completo as cliente_nombre, cl.dni, cl.email, cl.telefono,
               v.marca, v.modelo, v.anio
        FROM simulaciones sim
        JOIN clientes cl ON sim.id_cliente=cl.id
        JOIN vehiculos v ON sim.id_vehiculo=v.id
        WHERE sim.id=?
    """, (crid,)).fetchone()
    if not row:
        return redirect(url_for("creditos"))
    
    credito = dict(row)
    if credito["cliente_nombre"]:
        credito["cliente_nombre"] = credito["cliente_nombre"].replace(";", " ")
        
    cron = json.loads(credito["cronograma"])
    return render_template("credito_detalle.html", credito=credito, cronograma=cron)

@app.route("/creditos/<int:crid>/editar", methods=["GET","POST"])
@login_required
def credito_editar(crid):
    db = get_db()
    row = db.execute("SELECT * FROM simulaciones WHERE id=?", (crid,)).fetchone()
    if not row:
        return redirect(url_for("creditos"))
    
    credito = dict(row)
    credito["cliente_id"] = row["id_cliente"]
    credito["vehiculo_id"] = row["id_vehiculo"]
    
    c_rows = db.execute("SELECT id, nombre_completo FROM clientes ORDER BY nombre_completo").fetchall()
    clientes = []
    for r in c_rows:
        nombre = r["nombre_completo"].replace(";", " ") if r["nombre_completo"] else ""
        clientes.append({"id": r["id"], "nombre": nombre})

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
            UPDATE simulaciones SET
                tcea=?, van=?, tir=?, saldo_financiado=?, plazo_meses=?, cantidad_cuotas=?,
                porc_cuota_inicial=?, tipo_periodo_gracia=?, periodo_gracia_meses=?,
                tipo_moneda=?, id_cliente=?, id_vehiculo=?, moneda=?, precio_vehiculo=?,
                cuota_inicial_pct=?, cuota_inicial_monto=?, tipo_tasa=?, tasa_valor=?,
                capitalizacion=?, tem=?, gracia_tipo=?, gracia_meses=?, tsd=?, tsv=?,
                portes=?, cronograma=?
            WHERE id=?
        """, (
            tcea, van, tir, sf, plazo, plazo,
            ci_pct, gracia_tipo, gracia_meses, moneda, cid, vid, moneda, vv,
            ci_pct, ci_monto, tipo_tasa, tasa_valor, cap, tem,
            gracia_tipo, gracia_meses, tsd*100, tsv*100, portes, json.dumps(cronograma),
            crid
        ))

        db.execute("DELETE FROM pagos WHERE id_simulacion=?", (crid,))
        for row in cronograma:
            db.execute("""
                INSERT INTO pagos(
                    num_cuota, tipo_tasa, tasa_interes, dias_capitalizacion, dias_tasa,
                    tipo_gracia, esta_pagado, saldo_inicial_cf, interes_cf, amortizacion_cf,
                    seguro_desgravamen_cf, saldo_final_cf, saldo_inicial, interes, amortizacion,
                    seguro_desgravamen, seguro_riesgo, portes, gastos_admin, saldo_final, flujo,
                    id_simulacion
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row["periodo"], tipo_tasa, tasa_valor, 30, 360,
                gracia_tipo, 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                row["saldo_inicial"], row["interes"], row["amort"],
                row["seg_desgrav"], row["seg_veh"], row["portes"], 0.0,
                row["saldo_final"], -row["cuota_total"], crid
            ))
        db.commit()
        flash("Crédito recalculado y actualizado.", "success")
        return redirect(url_for("credito_detalle", crid=crid))

    return render_template("credito_form.html", clientes=clientes, credito=credito, titulo="Editar Crédito")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
