# Dashboard financiero (HTML + CSS + JavaScript)

Cliente web del Sistema General de Ingresos. Inicia sesión con la mutación `login`, consulta `generalBalance` con `Authorization: Bearer` y muestra los indicadores generales y el detalle por cuenta. No calcula nada: todos los importes vienen del API.

## Archivos

| Archivo | Qué hace |
|---|---|
| `index.html` | Estructura: login, encabezado, controles de período, indicadores, riesgo y detalle |
| `styles.css` | Diseño y versión adaptable a pantallas pequeñas |
| `app.js` | Login, consulta GraphQL, formato de importes, estados vacíos y errores |
| `config.js` | URL del API y período por defecto (único archivo que se edita) |

## Cómo levantarlo

Necesitas tres procesos. Desde la carpeta raíz del proyecto, en PowerShell:

**1. MySQL y API** (pasos del README de la actividad 7):

```powershell
.\.venv\Scripts\Activate.ps1
docker compose --env-file .env.docker up -d mysql
$env:SETTINGS_FILE = '.env.docker'
python -m app.demo_activity7
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

**2. Dashboard** (en otra terminal):

```powershell
cd dashboard
python -m http.server 5500 --bind 127.0.0.1
```

**3.** Abre <http://127.0.0.1:5500>.

> No abras `index.html` con doble clic (`file://`): el navegador envía el origen `null` y CORS lo bloquea. Siempre sírvelo con el comando anterior.

## CORS

El dashboard corre en el puerto 5500 y el API en el 8007, así que `app/factory.py` agrega `CORSMiddleware`. Por defecto permite `http://127.0.0.1:5500` y `http://localhost:5500`. Para otro origen:

```powershell
$env:CORS_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
```

## Usuario y período de prueba

- Usuario: `admin.actividad7@example.com`
- Contraseña: la genera `python -m app.demo_activity7` en `.activity7-credentials.json` (archivo ignorado por Git; no se sube).
- Período de demostración: **2026-10-26 a 2026-10-30**.

Valores esperados con los datos de Banco, Caja y Ahorro:

| Indicador | Valor |
|---|---|
| Saldo inicial | 1,000.00 |
| Ingresos | 3,500.00 |
| Egresos | 2,900.00 |
| Profit | 600.00 |
| Saldo final | 1,600.00 |
| General en rojo | No |
| Cuentas en rojo | 1 (Caja) |

## De dónde sale cada número

| En pantalla | Campo GraphQL |
|---|---|
| Saldo inicial | `openingBalance` |
| Ingresos | `totalIncome` |
| Egresos | `totalExpense` |
| Profit | `profit` |
| Saldo final | `closingBalance` |
| General en rojo | `isInRed` |
| Cuentas en rojo | `accountsInRed` |
| Tabla de detalle | `accounts { ... }` |

Cada tarjeta muestra el nombre de su campo al pasar el cursor, y su elemento HTML lleva `data-field`.

## Decisiones de diseño

- Los importes se formatean desde el texto del servidor (sin `float`) y siempre llevan dos decimales, en MXN.
- Un saldo final negativo se marca en rojo; un profit negativo se marca en ámbar para no confundirlos.
- El token se guarda en `sessionStorage` (se borra al cerrar la pestaña o al cerrar sesión). No hay secretos en el código.
- El período que se muestra es el que devuelve el servidor, no el de los campos de fecha.
- Si `fromDate` es posterior a `toDate`, no se llama al API y se muestra un mensaje.
- Si el token falla, vuelve al login con un mensaje. Si falta permiso, muestra "Acceso denegado" y no pinta números.

## Cómo provocar los casos de error para las evidencias

- **Token inválido:** con el dashboard abierto, en DevTools (F12) → Application → Session Storage → clave `ingresos.sesion`, cambia unas letras del `token` y pulsa Actualizar.
- **Sin permiso:** inicia sesión con un usuario que no tenga `accounts.read` o `transactions.read`.
- **Fechas inválidas:** pon "Desde" posterior a "Hasta".
- **API apagada:** detén uvicorn y pulsa Actualizar.