# Unidad III · Actividad 3 · Matriz de roles y permisos

Continuación de los dashboards financiero y administrativo en `dashboard/`, con la misma API y sesión JWT. El menú **Dashboard administrativo → Roles y permisos** requiere `roles.read`. La matriz muestra cuatro puestos y diez permisos agrupados en Usuarios, Cuentas, Conceptos, Movimientos y Roles. Los nombres y concesiones vienen de MySQL; no hay una matriz de valores precargados en el cliente.

**Equipo:** Enrique Zavala, Marcelo Medina, Leonard Balmes, Armando Cen y Dylan Vazquez Soriano.

## Abrir y comprobar

Con el entorno Python del proyecto activado, instala `requirements.txt`. Conserva la configuración de las actividades anteriores. Si necesitas un laboratorio nuevo con MySQL y Docker:

```sh
python -m app.init_docker  # Solo si no existe .env.docker
docker compose --env-file .env.docker up -d mysql
export SETTINGS_FILE=.env.docker
python -m app.migrate_unidad3_actividad2
python -m app.demo_unidad3_actividad3
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

En otra terminal, desde el mismo repositorio:

```sh
python -m http.server 5500 --directory dashboard --bind 127.0.0.1
```

Abre <http://127.0.0.1:5500>. GraphiQL está en <http://127.0.0.1:8007/graphql>. `dashboard/config.js` define la URL del API. Para PowerShell, sustituye `export SETTINGS_FILE=.env.docker` por `$env:SETTINGS_FILE='.env.docker'`.

El preparador crea solo la empresa de práctica `U3-A3` y sus personas, una cuenta y un concepto. No restaura una matriz editada. Si detecta concesiones distintas de la matriz inicial, se detiene antes de crear el laboratorio: usa una base de práctica independiente. Al repetirlo sobre su laboratorio existente, no duplica datos. Las contraseñas aleatorias quedan únicamente en `.activity3-credentials.json`, ignorado por Git y excluido del ZIP. Consulta ese archivo local para iniciar sesión; no copies su contenido en evidencias.

| Usuario | Puesto | Comprobación |
| --- | --- | --- |
| `admin.actividad3@example.com` | Ana · Administrador | Editar columnas y asignar puestos |
| `contador.actividad3@example.com` | Luis · Contador | Matriz en solo lectura |
| `capturista.actividad3@example.com` | María · Capturista | Cuentas antes/después de `accounts.write` |
| `capturista2.actividad3@example.com` | José · Capturista | El mismo cambio afecta al segundo capturista |
| `consulta.actividad3@example.com` | Pedro · Consulta | Cambiar a Capturista y registrar un movimiento con la sesión existente |

1. Como Ana, abre la matriz y marca **Crear cuentas** en Capturista. **Vista previa** debe mostrar activar `accounts.write`, ninguna desactivación, cuatro sin cambio y total final cinco.
2. **Guardar columna** envía la lista completa de IDs y vuelve a consultar las relaciones. Repite vista previa y guardado: aparece `changed: false`.
3. En las sesiones de María y José, abre Cuentas: ambos ven **Nueva cuenta**. Al revocar esa concesión y guardar, el botón desaparece para ambos y la cuenta creada permanece.
4. En Usuarios, cambia Pedro de Consulta a Capturista con **Guardar rol**. `isAdmin` permanece en No y la columna Consulta no cambia. Pedro vuelve al dashboard financiero y ya puede **Registrar movimiento**, sin iniciar sesión otra vez.
5. Luis puede consultar la matriz; no puede editarla. María no ve Usuarios ni Roles y permisos. El API también rechaza las operaciones sin permiso.

## Persistencia y acceso

`roles`, `permissions` y una consulta `rolePermissions` por columna construyen la cuadrícula. Solo aparecen permisos activos del catálogo; ausencia o relación inactiva significa No. Administrador siempre queda deshabilitado. No hay altas de roles o permisos en esta pantalla.

`previewRolePermissions` no escribe. La edición posterior invalida la vista previa. `setRolePermissions` guarda la lista completa y conserva las filas desactivadas. `assignRole` se usa exclusivamente en Usuarios; muestra el resultado confirmado, conserva el puesto anterior si hay rechazo, deja un único rol activo y no cambia `isAdmin`.

El cliente envía `Authorization: Bearer …`. El backend vuelve a leer permisos y membresía en cada petición. `viewer` actualiza menú y acciones al navegar y al volver a la pestaña. El token vive en memoria y `sessionStorage`, sin permisos codificados dentro del JWT. El alta de movimiento conserva la llave de idempotencia de la actividad 2 al reintentar.

Al iniciar, se traducen únicamente los nombres de permisos que todavía eran iguales a su código; se conservan nombres personalizados y concesiones. También se corrige la detección de índices funcionales en MySQL para permitir reinicios sin intentar recrearlos.

## Verificación y entrega

```sh
python -m pytest tests -q
# MySQL de pruebas; cada fixture crea y elimina exclusivamente una base aleatoria propia:
TEST_MYSQL=1 python -m pytest tests/test_roles_dashboard_u3.py tests/test_permission_sets.py::test_preview_apply_repeat_reactivate tests/test_permission_sets.py::test_empty_survives_new_application tests/test_access.py::test_exact_matrix_and_membership_roles tests/test_jwt_access.py::test_nine_pdf_cases_with_same_pedro_token -q
node --check dashboard/app.js
```

`TEST_MYSQL_SETTINGS` permite indicar otro archivo de configuración en lugar de `.env.docker`, sin sobrescribirlo. Los resultados guardados identifican qué pruebas se ejecutaron con cada motor. Las [evidencias](evidencias.md) incluyen capturas reales del cliente y GraphiQL contra MySQL.

Para repetir las capturas, instala Playwright fuera de la entrega (`npm install --prefix /tmp/u3-browser playwright`) y ejecuta `PLAYWRIGHT_MODULE=/tmp/u3-browser/node_modules/playwright node scripts/activity3_evidence.cjs` con el API y dashboard encendidos y el laboratorio en su estado inicial. `CHROMIUM` permite indicar un ejecutable local. El script modifica y restaura únicamente la columna Capturista y el puesto de Pedro de este laboratorio; deja la cuenta y el movimiento de práctica como historial. Ejecutarlo en una base de práctica aislada porque la matriz se comparte entre empresas.

```sh
python scripts/package_unidad3_actividad3.py
```

Genera `entrega/unidad3_actividad3_equipo.zip` y su SHA-256, con cliente, backend, pruebas, README y evidencias. Excluye ambientes virtuales, `node_modules`, configuraciones privadas y JWT vigentes. Entrega ese ZIP y el enlace del repositorio en Teams.
