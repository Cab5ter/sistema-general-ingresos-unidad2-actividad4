# Unidad II · Actividad 4

Configuración de permisos para diferentes roles del Sistema General de Ingresos. Se continúa el código de la actividad 3: la lista vive en `role_permissions`, la asignación de una persona en `company_user_roles` y la validación central en `app/access.py`, mediante `exigir_permiso`.

## Entrega y evidencias

- [Informe con una regla junto a cada captura](evidencias/unidad2-actividad4/UnidadII_Actividad4_Informe.pdf).
- [Índice de las capturas](evidencias/unidad2-actividad4/README.md).
- [Operaciones GraphQL y respuestas reales](evidencias/unidad2-actividad4/operaciones.json).
- [IDs de las cinco personas y catálogos](evidencias/unidad2-actividad4/ids.json).
- [SELECT final después del reinicio](evidencias/unidad2-actividad4/34-matriz-tras-reinicio.txt).
- [Consulta SQL para verificarlo](evidencias/unidad2-actividad4/select-final.sql).

Ana: ADMINISTRADOR e `isAdmin=true`. Luis: CONTADOR. María y José: CAPTURISTA. Pedro: CONSULTA al iniciar y CAPTURISTA al terminar. Todas las personas pertenecen a la empresa de demostración de la actividad 4.

## Resultado

María y José reciben rechazo al crear cuentas. Ana agrega `accounts.write` a CAPTURISTA una sola vez y los dos crean cuentas sin editar sus membresías. Ana retira el permiso y ambos vuelven a recibir rechazo. La misma pareja permanece en MySQL con `is_active=0`.

Pedro no registra movimientos como CONSULTA y no se guarda la fila rechazada. Ana usa `assignRole` y Pedro registra un ingreso de 125.50 como CAPTURISTA. La asignación anterior queda inactiva y Pedro conserva un solo rol activo. Las listas de CONTADOR y CONSULTA permanecen idénticas; Luis sigue creando cuentas.

José no puede agregar `concepts.write` a CONSULTA porque carece de `roles.write`. MySQL confirma que su intento no activó la pareja. Ana sí agrega el permiso y luego lo retira. La matriz final activa vuelve a coincidir con la tabla del documento: 26 relaciones activas. Se conservan 2 relaciones de prueba inactivas, que no conceden acceso.

Se detuvo y arrancó de nuevo el servidor Python. Después del reinicio siguen existiendo exactamente 4 roles y 10 permisos, con las mismas 26 relaciones activas y 2 inactivas.

## Entorno comprobado

Ejecución de esta entrega: Python 3.12.14, las versiones del `requirements.txt`, MySQL Community Server 8.4.7 local, base independiente de demostración, MySQL en 3317 y API en `http://127.0.0.1:8017/graphql`. Se usó MySQL local porque Docker no resultó accesible desde el entorno de herramientas. Se conserva el Docker Compose del proyecto para reproducirlo con los mismos servicios.

Python 3.14 no arranca con las versiones fijadas de Strawberry y SQLAlchemy. Para esta entrega se recomienda Python 3.12; el README previo documenta Python 3.13.

Las imágenes de GraphiQL son capturas de operaciones ejecutadas contra la API real. Las imágenes SQL son capturas de un visor HTML de resultados reales de SELECT ejecutados con SQLAlchemy contra MySQL. Cada SELECT también se entrega como texto y JSON; no se presenta el visor como MySQL Workbench.

## Reproducir con Docker

Desde la raíz del mismo proyecto, con Python 3.12 y Docker funcionando:

```bash
python3.12 -m venv env
./env/bin/python -m pip install -r requirements.txt
# Solo si todavía no existe; no reemplazar una configuración privada anterior:
./env/bin/python -m app.init_docker
docker compose --env-file .env.docker up -d --build
SETTINGS_FILE=.env.docker ./env/bin/python -m app.demo_activity4
```

Estos comandos recién inicializados usan los puertos predeterminados 8007 y 3307. Si `.env.docker` ya existe con otros puertos, usa su `API_PORT` en `ACTIVITY4_URL`. Por ejemplo, para la configuración local comprobada de esta entrega:

```bash
SETTINGS_FILE=.env.docker ACTIVITY4_URL=http://127.0.0.1:8017/graphql \
  ./env/bin/python -m app.demo_activity4
```

El script prepara la empresa mediante `createCompany`, `createCompanyAdmin`, `createCompanyUser`, `assignRole`, `createAccount`, `createConcept` y `assignConceptToAccount`. Reutiliza las personas ya preparadas. Las contraseñas se generan y guardan en `.activity4-credentials.json`, que se excluye de Git y del ZIP.

Para capturas automáticas, instala Playwright en una carpeta local y proporciona su módulo y el ejecutable Chromium. El recorrido verifica la matriz inicial antes de modificar permisos y guarda una imagen por comprobación:

```bash
npm install --prefix /tmp/actividad4-browser playwright
SETTINGS_FILE=.env.docker \
  ACTIVITY4_URL=http://127.0.0.1:8007/graphql \
  PYTHON="$PWD/env/bin/python" \
  PLAYWRIGHT_MODULE=/tmp/actividad4-browser/node_modules/playwright \
  CHROMIUM=/usr/bin/chromium \
  node scripts/activity4_evidence.cjs
docker compose --env-file .env.docker restart api
# Esperar a que /graphql responda y repetir las mismas variables:
SETTINGS_FILE=.env.docker AFTER_RESTART=1 \
  ACTIVITY4_URL=http://127.0.0.1:8007/graphql \
  PYTHON="$PWD/env/bin/python" \
  PLAYWRIGHT_MODULE=/tmp/actividad4-browser/node_modules/playwright \
  CHROMIUM=/usr/bin/chromium \
  node scripts/activity4_evidence.cjs
```

También se pueden ejecutar manualmente las operaciones guardadas en `operaciones.json`, en su orden, con los IDs de una instalación nueva. No se incluyen claves privadas, contraseñas, bases ni entornos virtuales en la entrega.

Para comprobar permisos, integridad y aislamiento entre empresas con la suite existente:

```bash
TEST_MYSQL=1 ./env/bin/python -m pytest -v
./env/bin/python -m pip check
```

Para reconstruir el ZIP del código y las evidencias disponibles:

```bash
./env/bin/python scripts/package_activity4.py
```

El empaquetador revisa integridad, compara los contenidos con los secretos locales y agrega un manifiesto SHA-256. El ZIP aparece en `entrega/UnidadII_Actividad4_Permisos.zip`.

## Validación de esta entrega

40 pruebas de integración aprobadas en MySQL 8.4.7 y 1 prueba de contrato GraphQL aprobada. La prueba de contrato se reejecutó después de copiar sus archivos de referencia a la carpeta aislada de pruebas. Se conservan los logs originales, XML y el resumen de ambas ejecuciones en el directorio de evidencias nuevo. `pip check` confirmó que no hay requisitos rotos.
