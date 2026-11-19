# Unidad III · Actividad 2 · Dashboard administrativo

Se conserva la aplicación de la Unidad III, Actividad 1. Se agregan una protección por llave para `createTransaction` y el módulo administrativo de Usuarios, Cuentas y Conceptos, usando la misma API GraphQL y sesión JWT.

## Cómo iniciarlo en Windows (desde la raíz del repositorio)

Requisitos: Windows/PowerShell, Python 3.12 con acceso a pip, Docker Desktop (para MySQL) y un navegador. No incluir archivos `.env` al entregar. No ejecutar sobre una base de producción; respalda tu MySQL antes de probar.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.init_docker                # solo si .env.docker aún no existe
docker compose --env-file .env.docker up -d mysql
$env:SETTINGS_FILE = '.env.docker'
python -m app.init_db
python -m app.migrate_activity7         # en bases anteriores que lo necesiten
python -m app.migrate_unidad3_actividad2
python -m app.export_schema
python -m app.demo_activity7           # prepara SOLO el laboratorio de la actividad 7
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

> Nota: `app.init_docker` genera un `.env.docker` secreto y se niega a sobrescribir uno existente. El archivo no debe subirse a GitHub. Si el proyecto ya tiene datos y credenciales de práctica, no repitas el proceso de preparación sin revisar antes su documentación y respaldar la base.

En una segunda terminal (con Python disponible):

```powershell
python -m http.server 5500 --directory dashboard --bind 127.0.0.1
```

Abre `http://127.0.0.1:5500` y entra con el usuario de prueba. El servidor GraphiQL está en `http://127.0.0.1:8007/graphql`.

## Secciones

Desde el mismo login, el menú superior cambia entre **Dashboard financiero** y **Dashboard administrativo**. La administración ofrece: **Usuarios** (`companyUsers`, `createCompanyUser`, `deactivateCompanyUser`), **Cuentas** (`accounts`, `createAccount`) y **Conceptos** (`concepts`, `accountConcepts`, `createConcept`, `assignConceptToAccount`, `removeConceptFromAccount`).

`viewer` devuelve la empresa y permisos **derivados de la sesión autenticada**, por lo que la interfaz no inventa roles ni muestra botones de escritura al usuario que carece del permiso. El backend vuelve a validar cada operación. `CompanyUser.role` muestra el rol asignado; no modifica permisos.

El formulario de usuario solo pide nombre, correo y contraseña; no admite un segundo administrador principal. Las bajas son lógicas y conservan historial. La contraseña nunca se consulta en la tabla.

## Idempotencia

`createTransaction` admite `idempotencyKey`, una UUID generada por la acción del cliente. Una misma llave con el mismo contenido devuelve el movimiento original; una llave distinta permite otro movimiento idéntico; una misma llave con otros datos genera `CONFLICT`.

La tabla `idempotency_keys` contiene llave, empresa, operación, hash de petición e ID del movimiento. Su índice único usa `(company_id, operation, key)`. La inserción de la llave y del movimiento ocurre dentro de la misma transacción de base de datos; `execute` confirma ambos en un solo commit. La migración es aditiva. Se conserva el campo opcional por compatibilidad con clientes anteriores; todas las pruebas nuevas usan la llave.

### Demostración de GraphiQL

Copia este ejemplo y reemplaza los IDs por los datos reales de tu base. Debe ser un concepto **activo asignado** a una cuenta activa, del mismo tipo de movimiento. Genera dos UUID distintas (en PowerShell: `[guid]::NewGuid().ToString()`).

```graphql
mutation CrearMovimiento($input: CreateTransactionInput!) {
  createTransaction(input: $input) { id amount transactionType }
}
```

Variables para el primer envío (sustituye IDs y UUID):

```json
{
  "input": {
    "accountId": "ID_CUENTA",
    "conceptId": "ID_CONCEPTO_INGRESO",
    "transactionType": "INCOME",
    "amount": "100.00",
    "idempotencyKey": "11111111-1111-4111-8111-111111111111"
  }
}
```

Ejecuta **dos veces** sin cambiar nada: debe devolver el **mismo `id`**. Cambia únicamente `idempotencyKey`: crea **otro `id`**. Reutiliza la primera llave cambiando el monto: error `CONFLICT`.

Para consultar en MySQL (puedes hacerlo desde MySQL Workbench o el cliente de la base de prueba):

```sql
SELECT id, company_id, operation, `key`, transaction_id
FROM idempotency_keys ORDER BY id;
SELECT id, amount, account_id FROM transactions ORDER BY id DESC LIMIT 10;
```

## Pruebas de backend

Desde la raíz, con la base de pruebas aislada:

```powershell
python -m pytest tests/test_idempotency_u3.py -q
python -m pytest tests -q
```

La primera ejecución de tests usa SQLite temporal salvo que configures `TEST_MYSQL=1` con MySQL disponible. **Es obligatoria además una comprobación real con MySQL** para las evidencias del PDF. Algunas pruebas del contrato anterior se adaptaron para permitir los nuevos campos sin modificar los antiguos.

## Capturas que faltan para la entrega

- GraphiQL: dos envíos de `createTransaction` con misma llave y mismo ID.
- Usuarios: tabla con nombres/roles/estados obtenidos de MySQL; registrar y desactivar un usuario.
- Cuentas: cuenta nueva visible, con referencia enmascarada.
- Conceptos: catálogo y lista de conceptos por cuenta, alta y asignación.
- Error de correo duplicado o concepto ya asignado visible en la interfaz.
- Inicio de sesión de un rol de solo lectura, sin botones de alta.

Guardar las capturas reales (no inventadas) dentro de `docs/unidad3-actividad2/evidencias/` y documentar el rol usado para las pruebas. Si el boceto cambió frente a las figuras del PDF, incorporar el nuevo boceto.

## Estado de verificación

La copia se preparó con comprobaciones de sintaxis para Python y JavaScript y creación estructural de `idempotency_keys` con SQLite. **Las pruebas completas de GraphQL, MySQL y navegador quedan pendientes de ejecutar localmente** porque el entorno en el que se preparó la copia no tenía disponibles todas las dependencias Python ni un servidor MySQL. No considerar la entrega validada hasta completar las pruebas anteriores.
