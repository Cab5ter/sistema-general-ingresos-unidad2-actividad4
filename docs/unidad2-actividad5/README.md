# Unidad II · Actividad 5 · Configurar permisos con GraphQL

> Historial de la actividad 5. Desde la actividad 6, las operaciones usan el token de login en Authorization: Bearer. Los antiguos selectores de actor ya no existen en el esquema. Los scripts y capturas históricos documentan el contrato de aquella entrega; para reproducir el contrato actual, seguir `../unidad2-actividad6/README.md`.

Continuación del Sistema General de Ingresos de la actividad 4. Se conservan Python, FastAPI, Strawberry, SQLAlchemy, MySQL, los cuatro roles, los diez permisos y las operaciones anteriores.

Entrega en equipo.

**Integrantes del equipo:** Enrique Zavala y Marcelo Medina.

Aportaciones de la entrega: catálogo filtrado, cálculo compartido de planes, aplicación atómica de listas, pruebas de rollback, investigación, variables y evidencias E01-E10. Se conserva la autoría del código previo.

Repositorio: https://github.com/Cab5ter/sistema-general-ingresos-unidad2-actividad4

## Implementación

- `permissionCatalog`: lee permisos activos desde SQL, ordena por código y filtra mediante PermissionResource. Requiere roles.read.
- `previewRolePermissions`: valida y calcula diferencias sin escribir. Requiere roles.read.
- `setRolePermissions`: establece exactamente la lista final, con un único commit o rollback. Requiere roles.write. Repetir la lista devuelve changed: false.
- Ambas operaciones de listas rechazan ADMINISTRADOR, roles inactivos y permisos inválidos, inexistentes, inactivos o repetidos. [] está permitido para los demás roles.
- Se conserva la restricción única de role_permissions y el arranque que considera filas históricas inactivas. No fue necesario cambiar columnas ni migrar el esquema.

## Iniciar API y MySQL

Si descargaste el ZIP, entra primero en `ingresos/` (`cd ingresos`). En GitHub, usa la raíz del repositorio. Se requiere Python 3.12 o 3.13 y Docker Compose. Python 3.14 no es compatible con las dependencias fijadas.

```bash
python3.12 -m venv env
./env/bin/python -m pip install -r requirements.txt
# Ejecutar solo si .env.docker aún no existe:
./env/bin/python -m app.init_docker
# Esperar al estado healthy antes de iniciar la API o las pruebas:
docker compose --env-file .env.docker up -d --build --wait
SETTINGS_FILE=.env.docker ACTIVITY4_URL=http://127.0.0.1:8007/graphql \
  ./env/bin/python -m app.demo_activity4
```

El comando prepara usuarios ficticios y datos financieros con las operaciones existentes. Los puertos predeterminados son 8007/3307; si ya existe `.env.docker`, usar sus API_PORT y MYSQL_PORT. El laboratorio de esta entrega utilizó API 8017 y MySQL 3317, MySQL 8.4.11 y Python 3.12.14. Las contraseñas demo quedan exclusivamente en un archivo privado excluido de Git y ZIP.

Para ejecutar Python fuera de Docker, con MySQL ya saludable:

```bash
SETTINGS_FILE=.env.docker ./env/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8017
```

## Operaciones y variables

Abrir `/graphql` en GraphiQL. Copiar `operaciones.graphql`, seleccionar el nombre indicado y pegar el JSON correspondiente en Variables. Ejecutar las operaciones por separado.

| Operación | Archivo de variables |
|---|---|
| PuntoDePartida, ExplorarCatalogo | variables/actor.json |
| CatalogoCompleto | variables/actor.json; variables/payments.json para el error |
| RevisarConfiguracion | variables/s1.json; variables/s0.json o variables/vacia.json según el caso |
| AplicarConfiguracion | variables/s1.json, repetir; variables/s0.json para restaurar; variables/vacia.json para E08 |
| ConsultarCuentas | variables/continuidad.json |
| RegistrarMovimiento | variables/movimiento.json |

Las variables E06-*.json registran cada propuesta inválida. Los archivos contienen IDs reales de este laboratorio, obtenidos de la base; `ids.json` relaciona códigos y personas. En una instalación diferente, volver a obtener IDs con PuntoDePartida y `app.demo_activity4`, y actualizar el actor, rol y permisos por sus códigos. No copiar IDs suponiendo que siempre coincidirán.

S0 contiene accounts.read, concepts.read, transactions.read y transactions.write. S1 agrega accounts.write. La configuración inicial y final se guardan por códigos e incluyen los cuatro roles.

## Pruebas

Desde la raíz, no desde esta carpeta:

```bash
TEST_MYSQL=1 ./env/bin/python -m pytest -q
TEST_MYSQL=1 ./env/bin/python -m pytest -v -s tests/test_permission_sets.py::test_e07_rollback_after_flush
./env/bin/python -m pytest -q
./env/bin/python -m app.export_schema
./env/bin/python -m pip check
```

Las pruebas MySQL crean y eliminan únicamente bases aleatorias `ingresos_test_*`; no borran la base de la aplicación. E07 usa un mock interno después de flush y antes del commit, comprueba que se efectuaron las modificaciones dentro de la transacción y compara todas las relaciones desde una sesión nueva tras el error. No existe un parámetro público de fallos.

## Reproducir capturas

Instalar Playwright en un directorio local (`npm install playwright`) y tener Chromium disponible. Con la API activa y los datos demo preparados:

```bash
SETTINGS_FILE=.env.docker PYTHON="$PWD/env/bin/python" \
  ACTIVITY5_URL=http://127.0.0.1:8017/graphql \
  node scripts/activity5_evidence.cjs
# El recorrido se detiene después de vaciar CAPTURISTA.
# Detener y volver a iniciar el proceso API (o docker compose restart api).
AFTER_RESTART=1 SETTINGS_FILE=.env.docker PYTHON="$PWD/env/bin/python" \
  ACTIVITY5_URL=http://127.0.0.1:8017/graphql \
  node scripts/activity5_evidence.cjs
```

El recorrido asume la matriz S0 de partida y debe ejecutarse secuencialmente en un laboratorio sin otras ediciones. Genera capturas de GraphiQL y resultados SQL reales. Las capturas SQL utilizan un visor HTML, no MySQL Workbench. Las preparaciones E06 desactivan temporalmente Capturista o accounts.write y restauran su estado en finally; también se documentan en comprobaciones.sql. El resultado final vuelve a la matriz inicial.

## Archivos de entrega

`investigacion.md` contiene las cuatro respuestas y fuentes oficiales; `evidencias.md` explica E01-E10; `evidencias/registro.json` conserva consultas, variables, respuestas y resultados SQL. `configuracion_inicial.json` y `configuracion_final.json` permiten comparar la matriz por códigos.

El ZIP `unidad2_actividad5_equipo.zip` contiene el proyecto completo en ingresos/ y esta documentación en la raíz, según la organización solicitada. Se excluyen configuración privada, bases, entornos y cachés. El envío a Teams queda a cargo del estudiante.

## Resultado verificado

66 pruebas aprobadas en MySQL 8.4.11; 65 aprobadas y una omitida en SQLite. E07 pasó también por separado. Se registraron 55 capturas de GraphiQL/SQL y una captura adicional del test E07. La advertencia de deprecación de Starlette/AnyIO no impide la ejecución.
