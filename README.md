# Bochocredit Application

Este es el repositorio para la aplicación Bochocredit, un sistema para la gestión y simulación de créditos vehiculares.

## Requisitos Previos

Asegúrate de tener instalado [Python 3.8+](https://www.python.org/) en tu computadora.

## Cómo iniciar el proyecto localmente

Sigue estos pasos para ejecutar la aplicación en tu entorno local por primera vez.

### 1. Clonar el repositorio
Abre tu terminal y clona el proyecto:
```bash
git clone https://github.com/1ASI0642-2610-7023-G3/Bochocredit-Application.git
cd Bochocredit-Application
```

### 2. Crear un Entorno Virtual
Es importante utilizar un entorno virtual para no tener conflictos con otras librerías en tu sistema.
```bash
python -m venv .venv
```

### 3. Activar el Entorno Virtual
Dependiendo de tu sistema operativo, ejecuta el siguiente comando:

- **Windows (PowerShell / VS Code):**
  ```powershell
  .venv\Scripts\activate
  ```
- **Windows (CMD):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Mac / Linux:**
  ```bash
  source .venv/bin/activate
  ```

*(Una vez activado, deberías ver `(.venv)` al inicio de tu línea de comandos).*

### 4. Instalar las Dependencias
Con el entorno virtual activado, instala los requerimientos del proyecto:
```bash
pip install -r requirements.txt
```

### 5. Inicializar la Base de Datos
Dado que la base de datos local (`.db`) no se sube a GitHub (por razones de seguridad y buenas prácticas), deberás inicializarla para que se creen las tablas necesarias antes de iniciar la aplicación.
Puedes hacerlo ejecutando este script de inicialización rápida en tu terminal:
```bash
python -c "from app_v2 import init_db; init_db()"
```

### 6. Iniciar la Aplicación
Finalmente, corre el servidor de Flask:
```bash
python app_v2.py
```

La aplicación estará corriendo y disponible en tu navegador en la siguiente dirección: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.
