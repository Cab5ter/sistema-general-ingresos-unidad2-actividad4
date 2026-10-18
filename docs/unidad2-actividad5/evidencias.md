# Evidencias · Unidad II · Actividad 5

Ejecución con Python 3.12.14, MySQL Community Server 8.4.11 y API local 8017. Los datos pertenecen a una empresa ficticia. Se utilizó la membresía de Ana, identificada en `ids.json`; no se incluyeron contraseñas, tokens ni hashes. Las imágenes GraphiQL muestran peticiones ejecutadas en la API. Las imágenes SQL son un visor de resultados reales de SQLAlchemy, con su consulta y JSON disponibles; no son capturas de Workbench.

Cada registro de `evidencias/registro.json` contiene operación, variables y respuesta, o la consulta SQL y todas sus filas. Las variables de las peticiones están también en `variables/`. La verificación compara IDs, parejas y estados, no solo conteos.

## E01. Punto de partida

**Precondición:** Catálogos cargados, Ana con ADMINISTRADOR y Capturista en S0.

**Operación y variables:** Consultar roles y permisos y ejecutar el SELECT de relaciones.

**Esperado:** Cuatro roles, diez permisos y cuatro concesiones de Capturista.

**Obtenido:** Se observaron los cuatro roles y diez permisos; la matriz activa inicial se exportó por códigos a configuracion_inicial.json.

**Regla demostrada:** La inicialización conserva la matriz y las concesiones reales.

### E01-inicial

![E01-inicial](evidencias/E01-inicial.png)

[Filas y consulta SQL completas](evidencias/E01-inicial.json).

### E01-catalogos

![E01-catalogos](evidencias/E01-catalogos.png)

### E01-roles-completo

![E01-roles-completo](evidencias/E01-roles-completo.png)

### E01-permissions-completo

![E01-permissions-completo](evidencias/E01-permissions-completo.png)


## E02. Catálogo

**Precondición:** Matriz inicial, los diez permisos activos.

**Operación y variables:** ExplorarCatalogo usa variables, alias cuentas/movimientos y el fragmento DatosPermiso. Consultar sin recurso y enviar PAYMENTS.

**Esperado:** Dos permisos por grupo, diez sin filtro y errors para PAYMENTS.

**Obtenido:** Los dos grupos tienen dos permisos; el catálogo completo tiene diez y PAYMENTS produce error de validación del enum.

**Regla demostrada:** El filtro consulta SQL y el enum restringe recursos antes del resolver.

### E02-alias-fragmento

![E02-alias-fragmento](evidencias/E02-alias-fragmento.png)

### E02-sin-filtro

![E02-sin-filtro](evidencias/E02-sin-filtro.png)

### E02-enum-invalido

![E02-enum-invalido](evidencias/E02-enum-invalido.png)


## E03. Previsualización sin escritura

**Precondición:** Capturista en S0; propuesta S1.

**Operación y variables:** Ejecutar RevisarConfiguracion con s1.json y comparar SELECT antes y después.

**Esperado:** accounts.write por activar, ninguna desactivación, cuatro sin cambio y finalCount 5.

**Obtenido:** La respuesta coincide y todas las filas SQL son idénticas antes y después.

**Regla demostrada:** Previsualizar solo calcula; no guarda ni reserva una configuración.

### E03-antes

![E03-antes](evidencias/E03-antes.png)

[Filas y consulta SQL completas](evidencias/E03-antes.json).

### E03-previsualizar

![E03-previsualizar](evidencias/E03-previsualizar.png)

### E03-despues

![E03-despues](evidencias/E03-despues.png)

[Filas y consulta SQL completas](evidencias/E03-despues.json).


## E04. Aplicación e idempotencia

**Precondición:** Capturista en S0.

**Operación y variables:** AplicarConfiguracion con s1.json dos veces, separadamente.

**Esperado:** Primera changed true; segunda changed false, sin altas/bajas, total cinco y mismos IDs.

**Obtenido:** La primera activa accounts.write; la segunda no cambia las filas. No hay parejas duplicadas.

**Regla demostrada:** Establecer la misma lista es idempotente.

### E04-primera

![E04-primera](evidencias/E04-primera.png)

### E04-sql-primera

![E04-sql-primera](evidencias/E04-sql-primera.png)

[Filas y consulta SQL completas](evidencias/E04-sql-primera.json).

### E04-repetida

![E04-repetida](evidencias/E04-repetida.png)

### E04-sql-repetida

![E04-sql-repetida](evidencias/E04-sql-repetida.png)

[Filas y consulta SQL completas](evidencias/E04-sql-repetida.json).


## E05. Desactivación y reactivación

**Precondición:** S1 ya aplicada.

**Operación y variables:** Aplicar s0.json y después s1.json, con SELECT en cada momento.

**Esperado:** accounts.write queda inactivo y vuelve a activo en la misma fila; Permission permanece activo.

**Obtenido:** El mismo relacion_id aparece antes, durante y después. Solo cambia relacion_activa; permiso_activo sigue siendo 1.

**Regla demostrada:** La revocación es lógica y la reactivación reutiliza la pareja.

### E05-desactivar

![E05-desactivar](evidencias/E05-desactivar.png)

### E05-inactiva

![E05-inactiva](evidencias/E05-inactiva.png)

[Filas y consulta SQL completas](evidencias/E05-inactiva.json).

### E05-reactivar

![E05-reactivar](evidencias/E05-reactivar.png)

### E05-reactivada

![E05-reactivada](evidencias/E05-reactivada.png)

[Filas y consulta SQL completas](evidencias/E05-reactivada.json).


## E06. Entradas inválidas

**Precondición:** Capturista en S1; catálogos restaurados tras cada variante.

**Operación y variables:** Ejecutar las seis variantes en preview y set; las variables E06-*.json registran las entradas.

**Esperado:** Todas producen errors y conservan íntegra la configuración de relaciones.

**Obtenido:** Las doce peticiones devolvieron errores descriptivos y ninguna cambió IDs, parejas o estados. Los UPDATE de preparación y restauración están en comprobaciones.sql; activity5_state.py los ejecuta de forma controlada.

**Regla demostrada:** Se valida antes de modificar y ambas operaciones comparten las mismas reglas.

| Variante | Resultado de preview y set | Preparación/restauración |
|---|---|---|
| Rol inexistente | NOT_FOUND | ID 999999 |
| Rol inactivo | BAD_INPUT | CAPTURISTA 0 y luego 1 |
| ADMINISTRADOR | FORBIDDEN | Sin preparación |
| Permiso inexistente mezclado con válidos | NOT_FOUND | ID 999999 junto con S1 |
| Permiso inactivo | BAD_INPUT | accounts.write 0 y luego 1 |
| ID repetido | BAD_INPUT | Incluye el ID como texto y como entero |

### E06-rol-inexistente-antes

![E06-rol-inexistente-antes](evidencias/E06-rol-inexistente-antes.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inexistente-antes.json).

### E06-rol-inexistente-preview

![E06-rol-inexistente-preview](evidencias/E06-rol-inexistente-preview.png)

### E06-rol-inexistente-aplicar

![E06-rol-inexistente-aplicar](evidencias/E06-rol-inexistente-aplicar.png)

### E06-rol-inexistente-despues

![E06-rol-inexistente-despues](evidencias/E06-rol-inexistente-despues.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inexistente-despues.json).

### E06-rol-inactivo-preparacion

![E06-rol-inactivo-preparacion](evidencias/E06-rol-inactivo-preparacion.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inactivo-preparacion.json).

### E06-rol-inactivo-antes

![E06-rol-inactivo-antes](evidencias/E06-rol-inactivo-antes.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inactivo-antes.json).

### E06-rol-inactivo-preview

![E06-rol-inactivo-preview](evidencias/E06-rol-inactivo-preview.png)

### E06-rol-inactivo-aplicar

![E06-rol-inactivo-aplicar](evidencias/E06-rol-inactivo-aplicar.png)

### E06-rol-inactivo-despues

![E06-rol-inactivo-despues](evidencias/E06-rol-inactivo-despues.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inactivo-despues.json).

### E06-rol-inactivo-restauracion

![E06-rol-inactivo-restauracion](evidencias/E06-rol-inactivo-restauracion.png)

[Filas y consulta SQL completas](evidencias/E06-rol-inactivo-restauracion.json).

### E06-administrador-antes

![E06-administrador-antes](evidencias/E06-administrador-antes.png)

[Filas y consulta SQL completas](evidencias/E06-administrador-antes.json).

### E06-administrador-preview

![E06-administrador-preview](evidencias/E06-administrador-preview.png)

### E06-administrador-aplicar

![E06-administrador-aplicar](evidencias/E06-administrador-aplicar.png)

### E06-administrador-despues

![E06-administrador-despues](evidencias/E06-administrador-despues.png)

[Filas y consulta SQL completas](evidencias/E06-administrador-despues.json).

### E06-permiso-inexistente-antes

![E06-permiso-inexistente-antes](evidencias/E06-permiso-inexistente-antes.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inexistente-antes.json).

### E06-permiso-inexistente-preview

![E06-permiso-inexistente-preview](evidencias/E06-permiso-inexistente-preview.png)

### E06-permiso-inexistente-aplicar

![E06-permiso-inexistente-aplicar](evidencias/E06-permiso-inexistente-aplicar.png)

### E06-permiso-inexistente-despues

![E06-permiso-inexistente-despues](evidencias/E06-permiso-inexistente-despues.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inexistente-despues.json).

### E06-permiso-inactivo-preparacion

![E06-permiso-inactivo-preparacion](evidencias/E06-permiso-inactivo-preparacion.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inactivo-preparacion.json).

### E06-permiso-inactivo-antes

![E06-permiso-inactivo-antes](evidencias/E06-permiso-inactivo-antes.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inactivo-antes.json).

### E06-permiso-inactivo-preview

![E06-permiso-inactivo-preview](evidencias/E06-permiso-inactivo-preview.png)

### E06-permiso-inactivo-aplicar

![E06-permiso-inactivo-aplicar](evidencias/E06-permiso-inactivo-aplicar.png)

### E06-permiso-inactivo-despues

![E06-permiso-inactivo-despues](evidencias/E06-permiso-inactivo-despues.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inactivo-despues.json).

### E06-permiso-inactivo-restauracion

![E06-permiso-inactivo-restauracion](evidencias/E06-permiso-inactivo-restauracion.png)

[Filas y consulta SQL completas](evidencias/E06-permiso-inactivo-restauracion.json).

### E06-duplicado-antes

![E06-duplicado-antes](evidencias/E06-duplicado-antes.png)

[Filas y consulta SQL completas](evidencias/E06-duplicado-antes.json).

### E06-duplicado-preview

![E06-duplicado-preview](evidencias/E06-duplicado-preview.png)

### E06-duplicado-aplicar

![E06-duplicado-aplicar](evidencias/E06-duplicado-aplicar.png)

### E06-duplicado-despues

![E06-duplicado-despues](evidencias/E06-duplicado-despues.png)

[Filas y consulta SQL completas](evidencias/E06-duplicado-despues.json).


## E07. Reversión tras escrituras pendientes

**Precondición:** Base temporal MySQL creada por el fixture; Capturista en S0.

**Operación y variables:** Ejecutar test_e07_rollback_after_flush con TEST_MYSQL=1. El mock de check_before_commit llama flush, comprueba cero concesiones activas dentro de la transacción y lanza RuntimeError.

**Esperado:** Error GraphQL y rollback de las escrituras; sesión nueva igual al estado previo.

**Obtenido:** La prueba automatizada pasa y registra todas las filas ANTES y DESPUES desde una sesión nueva en E07-test.txt. El estado persistido coincide exactamente.

**Regla demostrada:** Atomicidad: un fallo después de flush y antes de commit no deja cambios parciales.

[Salida completa del test](evidencias/E07-test.txt) · [JUnit](evidencias/E07-junit.xml)

![E07: prueba real de rollback](evidencias/E07-test.png)


## E08. Lista vacía y reinicio real

**Precondición:** Capturista en S1.

**Operación y variables:** Aplicar vacia.json; detener el proceso Uvicorn y lanzar uno nuevo con la misma configuración; consultar de nuevo.

**Esperado:** Cero concesiones activas antes y después; filas conservadas y cuatro roles/diez permisos.

**Obtenido:** La respuesta deja finalCount 0; SQL antes y después del nuevo proceso tiene las mismas filas inactivas. La consulta reiniciada devuelve current [].

**Regla demostrada:** El arranque distingue la configuración vacía de la falta de inicialización.

### E08-vaciar

![E08-vaciar](evidencias/E08-vaciar.png)

### E08-antes-reinicio

![E08-antes-reinicio](evidencias/E08-antes-reinicio.png)

[Filas y consulta SQL completas](evidencias/E08-antes-reinicio.json).

### E08-despues-reinicio

![E08-despues-reinicio](evidencias/E08-despues-reinicio.png)

[Filas y consulta SQL completas](evidencias/E08-despues-reinicio.json).

### E08-consulta-reiniciada

![E08-consulta-reiniciada](evidencias/E08-consulta-reiniciada.png)


[Registro del nuevo arranque de la API](evidencias/E08-arranque.txt).

## E09. Restauración

**Precondición:** Capturista vacío tras el reinicio.

**Operación y variables:** Aplicar s0.json, exportar la matriz activa de los cuatro roles y comprobar duplicados.

**Esperado:** Matriz final igual a configuracion_inicial.json y cero parejas duplicadas.

**Obtenido:** configuracion_final.json coincide exactamente por códigos con la inicial. Se conservan las filas históricas inactivas adicionales.

**Regla demostrada:** Las pruebas restauran la configuración inicial sin borrar historia.

### E09-restaurar

![E09-restaurar](evidencias/E09-restaurar.png)

### E09-matriz-final

![E09-matriz-final](evidencias/E09-matriz-final.png)

[Filas y consulta SQL completas](evidencias/E09-matriz-final.json).


## E10. Continuidad financiera

**Precondición:** Matriz restaurada, Ana activa, cuenta y concepto INCOME relacionados en la misma empresa.

**Operación y variables:** ConsultarCuentas y RegistrarMovimiento con los JSON continuidad y movimiento. SELECT del ID devuelto.

**Esperado:** Consulta válida y movimiento de 125.50 persistido con cuenta y concepto válidos.

**Obtenido:** La cuenta se devuelve en GraphQL y el movimiento aparece en MySQL con importe exacto 125.50, la cuenta y concepto de la empresa y capturedBy generado por el servidor.

**Regla demostrada:** Las operaciones previas siguen funcionando y conservan las reglas financieras.

### E10-cuentas

![E10-cuentas](evidencias/E10-cuentas.png)

### E10-movimiento

![E10-movimiento](evidencias/E10-movimiento.png)

### E10-movimiento-persistido

![E10-movimiento-persistido](evidencias/E10-movimiento-persistido.png)

[Filas y consulta SQL completas](evidencias/E10-movimiento-persistido.json).


## Comprobación automatizada

La suite completa incluye los contratos anteriores y las nuevas reglas. Véanse [resultado MySQL](evidencias/pytest-mysql.txt), [JUnit completo](evidencias/pytest-mysql.xml) y [pruebas de compatibilidad SQLite](evidencias/pytest-sqlite.txt). La prueba E07 se ejecutó también por separado con salida detallada.

Resultado final: **66 aprobadas en MySQL; 65 aprobadas y una omitida en SQLite**. [Respuestas de la suite MySQL](evidencias/graphql-mysql.json) · [Respuestas SQLite](evidencias/graphql-sqlite.json).
