# Unidad II · Actividad 7 · Gestión de balances

**Equipo:** Enrique Zavala, Marcelo Medina y Dylan Vazquez Soriano.

**Repositorio:** https://github.com/Cab5ter/sistema-general-ingresos-unidad2-actividad4

Esta entrega amplía el proyecto de la actividad 6: conserva login, JWT de 30 minutos, membresías, cuatro roles y permisos actuales. Implementa el contrato de la página 5 del PDF, con Python, Strawberry, SQLAlchemy y MySQL. La actividad también aparece como #10 de la planeación; el archivo de entrega se llama `unidad2_actividad7_equipo.zip`.

## Archivos y cambios

- `app/balances.py`: servicio compartido, una agregación SQL por consulta y detalle ordenado por ID.
- `app/balance_schema.py`: tipos `AccountBalance`, `GeneralBalance` y consultas con fechas obligatorias.
- `app/finance_schema.py`: escalar `DateTime` para `transactionDate` y `capturedAt`; Decimal serializado a dos decimales.
- `app/finance_service.py`: solo montos positivos, finitos, hasta 9,999,999,999.99 y representables en centavos. Rechaza 1.239; no lo redondea. `1.230` representa exactamente 1.23 y es válido.
- `app/finance_models.py`: `Numeric(12, 2)` en MySQL e índice de cuenta, estado y fecha. SQLite conserva TEXT y un agregado decimal exacto únicamente como alternativa de pruebas.
- `app/migrate_activity7.py`: valida todos los importes históricos antes de convertir el TEXT de actividades anteriores. No modifica cantidades para forzar resultados.
- `app/demo_activity7.py`: preparación y restauración acotada al laboratorio; no altera empresas reales.
- `tests/test_balances.py`: B01-B15 automatizados por HTTP, más límites de montos y fechas inválidas.
- `tests/test_balance_migration.py`: migración idempotente, rechazo sin redondear y conservación del historial de un capturista desactivado.
- [Operaciones](operaciones.graphql), [variables](variables), [IDs de la ejecución](ids.json), [evidencias](evidencias.md), [explicación](explicacion.md).

El campo anterior `accountBalance(accountId): Decimal!` se sustituye por el contrato exigido: ahora recibe `fromDate` y `toDate`, y requiere selección de campos. Se actualizaron las pruebas de ese contrato y el error de cuenta ajena. El resto de la API se conserva.

## Instalar e iniciar desde cero (PowerShell)

Requisitos: Python 3.12, MySQL 8.4 y las dependencias fijadas en `requirements.txt`. Docker es opcional; se incluye una ruta con Docker para reproducir el ambiente.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.init_docker
docker compose --env-file .env.docker up -d mysql
$env:SETTINGS_FILE = '.env.docker'
python -m app.init_db
python -m app.migrate_activity7
python -m app.demo_activity7
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

Espera a que MySQL esté saludable antes de `init_db`. `init_docker` crea secretos aleatorios en un archivo ignorado y se niega a sobrescribirlo. Si ya existe, reutilízalo. La API del ejemplo corre en Python local; no hace falta iniciar además el servicio `api` de Docker.

Sin Docker, crea una base MySQL propia y configura `DATABASE_URL`, `JWT_SECRET` y `BOOTSTRAP_KEY` en `.env`, tomando `.env.example` como referencia. Ambas claves deben ser diferentes y tener al menos 32 caracteres. Ejecuta los comandos desde `app.init_db` en adelante, sin definir `SETTINGS_FILE=.env.docker`.

### Actualizar la base de la actividad 6

1. Respalda la base y detén los procesos que escriben en ella.
2. Configura el ambiente para esa base y ejecuta `python -m app.migrate_activity7`.
3. Si hay valores con precisión adicional, no positivos o fuera del rango, la migración se cancela antes del ALTER e informa los IDs. Conserva los datos originales y resuelve su tratamiento antes de migrar; no los redondees para aprobar la práctica.
4. Reinicia la API. El inicio verifica que MySQL ya use DECIMAL(12,2).

MySQL hace commit implícito de DDL: ejecuta la migración en mantenimiento. La validación no transforma importes. El índice se crea solo si falta. En bases nuevas ya lo crea el modelo. No se agrega tabla de balances ni columna de saldo.

## Preparar, consultar y restaurar el laboratorio

`python -m app.demo_activity7` crea tres empresas separadas (A, B y vacía), un administrador de cada una y un usuario CONSULTA de A. Crea Banco, Caja y Ahorro en A, relaciona los conceptos INCOME/EXPENSE y captura **solo los seis movimientos del PDF**, todos a las 12:00 UTC. El ingreso de apertura del 25 se registra una única vez. Los datos del día 29 son intencionalmente datos de prueba.

La preparación escribe los IDs reales y las variables. No asumas que los IDs de otra instalación coincidirán con los versionados. Al repetirla, detecta el laboratorio existente y no duplica movimientos. Las contraseñas aleatorias quedan solo en `.activity7-credentials.json`, ignorado por Git y por el ZIP.

Abre http://127.0.0.1:8007/graphql y copia las operaciones de `operaciones.graphql`:

1. Ejecuta `IniciarSesion` con `input.email = admin.actividad7@example.com` y la contraseña `admin` del archivo privado. El JSON de login tiene la forma `{"input":{"email":"admin.actividad7@example.com","password":"CONTRASEÑA_LOCAL"}}`.
2. Coloca `{"Authorization":"Bearer TOKEN_OBTENIDO_EN_LOGIN"}` en **Headers**. No publiques ese encabezado.
3. Ejecuta `BalanceDeUnaCuenta` con `variables/banco.json`, `caja.json` y `ahorro.json`.
4. Ejecuta `BalanceDeLaEmpresa` con `variables/general.json`.
5. Repite la consulta de Banco con `variables/banco-dia28.json`.
6. Para el rol CONSULTA, inicia sesión con `consulta.actividad7@example.com` y su contraseña local. Puede leer ambas consultas, pero `createTransaction` se rechaza.

Para restaurar **exclusivamente** el laboratorio A después de modificaciones de prueba:

```powershell
python -m app.demo_activity7 --restore
```

Comprueba el marcador `U2-A7-A` y los IDs de sus tres cuentas, borra sus movimientos de prueba, reactiva sus cuentas/conceptos/relaciones y vuelve a capturar los seis originales. No uses ese comando para conservar movimientos adicionales del laboratorio; estos se reemplazan. No modifica otras empresas ni restablece permisos globales. B14 restaura el permiso en un bloque `finally` de la prueba.

## Ejecutar las pruebas y generar evidencia

Las pruebas crean una base temporal **por caso** y la eliminan al terminar. Necesitan las credenciales root de **la instancia de prueba** en `.env.docker` (`MYSQL_ROOT_PASSWORD` y `MYSQL_PORT`); no se ejecutan contra las tablas de la empresa de demostración. B01, B04, B06 y B12 están automatizados, al igual que los otros once casos.

```powershell
$env:TEST_MYSQL = '1'
$env:EVIDENCE_DIR = 'docs/unidad2-actividad7/evidencias'
python -m pytest -q --tb=short --junitxml=docs/unidad2-actividad7/evidencias/pytest-mysql.xml *> docs/unidad2-actividad7/evidencias/pytest-mysql.txt
python scripts/activity7_reference.py
python scripts/activity7_report.py
```

Revisar el código de salida de pytest: debe ser 0. `activity7_reference.py` requiere la API local iniciada y el laboratorio preparado; por defecto consulta el puerto 8007, o el definido en `GRAPHQL_URL`. Para un caso concreto: `python -m pytest tests/test_balances.py -k B04 -v`. Una ejecución parcial no sustituye la evidencia de la suite completa. El JSON registra operaciones, variables, respuestas y estados; oculta contraseñas y tokens, y no registra encabezados HTTP.

SQLite permite una comprobación adicional: elimina `TEST_MYSQL` del ambiente y ejecuta pytest. **La evidencia principal de esta entrega corresponde a MySQL 8.4.13**, con SUM sobre DECIMAL real.

## Reglas verificadas

- Todas las cantidades son MXN. Las cuentas comienzan en cero. El saldo de apertura se representa mediante un movimiento, nunca se duplica en otro campo.
- `fromDate` y `toDate` son Date obligatorios, inclusive ambos días UTC. Para 26-30: inicio `2026-10-26T00:00:00Z`, fin exclusivo `2026-10-31T00:00:00Z`. Se admiten consultas de un solo día.
- `transactionDate` lleva zona y se normaliza a UTC. La columna DATETIME(6) representa UTC sin zona almacenada. Las filas previas deben seguir esa misma convención. `capturedAt` siempre lo decide el servidor.
- El LEFT JOIN filtra movimientos activos y anteriores al fin en ON, por lo que no desaparecen cuentas vacías. No se une con conceptos para sumar: agregar otra relación no duplica dinero.
- Cuentas desactivadas conservan su historial; conceptos, relaciones o capturistas inactivos tampoco anulan movimientos. Solo `Transaction.is_active` excluye el movimiento.
- El general suma el mismo detalle, sin consultas adicionales por cuenta. Los importes vacíos son `"0.00"`. Los agregados pueden superar el máximo de una transacción.
- Ambas consultas validan el token, la membresía activa y **los dos permisos** actuales. `companyId` viene de la sesión y no es un argumento. Una cuenta ajena y una inexistente responden `Cuenta no disponible.` sin nombres ni importes.

## Entrega

```powershell
python scripts/package_activity7.py
```

Genera `entrega/unidad2_actividad7_equipo.zip`, revisa su integridad y excluye secretos, entornos, bases y cachés. Entrega ese ZIP y el enlace del repositorio en Teams. El envío a Teams lo realiza el estudiante.

Referencias técnicas: [agregaciones SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/functions.html), [escalares de Strawberry](https://strawberry.rocks/docs/types/scalars), [MySQL en Windows](https://dev.mysql.com/doc/refman/8.4/en/windows-installation.html). El enunciado académico es `unidad2_actividad_7.pdf`, páginas 1-9.
