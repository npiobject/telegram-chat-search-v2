# 🚂 Guía de Despliegue en Railway - Telegram Chat Search V2.0

## 📋 Índice

- [PASO 6 — Configurar Volume para la BD (Opcional)](#paso-6--configurar-volume-para-la-bd-opcional)
- [PASO 7 — Configurar Variables de Entorno](#paso-7--configurar-variables-de-entorno-en-railway)
- [PASO 8 — Desplegar en Railway](#paso-8--desplegar-en-railway)
- [PASO 9 — Verificar el Despliegue](#paso-9--verificar-el-despliegue)
- [PASO 10 — Problemas Comunes y Soluciones](#paso-10--problemas-comunes-y-soluciones)
- [Resumen de Archivos](#resumen-de-archivos-de-despliegue)

---

## PASO 6 — Configurar Volume para la BD (Opcional)

### 🤔 ¿Necesito un Volume?

**NO es obligatorio** porque la base de datos SQLite (`data/telegram_messages.db`, ~12 MB) ya está **incluida dentro de la imagen Docker** (Estrategia A). Esto significa que al desplegar, la BD ya está lista para usarse.

### ¿Cuándo SÍ necesito un Volume?

Necesitas configurar un **Volume persistente** si:

- ✅ Quieres **actualizar la base de datos** sin reconstruir toda la imagen Docker
- ✅ Quieres que los datos persistan entre redespliegues
- ✅ Planeas **agregar mensajes nuevos** mediante sincronización con Telegram API (funcionalidad futura)
- ✅ Quieres mantener estadísticas de búsqueda o logs persistentes

### ⚠️ Requisito Importante: Plan de Pago

**Los Volumes NO están disponibles en el plan Free Trial de Railway.** Necesitas como mínimo el plan **Hobby ($5/mes)**.

| Plan | Volumes | RAM | Coste |
|------|:-------:|-----|-------|
| Free Trial | ❌ NO | 0.5 GB | $5 crédito único |
| Hobby | ✅ SI | 8 GB | $5/mes |
| Pro | ✅ SI | 32 GB | $20/mes |

---

### 📦 Cómo Configurar un Volume en Railway

#### Paso 6.1: Crear el Volume

1. Ve al **Dashboard de Railway** (https://railway.app)
2. Selecciona tu proyecto (Telegram Chat Search)
3. Haz clic en el **Service** (servicio) que creaste
4. En el menú lateral, selecciona **"Volumes"**
5. Haz clic en el botón **"+ New Volume"**

![Captura: Botón "New Volume" en el panel izquierdo]

6. Configura el volume con estos datos:

| Campo | Valor | Descripción |
|-------|-------|-------------|
| **Name** | `telegram-data` | Nombre descriptivo del volume |
| **Mount Path** | `/app/data` | **CRÍTICO:** Debe coincidir con la ruta en el contenedor |
| **Size** | 1 GB | Más que suficiente para la BD + logs |

7. Haz clic en **"Add"**

#### 📍 ¿Por qué `/app/data`?

En el `Dockerfile`, el `WORKDIR` está configurado como `/app`:

```dockerfile
WORKDIR /app
```

Y la aplicación busca la BD en `data/telegram_messages.db` relativo al directorio de trabajo, que se resuelve como:

```
/app/data/telegram_messages.db
```

Por lo tanto, el **Mount Path** del volume DEBE ser `/app/data` para que la aplicación encuentre la base de datos.

---

#### Paso 6.2: Subir la Base de Datos Inicial al Volume

Una vez creado el volume, necesitas **subir tu base de datos local** al volume en Railway. Hay dos métodos:

##### **Método A: Railway CLI (Recomendado)**

1. **Instala Railway CLI** (si no lo tienes):
   ```bash
   npm install -g @railway/cli
   ```

2. **Autentica tu cuenta**:
   ```bash
   railway login
   ```
   Se abrirá tu navegador para autorizar.

3. **Vincula tu directorio local al proyecto**:
   ```bash
   cd "C:\Users\fsant\C - Desarrollo\Telegram\V2.0"
   railway link
   ```
   Selecciona tu proyecto y servicio de la lista.

4. **Sube la base de datos al volume**:
   ```bash
   railway volume add telegram-data
   railway volume upload telegram-data ./data/telegram_messages.db /telegram_messages.db
   ```

5. **Verifica que se subió correctamente**:
   ```bash
   railway run ls -lh /app/data/
   ```
   Deberías ver el archivo `telegram_messages.db` listado.

##### **Método B: Manual mediante SSH (Alternativo)**

Si prefieres no usar CLI:

1. Ve a **Service → Settings → Volumes**
2. Haz clic en los **tres puntos** (⋮) del volume `telegram-data`
3. Selecciona **"Shell"** (abre una terminal en el contenedor)
4. Usa `wget` o `curl` para descargar la BD desde un servidor temporal:
   ```bash
   cd /app/data
   wget https://tu-servidor-temporal.com/telegram_messages.db
   ```

> ⚠️ **Nota de Seguridad:** NO subas tu base de datos a servidores públicos si contiene información sensible. Usa el Método A con Railway CLI.

---

#### Paso 6.3: Configurar Permisos (Si hay errores)

Si al desplegar ves errores de permisos como:

```
PermissionError: [Errno 13] Permission denied: '/app/data/telegram_messages.db'
```

Agrega esta **variable de entorno** en Railway:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `RAILWAY_RUN_UID` | `0` | Ejecuta el contenedor como root para evitar problemas de permisos |

> ⚠️ **Advertencia de Seguridad:** Ejecutar como root (`UID=0`) no es ideal en producción, pero Railway es un entorno aislado y es aceptable para simplificar permisos. Una alternativa más segura es ajustar los permisos dentro del Dockerfile:

```dockerfile
# En Dockerfile, antes de COPY
RUN mkdir -p /app/data && chmod 777 /app/data
```

---

#### Paso 6.4: Modificar Dockerfile para Usar el Volume (Opcional)

Si decides usar un volume, puedes **comentar** la línea que copia la BD en el Dockerfile para reducir el tamaño de la imagen:

```dockerfile
# COPY data/telegram_messages.db /app/data/telegram_messages.db
```

De esta forma:
- ✅ La BD vive **solo en el volume persistente**
- ✅ La imagen Docker es **más ligera**
- ✅ Puedes actualizar la BD sin reconstruir la imagen

Pero recuerda que necesitarás subir la BD inicial manualmente (Paso 6.2).

---

### ✅ Resumen: ¿Volume Sí o No?

| Escenario | Volume Necesario | Plan Mínimo |
|-----------|:----------------:|-------------|
| Solo lectura, BD estática | ❌ NO | Free Trial |
| Actualizar BD frecuentemente | ✅ SI | Hobby ($5/mes) |
| Sincronización con Telegram API | ✅ SI | Hobby ($5/mes) |
| App de prueba temporal | ❌ NO | Free Trial |

---

## PASO 7 — Configurar Variables de Entorno en Railway

Las **variables de entorno** permiten configurar la aplicación sin modificar el código. Railway las inyecta automáticamente en el contenedor al desplegar.

### 📋 Variables Necesarias

| Variable | Valor Ejemplo | Obligatoria | Notas |
|----------|---------------|:-----------:|-------|
| `OPENROUTER_API_KEY` | `sk-or-v1-xxxxxxxxxxxxx` | ⚠️ SI* | Necesaria para resumenes con IA. Sin ella, la app usa `MockSummarizer` (resumenes de placeholder) |
| `OPENROUTER_MODEL` | `anthropic/claude-3-haiku` | ❌ NO | Modelo por defecto en `config.py`. Alternativas: `anthropic/claude-3.5-sonnet`, `google/gemini-flash-1.5`, `meta-llama/llama-3-70b-instruct` |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | ✅ SI | Ya está en `Dockerfile` como `ENV`, pero mejor configurarla explícitamente |
| `PORT` | **(auto)** | ❌ NO | **NO la configures manualmente.** Railway la inyecta automáticamente (ej: `8080`, `3000`, etc.) |

> **\* Nota sobre `OPENROUTER_API_KEY`:** Técnicamente la app funciona sin ella, pero los resumenes serán textos de placeholder como *"Este es un resumen simulado porque no hay API key configurada"*. Para producción, esta variable es **imprescindible**.

---

### 🔑 Cómo Obtener una API Key de OpenRouter

1. Ve a **https://openrouter.ai**
2. Crea una cuenta (gratis, acepta login con Google/GitHub)
3. Ve a **https://openrouter.ai/keys**
4. Haz clic en **"Create Key"**
5. Dale un nombre (ej: `Telegram Search Bot`)
6. **Copia la key** (empieza con `sk-or-v1-...`)
7. **Agrega créditos** (mínimo $5 USD) en https://openrouter.ai/credits

> 💡 **Tip:** OpenRouter cobra por uso. El modelo `claude-3-haiku` cuesta ~$0.25 por millón de tokens (muy económico). Con $5 puedes generar cientos de resumenes.

---

### ⚙️ Cómo Configurar las Variables en Railway

#### **Opción A: Editor Visual (Recomendado para Principiantes)**

1. Ve al **Dashboard de Railway** (https://railway.app)
2. Selecciona tu proyecto
3. Haz clic en tu **Service**
4. En el menú lateral, selecciona **"Variables"**
5. Haz clic en **"+ New Variable"**
6. Para cada variable:
   - **Variable Name:** `OPENROUTER_API_KEY`
   - **Value:** `sk-or-v1-xxxxxxxxxxxxx`
   - Haz clic en **"Add"**

![Captura: Formulario "New Variable" con campos Name y Value]

7. Repite para las demás variables:
   - `OPENROUTER_MODEL` → `anthropic/claude-3-haiku`
   - `GRADIO_SERVER_NAME` → `0.0.0.0`

8. **NO agregues la variable `PORT`** (Railway la maneja automáticamente)

---

#### **Opción B: RAW Editor (Recomendado para Usuarios Avanzados)**

1. En la pestaña **"Variables"**, haz clic en **"RAW Editor"** (arriba a la derecha)
2. Pega este texto (reemplaza `xxxxx` con tu API key real):

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-3-haiku
GRADIO_SERVER_NAME=0.0.0.0
```

3. Haz clic en **"Update Variables"**

![Captura: RAW Editor con las tres variables en formato clave=valor]

---

### 🔒 Seguridad: NUNCA Subas `.env` a GitHub

Las API keys son **secretos sensibles**. Si las subes a un repositorio público, **cualquiera puede usarlas** y gastar tus créditos.

✅ **Buenas prácticas:**
- ✅ Usa el archivo `.gitignore` para excluir `.env`
- ✅ Configura las variables **solo en Railway Dashboard**
- ✅ Usa variables de entorno diferentes para desarrollo y producción

❌ **NUNCA hagas esto:**
```bash
# ❌ MAL: Commitear el archivo .env
git add .env
git commit -m "Add env vars"
git push
```

✅ **Haz esto en su lugar:**
```bash
# ✅ BIEN: .gitignore ya excluye .env
cat .gitignore
# Salida esperada:
# .env
# .env.local
# ...
```

---

### 🧪 Verificar que las Variables están Configuradas

Después de agregarlas, verifica que Railway las reconoce:

1. En **Service → Variables**, deberías ver 3 variables listadas:
   - `OPENROUTER_API_KEY` → `••••••••••••` (oculta)
   - `OPENROUTER_MODEL` → `anthropic/claude-3-haiku`
   - `GRADIO_SERVER_NAME` → `0.0.0.0`

2. (Opcional) Usa Railway CLI para listarlas:
   ```bash
   railway variables
   ```

   Salida esperada:
   ```
   OPENROUTER_API_KEY=sk-or-v1-xxxxx (hidden)
   OPENROUTER_MODEL=anthropic/claude-3-haiku
   GRADIO_SERVER_NAME=0.0.0.0
   PORT=8080 (injected by Railway)
   ```

---

### 🎯 Modelos Alternativos en OpenRouter

Si quieres usar un modelo diferente, cambia `OPENROUTER_MODEL`:

| Modelo | ID en OpenRouter | Coste Aprox. | Velocidad | Calidad |
|--------|------------------|--------------|-----------|---------|
| Claude 3 Haiku | `anthropic/claude-3-haiku` | $0.25/M tokens | ⚡⚡⚡ Muy rápido | ⭐⭐⭐ Buena |
| Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | $3/M tokens | ⚡⚡ Rápido | ⭐⭐⭐⭐⭐ Excelente |
| Gemini Flash 1.5 | `google/gemini-flash-1.5` | $0.075/M tokens | ⚡⚡⚡ Muy rápido | ⭐⭐⭐⭐ Muy buena |
| Llama 3 70B | `meta-llama/llama-3-70b-instruct` | $0.59/M tokens | ⚡⚡ Moderado | ⭐⭐⭐⭐ Muy buena |
| GPT-4o mini | `openai/gpt-4o-mini` | $0.15/M tokens | ⚡⚡⚡ Rápido | ⭐⭐⭐⭐ Muy buena |

Recomendación: **Claude 3 Haiku** (balance coste/calidad) o **Gemini Flash 1.5** (el más barato y sorprendentemente bueno).

---

## PASO 8 — Desplegar en Railway

Ahora que tienes todo configurado, es momento de **desplegar la aplicación**. Railway ofrece 3 métodos. Elige el que prefieras.

---

### 🎯 Opción A: Desde GitHub (⭐ Recomendada)

Esta es la **forma más profesional** porque:
- ✅ Cada push a GitHub redespliega automáticamente
- ✅ Historial completo de cambios (control de versiones)
- ✅ Fácil de revertir si algo falla
- ✅ Permite colaboración en equipo

---

#### Paso 8.A.1: Crear un Repositorio en GitHub

1. **Ve a GitHub** (https://github.com) e inicia sesión
2. Haz clic en el botón **"New"** (o ve a https://github.com/new)
3. Configura el repositorio:
   - **Repository name:** `telegram-chat-search` (o el nombre que prefieras)
   - **Description:** "Sistema de búsqueda semántica sobre mensajes de Telegram con IA"
   - **Visibility:**
     - ✅ **Private** (recomendado si la BD contiene info sensible)
     - ⚠️ Public (solo si la BD es de prueba)
   - **NO marques** "Add a README file" (ya tienes archivos localmente)
4. Haz clic en **"Create repository"**

![Captura: Formulario de creación de repo con nombre "telegram-chat-search" y visibilidad Private]

---

#### Paso 8.A.2: Subir tu Código Local a GitHub

Abre **Git Bash** o **PowerShell** en tu directorio del proyecto:

```bash
cd "C:\Users\fsant\C - Desarrollo\Telegram\V2.0"
```

##### **Si es tu primer commit** (repositorio nuevo):

```bash
# Inicializar Git (si no lo hiciste antes)
git init

# Agregar todos los archivos (respetando .gitignore)
git add .

# Crear el commit inicial
git commit -m "Initial commit: Telegram Chat Search V2.0 for Railway"

# Vincular al repo de GitHub (reemplaza USERNAME con tu usuario)
git remote add origin https://github.com/USERNAME/telegram-chat-search.git

# Renombrar rama a 'main' (estándar de GitHub)
git branch -M main

# Subir todo a GitHub
git push -u origin main
```

> 🔑 **Autenticación:** GitHub te pedirá credenciales. Usa un **Personal Access Token** (no tu contraseña). Créalo en: https://github.com/settings/tokens

##### **Si ya tienes commits locales:**

```bash
# Simplemente conecta y sube
git remote add origin https://github.com/USERNAME/telegram-chat-search.git
git branch -M main
git push -u origin main
```

---

#### Paso 8.A.3: Verificar que se Subió Correctamente

1. Ve a tu repositorio en GitHub (https://github.com/USERNAME/telegram-chat-search)
2. Deberías ver todos los archivos:
   - ✅ `app.py`
   - ✅ `Dockerfile`
   - ✅ `railway.toml`
   - ✅ `requirements-prod.txt`
   - ✅ `telegram_chat_search/` (directorio con el código)
   - ✅ `data/telegram_messages.db` (si no usas volume)
   - ❌ **NO debe haber:** `.env`, `chats/`, `temp_hf/`, `__pycache__/`

Si ves archivos que no deberían estar, agrégalos a `.gitignore` y haz:
```bash
git rm --cached archivo-no-deseado
git commit -m "Remove sensitive files"
git push
```

---

#### Paso 8.A.4: Desplegar desde GitHub en Railway

1. Ve al **Dashboard de Railway** (https://railway.app)
2. Haz clic en **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**

![Captura: Opciones "Empty Project", "Deploy from GitHub repo", "Deploy from template"]

4. **Autoriza Railway** a acceder a GitHub (si es la primera vez)
   - Haz clic en **"Configure GitHub App"**
   - Selecciona tu cuenta/organización
   - Dale acceso al repositorio `telegram-chat-search`

5. Selecciona el repositorio de la lista:
   - Busca `USERNAME/telegram-chat-search`
   - Haz clic en **"Deploy Now"**

6. Railway automáticamente:
   - ✅ Detecta el `Dockerfile`
   - ✅ Configura el builder como `DOCKERFILE` (lee `railway.toml`)
   - ✅ Comienza a construir la imagen Docker

![Captura: Railway mostrando "Detected Dockerfile" y "Building..."]

---

#### Paso 8.A.5: Configurar Variables de Entorno

**Mientras se construye** (o después), configura las variables de entorno:

1. En el panel del Service, ve a **"Variables"**
2. Agrega las variables del **PASO 7**:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-xxxxx
   OPENROUTER_MODEL=anthropic/claude-3-haiku
   GRADIO_SERVER_NAME=0.0.0.0
   ```
3. Railway **reiniciará el despliegue** automáticamente

---

#### Paso 8.A.6: Esperar el Build y Deploy

El proceso toma **5-10 minutos** (primera vez):

1. **Build Phase** (~5-7 min):
   - Descarga la imagen base Python
   - Instala dependencias
   - **Descarga el modelo de HuggingFace** (paraphrase-multilingual-MiniLM-L12-v2)
   - Construye la imagen final

2. **Deploy Phase** (~30-60 seg):
   - Inicia el contenedor
   - Precarga los embeddings en memoria
   - Lanza Gradio en el puerto asignado

Puedes seguir el progreso en:
- **Service → Deployments → Latest Deployment → View Logs**

![Captura: Logs mostrando "Step 8/15: RUN pip install..." y progreso]

---

### 🖥️ Opción B: Railway CLI (Deploy Local + GitHub)

Si prefieres la **línea de comandos**:

#### Paso 8.B.1: Instalar Railway CLI

```bash
# Con npm (Node.js requerido)
npm install -g @railway/cli

# Verificar instalación
railway --version
```

#### Paso 8.B.2: Autenticar

```bash
railway login
```

Se abrirá tu navegador. Haz clic en **"Authorize"**.

#### Paso 8.B.3: Inicializar Proyecto

```bash
cd "C:\Users\fsant\C - Desarrollo\Telegram\V2.0"

# Crear nuevo proyecto en Railway
railway init

# Railway te preguntará:
# - Project name: telegram-chat-search
# - Environment: production (presiona Enter)
```

#### Paso 8.B.4: Vincular a GitHub (Opcional)

```bash
# Si ya tienes el repo en GitHub:
railway link
# Selecciona el proyecto de la lista

# Railway vinculará tu directorio local al proyecto
```

#### Paso 8.B.5: Desplegar

```bash
railway up
```

Railway subirá los archivos, construirá la imagen y desplegará.

#### Paso 8.B.6: Ver Logs

```bash
railway logs -f
```

Verás los logs en tiempo real (como `docker logs -f`).

---

### 📦 Opción C: Railway CLI sin GitHub (Solo Local)

Si **no quieres usar GitHub** (solo desarrollo local):

```bash
cd "C:\Users\fsant\C - Desarrollo\Telegram\V2.0"

# Inicializar proyecto
railway init

# Desplegar directamente desde archivos locales
railway up

# Railway subirá todo el directorio (respetando .dockerignore)
```

⚠️ **Desventaja:** No hay historial de versiones, y cada `railway up` sube TODO de nuevo.

---

### ✅ Verificar que el Deploy Está en Progreso

En cualquiera de las 3 opciones, verifica en Railway Dashboard:

1. Ve a **Deployments** (en el menú lateral del Service)
2. Deberías ver un deployment con estado:
   - 🟡 **Building** → Construyendo la imagen Docker
   - 🟡 **Deploying** → Iniciando el contenedor
   - 🟢 **Active** → ¡Funcionando! ✅
   - 🔴 **Failed** → Ver logs para debugear

![Captura: Lista de deployments mostrando "Active" en verde]

---

## PASO 9 — Verificar el Despliegue

Una vez que el deployment está **Active** (verde), es momento de verificar que todo funciona correctamente.

---

### 9.1 Verificar Build Logs

Los logs de construcción muestran el proceso de creación de la imagen Docker.

#### Cómo Acceder a los Build Logs:

1. Ve a **Service → Deployments**
2. Haz clic en el último deployment (debería estar en verde "Active")
3. Haz clic en la pestaña **"Build Logs"**

#### ✅ Qué Buscar (Signos de Éxito):

```log
#8 [builder 3/8] RUN pip install --no-cache-dir -r requirements-prod.txt
#8 12.34 Collecting sentence-transformers
#8 15.67 Collecting torch==2.5.1
#8 45.89 Successfully installed torch-2.5.1 sentence-transformers-3.3.1 ...

#10 [builder 5/8] RUN python -c "from sentence_transformers import SentenceTransformer..."
#10 23.45 Downloading paraphrase-multilingual-MiniLM-L12-v2...
#10 56.78 Model downloaded successfully to /root/.cache/huggingface/...

#15 [stage-1 6/6] COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
#15 DONE 2.3s

#16 exporting to image
#16 exporting layers done
#16 writing image sha256:abc123... done
#16 naming to registry.railway.app/telegram-chat-search:latest done

Successfully built image: registry.railway.app/telegram-chat-search:latest
```

#### ❌ Errores Comunes en Build:

| Error | Causa | Solución |
|-------|-------|----------|
| `error: command 'gcc' failed` | Falta compilador C para lxml | Verifica que `Dockerfile` tiene `RUN apt-get install -y gcc g++ libxml2-dev libxslt1-dev` |
| `Timeout: pip install took >15min` | Conexión lenta, PyTorch muy pesado | Normal en Railway Free. Espera o usa imagen pre-built de PyTorch |
| `No space left on device` | Imagen demasiado grande | Revisa `.dockerignore`, elimina `chats/` y `temp_hf/` |
| `Failed to download model` | HuggingFace caído o bloqueado | Reintenta build, o usa mirrors de HF |

#### 💡 Tip: El build solo se ejecuta **una vez** (o cuando cambies el código). Los redespliegues posteriores usan la imagen cacheada.

---

### 9.2 Verificar Deploy Logs (Runtime)

Los logs de despliegue muestran lo que pasa **cuando la app arranca**.

#### Cómo Acceder a los Deploy Logs:

1. Ve a **Service → Deployments → Latest → "Deploy Logs"**
2. O usa CLI: `railway logs -f`

#### ✅ Qué Buscar (Signos de Éxito):

```log
======== Iniciando Telegram Chat Search V2.0 ========

Precargando embeddings en memoria...
Cargados 4154 embeddings (384 dims)
Modelo de embeddings: paraphrase-multilingual-MiniLM-L12-v2

Configuración:
  - Base de datos: /app/data/telegram_messages.db
  - OpenRouter API: Configurada ✓
  - Modelo LLM: anthropic/claude-3-haiku
  - Puerto: 8080

Running on local URL:  http://0.0.0.0:8080
Running on public URL: https://tu-proyecto-production.up.railway.app

To create a public link, set `share=True` in `launch()`.
```

#### ❌ Errores Comunes en Deploy:

| Error | Causa | Solución |
|-------|-------|----------|
| `killed` o `OOMKilled` | Sin memoria (Free plan = 0.5 GB) | Upgrade a Hobby ($5/mo, 8 GB RAM) |
| `FileNotFoundError: data/telegram_messages.db` | BD no incluida en imagen, o volume mal montado | Verifica `COPY data/...` en Dockerfile, o monta volume en `/app/data` |
| `Address already in use` | Puerto ocupado (raro en Railway) | Verifica que `app.py` lee `$PORT` correctamente |
| `No module named 'sentence_transformers'` | Dependencias no instaladas | Verifica `requirements-prod.txt` tiene todas las deps |
| `OpenRouterSummarizer: API key not found` | Variable `OPENROUTER_API_KEY` no configurada | Agrega la variable en Railway Dashboard |

---

### 9.3 Acceder a la Aplicación

Una vez que los logs muestran `Running on public URL`, la app está lista.

#### Paso 9.3.1: Obtener la URL Pública

Railway genera automáticamente una URL como:

```
https://telegram-chat-search-production.up.railway.app
```

**Cómo encontrarla:**

1. **Opción A:** En el Dashboard
   - Ve a **Service → Settings → Networking**
   - Sección **"Public Networking"**
   - Verás un dominio generado: `*.up.railway.app`

![Captura: Panel "Public Networking" mostrando la URL generada]

2. **Opción B:** En los Deploy Logs
   - Busca la línea `Running on public URL:`

3. **Opción C:** Usar Railway CLI
   ```bash
   railway open
   ```
   Abre la URL automáticamente en tu navegador.

#### ⚠️ Si No Hay URL Pública:

Si ves **"No public URL"** o **"Public networking disabled"**:

1. Ve a **Service → Settings → Networking**
2. Haz clic en **"Generate Domain"**
3. Railway creará un dominio `*.up.railway.app` automáticamente

![Captura: Botón "Generate Domain" en la sección Public Networking]

---

#### Paso 9.3.2: Probar la Aplicación

1. **Abre la URL** en tu navegador
2. Deberías ver la interfaz Gradio con:
   - ✅ **Tema oscuro** (negro/gris oscuro)
   - ✅ **Header naranja** (#e85d04) con el título "🔍 Búsqueda Semántica - Freedomia Chat"
   - ✅ **Cuadro de búsqueda** (textbox)
   - ✅ **Slider de resultados** (5-50)
   - ✅ **Botón "Buscar"** naranja
   - ✅ **Botón "Limpiar"** gris

![Captura: Interfaz Gradio mostrando el header naranja y el cuadro de búsqueda]

3. **Haz una búsqueda de prueba:**
   - Escribe en el cuadro: `Google Wallet`
   - Haz clic en **"Buscar"**
   - Espera 5-10 segundos

4. **Verifica los resultados:**
   - ✅ Aparecen mensajes en formato Markdown
   - ✅ Cada mensaje tiene:
     - 🧠 (match semántico), 🔤 (match FTS), o ✨ (ambos)
     - Nombre del usuario
     - ⭐ (si es usuario importante)
     - Fecha y hora
     - Enlace `[→ Abrir en Telegram]` (si implementaste deep links)
   - ✅ Al final aparece un **resumen con IA** (en negrita y fondo gris)

![Captura: Resultados mostrando 3 mensajes con iconos y un resumen al final]

---

### 9.4 Verificar Funcionalidad Completa

Usa este **checklist** para asegurar que todo funciona:

#### ✅ Checklist de Funcionalidad:

- [ ] **La interfaz carga en <5 segundos** (sin errores 502/503)
- [ ] **El tema oscuro** se aplica correctamente (fondo negro, texto blanco)
- [ ] **El header naranja** (#e85d04) es visible
- [ ] **El cuadro de búsqueda** acepta texto en español
- [ ] **El slider de resultados** se mueve de 5 a 50
- [ ] **El botón "Buscar"** cambia de color al pasar el mouse (hover)
- [ ] **Los resultados aparecen en <10 segundos** (búsqueda rápida)
- [ ] **Los iconos se muestran correctamente:**
  - 🧠 = Match semántico (vectorial)
  - 🔤 = Match FTS (texto completo)
  - ✨ = Ambos (híbrido)
- [ ] **Los usuarios importantes** tienen estrella ⭐ (ej: Luis Alberto Iglesias Gómez)
- [ ] **El resumen con IA se genera** (NO aparece "MockSummarizer" ni mensajes de placeholder)
- [ ] **El resumen menciona temas relevantes** (coherencia)
- [ ] **El botón "Limpiar" borra** el cuadro de búsqueda y resultados
- [ ] **Las búsquedas en español funcionan** (ej: "wallet", "Google", "privacidad")
- [ ] **NO hay errores en la consola del navegador** (F12 → Console)

---

#### 🧪 Casos de Prueba Recomendados:

| Búsqueda | Resultados Esperados |
|----------|----------------------|
| `Google Wallet` | Mensajes sobre pagos, privacidad, alternativas |
| `privacidad` | Discusiones sobre datos personales, KYC, apps |
| `Luis Alberto` | Mensajes del usuario importante ⭐ |
| `blockchain` | Mensajes técnicos sobre criptomonedas |
| `(búsqueda vacía)` | Mensaje de error o sin resultados |

---

#### ❌ Si el Resumen Muestra "MockSummarizer":

Ejemplo de salida incorrecta:
```
📊 Resumen:
Este es un resumen simulado porque no hay API key configurada.
Los mensajes tratan sobre: temas varios, discusiones, información.
```

**Causa:** La variable `OPENROUTER_API_KEY` no está configurada o es inválida.

**Solución:**
1. Ve a **Service → Variables**
2. Verifica que `OPENROUTER_API_KEY` existe y empieza con `sk-or-v1-`
3. Verifica que tienes **créditos en OpenRouter** (https://openrouter.ai/credits)
4. Redespliega: `railway up` o trigger un nuevo deploy en el Dashboard

---

#### 🔍 Si NO Aparecen Resultados:

**Posibles causas:**
1. La base de datos está vacía → Verifica que `data/telegram_messages.db` tiene mensajes:
   ```bash
   railway run sqlite3 /app/data/telegram_messages.db "SELECT COUNT(*) FROM messages;"
   ```
   Debería devolver `4154` (o el número de mensajes que importaste).

2. Los embeddings no se cargaron → Revisa los logs de deploy, busca:
   ```log
   Cargados 4154 embeddings
   ```

3. Problema con FTS5 → Verifica que la BD tiene el índice:
   ```bash
   railway run sqlite3 /app/data/telegram_messages.db ".schema messages_fts"
   ```

---

### 9.5 Verificar Logs de Consultas

Cada búsqueda genera logs. Úsalos para debugear:

```bash
railway logs -f
```

Salida esperada cuando buscas "Google Wallet":
```log
INFO: Búsqueda: 'Google Wallet' (top_k=15)
INFO: Vector search: 8 resultados
INFO: FTS search: 5 resultados
INFO: RRF fusion: 10 resultados únicos
INFO: Enviando 10 mensajes a OpenRouter para resumir...
INFO: Resumen generado (245 tokens, $0.0012)
```

---

## PASO 10 — Problemas Comunes y Soluciones

Aquí están los **errores más frecuentes** al desplegar en Railway y cómo solucionarlos.

---

### 10.1 ❌ Error: Out of Memory (OOM)

#### Síntomas:
- El deployment muestra estado **"Crashed"** o **"Failed"**
- Los logs terminan abruptamente con `Killed` o `OOMKilled`
- La app arranca pero se cae al hacer la primera búsqueda

#### Logs Típicos:
```log
Precargando embeddings en memoria...
Cargados 2341 embeddings...
Killed
```

#### Causa:
El **plan Free Trial de Railway solo tiene 0.5 GB de RAM**. La aplicación necesita:
- ~300 MB para el modelo de embeddings
- ~200 MB para 4154 embeddings (384 dims × 4154 × 4 bytes)
- ~150 MB para Gradio + dependencias
- ~100 MB para PyTorch
- **Total: ~750 MB - 1.5 GB**

#### Soluciones:

##### **Solución A: Upgrade a Plan Hobby (Recomendada)**

```
Plan Hobby:
  - Coste: $5/mes
  - RAM: 8 GB (más que suficiente)
  - CPU: 8 vCPUs
  - Sin límite de tiempo de ejecución
```

**Cómo hacer upgrade:**
1. Ve a **Dashboard → Settings → Plan**
2. Selecciona **"Hobby"**
3. Agrega tu tarjeta de crédito
4. Haz clic en **"Subscribe"**

##### **Solución B: Reducir Consumo de Memoria (Temporal)**

Si quieres seguir en Free Trial (solo para pruebas):

1. **Reduce `top_k` en las búsquedas:**

   Edita `telegram_chat_search/chat_interface/app.py`, línea ~117:

   ```python
   # Antes (usa mucha RAM):
   results = hybrid_search.search(query, top_k=50, alpha=0.6)

   # Después (usa menos RAM):
   results = hybrid_search.search(query, top_k=15, alpha=0.6)
   ```

2. **Usa un modelo de embeddings más pequeño:**

   Edita `telegram_chat_search/config.py`:

   ```python
   # Antes:
   embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"  # 384 dims

   # Después:
   embedding_model: str = "all-MiniLM-L6-v2"  # 384 dims, pero más rápido y ligero
   ```

   Pero tendrás que **regenerar los embeddings**:
   ```bash
   python -m telegram_chat_search generate-embeddings
   ```

3. **Commit y redespliega:**
   ```bash
   git add .
   git commit -m "Reduce memory usage for Railway Free plan"
   git push
   ```

⚠️ **Nota:** Estas optimizaciones **reducen la calidad** de los resultados. El plan Hobby es la mejor solución.

---

### 10.2 ❌ Error: Build Timeout

#### Síntomas:
- El build falla después de **15-20 minutos**
- Railway muestra: `Build timed out after 20m`
- Los logs se detienen en `Downloading PyTorch...` o `Downloading model...`

#### Causa:
- La imagen de PyTorch es **muy pesada** (~800 MB)
- El modelo de HuggingFace tarda en descargarse
- Railway Free tiene **límites de tiempo de build**

#### Soluciones:

##### **Solución A: Usar Imagen Pre-built de PyTorch (Más rápida)**

Edita el `Dockerfile`:

```dockerfile
# Antes:
FROM python:3.10-slim AS builder

# Después (imagen con PyTorch pre-instalado):
FROM pytorch/pytorch:2.5.1-cpu AS builder
```

Esto ahorra **5-7 minutos** en el build.

##### **Solución B: Optimizar .dockerignore**

Asegúrate de que estos directorios NO se copian al contenedor:

```
# .dockerignore
chats/
temp_hf/
.git/
__pycache__/
*.pyc
*.db-journal
sessions/
```

Esto reduce el tamaño del **build context**.

##### **Solución C: Dividir el Build en Etapas Más Pequeñas**

El `Dockerfile` ya usa **multi-stage build**, pero puedes optimizarlo:

```dockerfile
# Cachea las dependencias primero (cambian poco)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-prod.txt

# Descarga el modelo en una capa separada
RUN --mount=type=cache,target=/root/.cache/huggingface \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

---

### 10.3 ❌ Error: Healthcheck Fails

#### Síntomas:
- Railway muestra **"Unhealthy"** en el status
- El deployment se reinicia cada 2-3 minutos
- Los logs muestran `Healthcheck failed: timeout`

#### Causa:
La aplicación tarda **más de 300 segundos** en arrancar (tiempo del healthcheck en `railway.toml`).

Esto puede pasar si:
- Los embeddings son muchos (>10,000)
- La base de datos es muy grande (>100 MB)
- Railway Free tiene CPU limitada

#### Solución:

##### **Aumentar el Timeout del Healthcheck:**

Edita `railway.toml`:

```toml
# Antes:
[deploy.healthcheck]
timeout = 300

# Después:
[deploy.healthcheck]
timeout = 600  # 10 minutos
```

Commit y redespliega:
```bash
git add railway.toml
git commit -m "Increase healthcheck timeout to 10 minutes"
git push
```

##### **Optimizar el Startup:**

1. **Cachea embeddings en disco** (en lugar de cargarlos en RAM):

   Edita `telegram_chat_search/chat_interface/app.py`:

   ```python
   # En lugar de cargar todos en memoria:
   embeddings = embedding_repo.load_embeddings()  # Carga todo

   # Carga bajo demanda (lazy loading):
   # Solo se cargan cuando se hace una búsqueda
   ```

2. **Deshabilita el healthcheck** (no recomendado):

   ```toml
   [deploy.healthcheck]
   enabled = false
   ```

---

### 10.4 ❌ Error: Database Not Found

#### Síntomas:
- La app arranca pero crashea al buscar
- Logs muestran: `FileNotFoundError: [Errno 2] No such file or directory: '/app/data/telegram_messages.db'`

#### Causa:
1. La BD no fue incluida en la imagen Docker
2. El `.dockerignore` excluye `data/`
3. El volume no está montado correctamente

#### Soluciones:

##### **Verificar que `data/` NO está en .dockerignore:**

```bash
# .dockerignore NO debe tener:
# data/
```

Si lo tiene, **bórralo** y redespliega.

##### **Verificar que el Dockerfile Copia la BD:**

```dockerfile
# Debe existir esta línea:
COPY data/telegram_messages.db /app/data/telegram_messages.db
```

##### **Debug: Listar Archivos en el Contenedor:**

```bash
railway run ls -la /app/data/
```

Deberías ver:
```
total 12288
-rw-r--r-- 1 root root 12582912 Feb  9 10:30 telegram_messages.db
```

Si NO aparece, revisa los pasos anteriores.

##### **Si Usas Volume: Verifica el Mount Path:**

El mount path DEBE ser `/app/data` (coincide con `WORKDIR /app` + `data/telegram_messages.db`).

---

### 10.5 ❌ Error: Port Mismatch

#### Síntomas:
- La app arranca correctamente en los logs
- Los logs muestran: `Running on http://0.0.0.0:7860`
- Pero Railway muestra **"Unhealthy"** o no responde en la URL pública

#### Causa:
Railway asigna un puerto **dinámico** (variable `$PORT`), pero la app está escuchando en un puerto fijo (`7860`).

#### Solución:

##### **Verificar que `app.py` Lee `$PORT`:**

Edita `app.py`:

```python
import os

if __name__ == "__main__":
    # Lee el puerto de la variable de entorno $PORT (Railway lo inyecta)
    port = int(os.environ.get("PORT", 7860))

    # IMPORTANTE: server_name debe ser 0.0.0.0 (no localhost)
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )
```

##### **Verificar Variable de Entorno:**

```bash
railway run env | grep PORT
```

Salida esperada:
```
PORT=8080
```

Si NO aparece, Railway debería inyectarla automáticamente. Verifica en **Service → Variables**.

##### **NO Configures `PORT` Manualmente:**

❌ **NUNCA hagas esto:**
```env
PORT=7860  # ❌ Railway sobrescribe esto, causará conflictos
```

✅ **Railway la inyecta automáticamente** (no la toques).

---

### 10.6 ❌ Error: OpenRouter API Fails

#### Síntomas:
- Los resultados aparecen pero el resumen dice:
  ```
  ⚠️ Error al generar resumen: 401 Unauthorized
  ```
- O aparece el resumen de `MockSummarizer`:
  ```
  Este es un resumen simulado porque no hay API key configurada.
  ```

#### Causa:
1. `OPENROUTER_API_KEY` no está configurada
2. La API key es **inválida** o **expiró**
3. No tienes **créditos** en tu cuenta de OpenRouter

#### Soluciones:

##### **Verificar que la Variable Existe:**

```bash
railway run env | grep OPENROUTER_API_KEY
```

Si NO aparece, agrégala en **Service → Variables**.

##### **Verificar que la Key es Válida:**

Haz una prueba manual con `curl`:

```bash
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer sk-or-v1-xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-3-haiku",
    "messages": [{"role": "user", "content": "Hola"}]
  }'
```

Respuesta esperada:
```json
{
  "id": "gen-xxxx",
  "choices": [{"message": {"content": "¡Hola! ¿Cómo estás?"}}]
}
```

Si devuelve `401 Unauthorized`, la key es **inválida**.

##### **Verificar Créditos en OpenRouter:**

1. Ve a https://openrouter.ai/credits
2. Deberías tener **al menos $1 USD**
3. Si está en $0, agrega créditos con tarjeta de crédito

##### **Regenerar la API Key:**

1. Ve a https://openrouter.ai/keys
2. Haz clic en **"Revoke"** en la key antigua
3. Crea una nueva key
4. Actualiza la variable en Railway
5. Redespliega

---

### 10.7 ❌ Error: Model Download at Runtime

#### Síntomas:
- La **primera búsqueda** tarda **2-3 minutos**
- Los logs muestran:
  ```log
  Downloading paraphrase-multilingual-MiniLM-L12-v2...
  Downloading (…)ce_bert_config.json: 100%|██████| 571/571 [00:00<00:00, 285kB/s]
  Downloading pytorch_model.bin: 100%|██████| 471M/471M [01:23<00:00, 5.65MB/s]
  ```

#### Causa:
El modelo **NO se pre-descargó** durante el build. Se descarga al arrancar la app (lento).

#### Solución:

##### **Verificar que el Dockerfile Tiene el Pre-download:**

```dockerfile
# Debe estar esta línea en el Dockerfile:
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

##### **Verificar que `HF_HOME` Está Configurado:**

```dockerfile
ENV HF_HOME=/root/.cache/huggingface
```

##### **Verificar que el Modelo se Copió a la Imagen Final:**

```dockerfile
# Multi-stage: copiar el modelo del builder
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
```

Si falta alguna línea, agrégala, commit y redespliega:
```bash
git add Dockerfile
git commit -m "Fix model pre-download in Dockerfile"
git push
```

---

### 10.8 💰 Costes y Límites de Railway

#### Comparación de Planes:

| Plan | RAM | CPU | Disco | Coste Mensual | Crédito Incluido | Volumes | Build Timeout |
|------|-----|-----|-------|---------------|------------------|---------|---------------|
| **Free Trial** | 0.5 GB | 1 vCPU | 1 GB | $0 | $5 (30 días) | ❌ NO | 20 min |
| **Hobby** | 8 GB | 8 vCPU | 100 GB | $5/mes | $5/mes | ✅ SI | Sin límite |
| **Pro** | 32 GB | 32 vCPU | 500 GB | $20/mes | $20/mes | ✅ SI | Sin límite |

#### Recomendaciones:

| Escenario | Plan Recomendado |
|-----------|------------------|
| Pruebas rápidas (1-2 días) | Free Trial |
| Producción (uso personal) | Hobby ($5/mes) |
| Múltiples usuarios, alta carga | Pro ($20/mes) |

#### ⚠️ Límites del Free Trial:

- **0.5 GB RAM** → OOM casi garantizado con esta app
- **$5 de crédito** → Se acaba en ~30 días (o antes si usas mucho CPU)
- **Sin volumes** → No puedes actualizar la BD sin reconstruir
- **Build timeout 20 min** → Puede fallar si el build es lento

**Conclusión:** Para esta app, el **plan Hobby es el mínimo viable**.

---

### 10.9 🛠️ Comandos Útiles de Railway CLI

#### Ver Logs en Tiempo Real:
```bash
railway logs -f
```

#### Ejecutar Bash Dentro del Contenedor:
```bash
railway run bash
```

Dentro del bash:
```bash
ls -la /app/data/
sqlite3 /app/data/telegram_messages.db "SELECT COUNT(*) FROM messages;"
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

#### Ver Variables de Entorno:
```bash
railway variables
```

#### Ver Estado del Servicio:
```bash
railway status
```

Salida esperada:
```
Service: telegram-chat-search
Status: Active
Deployment: https://telegram-chat-search-production.up.railway.app
```

#### Abrir la App en el Navegador:
```bash
railway open
```

#### Redesplegar Manualmente:
```bash
railway up
```

#### Ver Info del Proyecto:
```bash
railway whoami
```

#### Descargar la BD desde el Volume:
```bash
railway volume download telegram-data /telegram_messages.db ./backup.db
```

#### Subir una BD Actualizada:
```bash
railway volume upload telegram-data ./data/telegram_messages.db /telegram_messages.db
```

---

### 10.10 🐛 Debug Avanzado: Ejecutar Python Dentro del Contenedor

Si necesitas debugear código Python:

```bash
railway run python
```

Dentro del intérprete:
```python
from telegram_chat_search.config import Config
config = Config()
print(config.db_path)
# Salida: /app/data/telegram_messages.db

from telegram_chat_search.database.repositories import MessageRepository
repo = MessageRepository(config)
count = repo.count_messages()
print(f"Mensajes en BD: {count}")
# Salida: Mensajes en BD: 4154
```

---

## 📚 Resumen de Archivos de Despliegue

Estos son **todos los archivos** que debes tener antes de desplegar en Railway:

| Fichero | Paso | Descripción |
|---------|:----:|-------------|
| **`.gitignore`** | 1 | Excluye archivos sensibles: `.env`, `chats/`, `temp_hf/`, `__pycache__/`, `*.pyc`, `.venv/`, `sessions/` |
| **`requirements-prod.txt`** | 2 | Dependencias optimizadas para producción. PyTorch CPU-only (`--index-url`), sin deps de desarrollo (`pytest`, `black`, etc.) |
| **`app.py` (modificado)** | 3 | Entry point que lee `$PORT` de Railway, `server_name=0.0.0.0`, sin `share=True` |
| **`Dockerfile`** | 4 | Multi-stage build. Base Python 3.10-slim, instala gcc/libxml2 para lxml, pre-descarga modelo de HuggingFace, copia BD, expone puerto 7860 |
| **`.dockerignore`** | 4 | Excluye archivos innecesarios del contexto de build: `chats/`, `temp_hf/`, `.git/`, `*.pyc`, `.env`, `__pycache__/`, `.venv/` |
| **`railway.toml`** | 5 | Configura builder=DOCKERFILE, healthcheck con timeout=300s, restart_policy_type=ON_FAILURE, restart_policy_max_retries=3 |
| **`RAILWAY_DEPLOY_GUIDE.md`** | 6-10 | **Este documento** con instrucciones detalladas de despliegue |

---

## ✅ Checklist Final de Pre-Despliegue

Antes de hacer `railway up`, verifica:

- [ ] Archivo `.gitignore` excluye `.env`, `chats/`, `temp_hf/`
- [ ] Archivo `requirements-prod.txt` tiene todas las dependencias (sentence-transformers, gradio, httpx, click, rich, etc.)
- [ ] Archivo `app.py` lee `os.environ.get("PORT", 7860)` y usa `server_name="0.0.0.0"`
- [ ] Archivo `Dockerfile` tiene multi-stage build y pre-descarga el modelo
- [ ] Archivo `.dockerignore` excluye directorios pesados
- [ ] Archivo `railway.toml` configura healthcheck con timeout adecuado
- [ ] Base de datos `data/telegram_messages.db` existe y tiene mensajes
- [ ] Repositorio en GitHub (si usas Opción A)
- [ ] Variables de entorno configuradas en Railway Dashboard (`OPENROUTER_API_KEY`, `GRADIO_SERVER_NAME`)
- [ ] Plan Hobby activado (si necesitas >0.5 GB RAM)

---

## 🎉 ¡Listo para Producción!

Si seguiste todos los pasos, tu aplicación **Telegram Chat Search V2.0** debería estar:

- ✅ **Desplegada en Railway** con URL pública
- ✅ **Funcionando 24/7** (siempre disponible)
- ✅ **Con búsqueda híbrida** (semántica + FTS5)
- ✅ **Con resumenes de IA** (OpenRouter + Claude Haiku)
- ✅ **Con tema oscuro Freedomia** (naranja #e85d04)
- ✅ **Optimizada** (modelo pre-descargado, embeddings en memoria)

### Próximos Pasos:

1. **Compartir la URL** con tu equipo
2. **Monitorear logs** con `railway logs -f`
3. **Configurar dominio personalizado** (en Railway: Settings → Networking → Custom Domain)
4. **Implementar sincronización** con Telegram API (para actualizar la BD automáticamente)
5. **Agregar analytics** (ej: contar búsquedas, queries más populares)

---

## 🆘 Soporte

Si tienes problemas:

1. **Revisa la sección PASO 10** (cubre el 90% de errores comunes)
2. **Revisa los logs:** `railway logs -f`
3. **Busca en la documentación oficial:** https://docs.railway.app
4. **Únete al Discord de Railway:** https://discord.gg/railway

---

**Guía creada por:** Telegram Chat Search V2.0
**Versión:** 1.0
**Fecha:** 2026-02-09
**Licencia:** MIT

---

🚂 **¡Feliz despliegue en Railway!** 🚀
