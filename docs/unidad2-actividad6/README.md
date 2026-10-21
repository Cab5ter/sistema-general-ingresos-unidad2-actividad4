# Unidad II · Actividad 6 · Control de acceso según el rol

Implementación de la sección «Segunda parte. Actividad para entregar» de las páginas 9 a 11 del material. Equipo: Enrique Zavala y Marcelo Medina. Continúa el mismo proyecto de las actividades 1 a 5.

## Inicio

Desde la raíz del proyecto en PowerShell, con Python y Docker Desktop activos:

```powershell
python -m venv env
.\env\Scripts\python.exe -m pip install -r requirements.txt
# Solo si aún no existe .env.docker. No sobrescribir la configuración anterior.
.\env\Scripts\python.exe -m app.init_docker
docker compose --env-file .env.docker up -d --build
$env:SETTINGS_FILE = '.env.docker'
```

PyJWT ya forma parte de `requirements.txt`. `JWT_SECRET` se genera aleatoriamente en `.env.docker`; los ejemplos `.env.example` y `.env.docker.example` no tienen valores reales. La vigencia de esta actividad es exactamente 30 minutos (`JWT_EXPIRE_MINUTES=30`). No se almacenan tokens en MySQL ni se agrega otra matriz de permisos.

El puerto normal es http://127.0.0.1:8007/graphql. En el laboratorio de esta entrega se usaron un proyecto Compose separado y los puertos 8008/3308 para conservar la instalación anterior. Cambiar los puertos únicamente en la configuración local, no las claves de un volumen MySQL ya inicializado.

## Login y encabezado

En GraphiQL ejecutar `Entrar` de `operaciones.graphql` con el correo y la contraseña local de la persona. El resultado conserva `tokenType`, `token` y `user { name }`. Una credencial incorrecta no entrega token y nunca se expone el hash.

Después, en **Headers** de GraphiQL, escribir JSON:

```json
{"Authorization":"Bearer TOKEN_DEVUELTO_POR_LOGIN"}
```

Enviar las demás operaciones con ese encabezado, sin contraseña y sin `actorCompanyUserId`. `companyId` de un input sigue siendo el recurso solicitado; el servidor comprueba que coincida con la empresa de la membresía firmada. No permite cambiar la identidad.

`app/auth.py::leer_actor` verifica la firma exclusivamente HS256, el vencimiento y los tres claims obligatorios. Comprueba en la base que la membresía exista, pertenezca a la empresa firmada y que usuario, empresa y membresía sigan activos. `Service.require` llama a `leer_actor` y a `exigir_permiso` antes de ejecutar la operación. Se conserva la segunda comprobación de permisos antes del commit.

El token contiene solo `companyUserId`, `companyId` y `exp`: no contiene contraseña, hash, rol ni lista de permisos. `login` obtiene ambos IDs de la membresía en la base. Si un correo tuviera varias membresías activas, el login se rechaza por ambigüedad en lugar de elegir una empresa arbitraria. Los JWT antiguos que solo tenían `sub` requieren un login nuevo.

La inicialización de empresas y su primer administrador sigue requiriendo la clave local `X-Bootstrap-Key`. Las operaciones empresariales y de roles se autentican con Bearer. Los catálogos de roles continúan siendo globales, tal como en las actividades anteriores.

## Personas y nueve casos

Para preparar explícitamente el escenario de Ana, Luis, María, José y Pedro en el laboratorio:

```powershell
$env:EVIDENCE_DIR = 'D:\ruta\fuera-del-repositorio\evidencias-actividad6'
$env:ACTIVITY4_URL = 'http://127.0.0.1:8007/graphql'
.\env\Scripts\python.exe -m app.demo_activity4
```

Este comando conserva la empresa y usuarios existentes por correo, usa la contraseña privada de `.activity4-credentials.json`, prepara cuenta/concepto válidos y asigna los puestos del escenario: Ana ADMINISTRADOR, Luis CONTADOR, María y José CAPTURISTA, Pedro CONSULTA. Es una preparación deliberada de pruebas: devolverá a Pedro a CONSULTA si ya estaba promovido. Después del caso 6 Pedro termina en CAPTURISTA.

Cada persona hace login y usa su propio token. Los IDs se obtienen del `ids.json` generado, sin asumir valores fijos.

| Caso | Encabezado | Operación | Resultado y regla |
|---|---|---|---|
| 1 | Ninguno | Cuenta | UNAUTHENTICATED; no se crea fila. |
| 2 | Token de María | Movimiento | Se registra con transactions.write. |
| 3 | Mismo token de María | Cuenta | FORBIDDEN; CAPTURISTA no tiene accounts.write. |
| 4 | Token de Luis | Cuenta | CONTADOR sí crea una cuenta. |
| 5 | Token de Pedro CONSULTA | Movimiento | FORBIDDEN; no se crea fila. |
| 6 | Token de Ana | CambiarPuesto de Pedro a CAPTURISTA | Se cambia el rol mediante roles.write. |
| 7 | Exactamente el token de Pedro del caso 5 | Movimiento | Se guarda sin login nuevo: permisos actuales desde la base. |
| 8 | Token de otra empresa | Cuentas de la empresa original | FORBIDDEN; no se leen recursos ajenos. |
| 9a | Token con firma alterada | Cuenta | UNAUTHENTICATED; no se crea fila. |
| 9b | Token vencido | Cuenta | UNAUTHENTICATED; no se crea fila. |

Para cada rechazo de escritura consultar la tabla desde otra conexión con la marca de la petición: el conteo por marca debe seguir en cero y el total de filas debe ser igual antes y después. `comprobaciones.sql` proporciona las consultas.

## Evidencias fuera de Git

El PDF permite un cliente HTTP contra `/graphql`. El generador ejecuta peticiones HTTP reales y SELECT independientes en MySQL; produce un registro y un visor HTML con el encabezado, documento, respuesta, regla y conteos antes/después. El token correcto se representa por sus claims verificados. No guarda el JWT completo ni las contraseñas. Las capturas son del visor de registros HTTP/SQL, no de GraphiQL.

```powershell
$env:SETTINGS_FILE = '.env.docker'
$env:EVIDENCE_DIR = 'D:\ruta\fuera-del-repositorio\evidencias-actividad6'
$env:ACTIVITY4_URL = 'http://127.0.0.1:8007/graphql'
.\env\Scripts\python.exe -m scripts.activity6_evidence
# Requiere Playwright y un navegador instalado para guardar los PNG del visor.
# npm install --prefix tmp/capturas playwright
$env:PLAYWRIGHT_MODULE = (Resolve-Path 'tmp/capturas/node_modules/playwright').Path
$env:CHROMIUM = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
node scripts/activity6_capture.cjs
```

Se generan 12 capturas: login correcto, login rechazado, casos 1 a 8 y dos variantes del caso 9. `registro.json` contiene los resultados reales y las comprobaciones SQL. `index.html` permite recorrerlas. La clave `mismo_token_del_caso_5` demuestra la reutilización de la variable en memoria; el token no se almacena. No subir esta carpeta al repositorio.

## Pruebas

```powershell
$env:EVIDENCE_DIR = 'D:\ruta\fuera-del-repositorio\evidencias-actividad6'
.\env\Scripts\python.exe -m pytest -q
$env:TEST_MYSQL = '1'
.\env\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_MYSQL
```

Las pruebas MySQL crean y eliminan solo bases aleatorias `ingresos_test_*`. Las pruebas SQLite usan archivos temporales. Se comprueban los nueve casos, la duración y firma, claims obligatorios/coherentes, algoritmo incorrecto, token sin firma, secreto incorrecto, encabezados malformados, suplantación con el argumento retirado y conservación de las reglas anteriores. El fixture de regresión traduce su selector interno de persona a un token obtenido por login: ese selector no se envía a GraphQL.

Validación del 20 de octubre de 2026: **85 pruebas aprobadas en MySQL 8.4.11; 84 aprobadas y una omitida en SQLite** (la omitida comprueba la migración hacia MySQL). Los 12 registros de evidencia del servidor Docker pasaron, incluyendo las dos variantes del caso 9. Se validaron también los 19 documentos GraphQL actuales contra el esquema. Solo se observó el aviso de deprecación existente de Starlette/AnyIO.

La documentación y los scripts de captura de las actividades anteriores son históricos. Sus imágenes muestran el contrato anterior. Las operaciones de GraphQL actuales y las de la actividad 5 ya usan Bearer; para las nuevas capturas usar los generadores de esta actividad.
