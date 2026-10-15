# Evidencias · Unidad II · Actividad 4

Todas las operaciones GraphQL se ejecutaron contra MySQL real. Cada captura tiene la regla que demuestra. Los SELECT se conservan también en texto, JSON y un visor HTML de sus resultados reales.

| Evidencia | Regla demostrada |
|---|---|
| [Configuración inicial: cuatro roles](01-roles.png) | El catálogo contiene ADMINISTRADOR, CONTADOR, CAPTURISTA y CONSULTA. |
| [Configuración inicial: diez permisos](02-permisos.png) | Los permisos son acciones del catálogo; no pertenecen directamente a cada usuario. |
| [ADMINISTRADOR - lista inicial](03-administrador-inicial.png) | El administrador dispone de los diez permisos. |
| [CONTADOR - lista inicial](04-contador-inicial.png) | El contador tiene accounts.write, pero no roles.write. |
| [CAPTURISTA - lista inicial](05-capturista-inicial.png) | El capturista tiene transactions.write y todavía no tiene accounts.write. |
| [CONSULTA - lista inicial](06-consulta-inicial.png) | Consulta no tiene ningún permiso de escritura. |
| [Cinco personas, una empresa](07-cinco-personas.png) | Ana es administradora; Luis contador; María y José capturistas; Pedro consulta. |
| [María / CAPTURISTA: crear cuenta antes del cambio](08-maria-rechazada.png) | Sin accounts.write, el servidor rechaza createAccount antes de guardar. |
| [José / CAPTURISTA: crear cuenta antes del cambio](09-jose-rechazado.png) | José también recibe rechazo porque usa la misma lista del rol Capturista. |
| [Comprobación de las cuentas rechazadas](10-cuentas-no-guardadas.png) | Un rechazo no hace commit: las dos cuentas solicitadas no existen. |
| [Ana / ADMINISTRADOR: agrega accounts.write al capturista](11-ana-agrega-permiso.png) | Una modificación en role_permissions habilita la acción para todos los capturistas. |
| [Ana: no se duplica una pareja activa](12-pareja-duplicada.png) | assignPermissionToRole rechaza una relación que ya está activa. |
| [María / CAPTURISTA: cuenta después del cambio](13-maria-aceptada.png) | María crea una cuenta porque su rol ahora incluye accounts.write. |
| [José / CAPTURISTA: cuenta después del cambio](14-jose-aceptado.png) | José también crea una cuenta sin cambiar su ficha ni su asignación de rol. |
| [Ana: retira accounts.write del capturista](15-ana-quita-permiso.png) | removePermissionFromRole desactiva la pareja y conserva su historial. |
| [MySQL: la pareja permanece inactiva](16-pareja-inactiva.png) | La misma fila de CAPTURISTA + accounts.write existe con is_active=0; no fue borrada. |
| [María: rechazo después de retirar el permiso](17-maria-rechazada-otra-vez.png) | La revocación del permiso del rol alcanza a María. |
| [José: rechazo después de retirar el permiso](18-jose-rechazado-otra-vez.png) | La misma revocación alcanza a José sin editar a las personas. |
| [Pedro / CONSULTA: movimiento rechazado](19-pedro-rechazado.png) | Consulta permite ver movimientos, pero no registrarlos. |
| [MySQL: movimiento rechazado ausente](20-movimiento-no-guardado.png) | El rechazo de Pedro no agrega ninguna fila a transactions. |
| [Ana: cambia a Pedro de CONSULTA a CAPTURISTA](21-pedro-cambia-rol.png) | assignRole cambia el puesto de una sola persona. |
| [MySQL: historial y un solo rol activo de Pedro](22-pedro-un-rol-activo.png) | CONSULTA queda inactivo y CAPTURISTA queda activo; Pedro conserva exactamente un rol activo. |
| [Pedro / CAPTURISTA: movimiento aceptado](23-pedro-aceptado.png) | Con transactions.write en su nuevo rol, Pedro guarda el ingreso de 125.50. |
| [CONTADOR: lista después del cambio de Pedro](24-contador-sin-cambios.png) | La lista del contador es idéntica a la inicial; cambiar a Pedro no modifica a Luis. |
| [Luis / CONTADOR: todavía puede crear cuentas](25-luis-crea-cuenta.png) | Luis conserva accounts.write después de cambiar el rol de Pedro. |
| [CONSULTA: lista después del cambio de Pedro](26-consulta-sin-cambios.png) | La lista de Consulta conserva los mismos permisos y ninguno termina en .write. |
| [José / CAPTURISTA: intenta modificar CONSULTA](27-jose-no-administra.png) | José no tiene roles.write; el servidor rechaza su intento de agregar concepts.write. |
| [MySQL: José no modificó la lista](28-lista-no-modificada.png) | El intento de José no creó ni activó la pareja CONSULTA + concepts.write. |
| [Ana / ADMINISTRADOR: agrega concepts.write a CONSULTA](29-ana-si-administra.png) | Ana tiene roles.write y la misma operación sí se guarda. |
| [Ana: retira concepts.write de CONSULTA](30-ana-restaura-consulta.png) | Consulta vuelve a quedar sin permisos de escritura y se conserva la fila inactiva. |
| [SELECT final de role_permissions](31-select-final.png) | Las 26 relaciones activas coinciden con la matriz inicial; las dos pruebas retiradas permanecen inactivas. |
| [Catálogos antes de reiniciar](32-conteos-antes-reinicio.png) | Se conservan cuatro roles, diez permisos y 26 relaciones activas. |
| [MySQL después de reiniciar el servidor](33-catalogos-tras-reinicio.png) | El reinicio conserva 4 roles y 10 permisos; no duplica catálogos ni reactiva permisos retirados. |
| [Matriz final después del reinicio](34-matriz-tras-reinicio.png) | Después de reiniciar, la matriz activa sigue coincidiendo con la del documento y las dos parejas retiradas siguen inactivas. |

## Cierre

Después del reinicio: 4 roles, 10 permisos, 26 relaciones activas de la matriz original y 2 relaciones de prueba inactivas. Pedro conserva un solo rol activo y termina como CAPTURISTA.

No se guardó ninguna de las cuatro cuentas rechazadas, incluidas las dos posteriores a retirar el permiso. Sí se guardaron las dos cuentas autorizadas de los capturistas y la cuenta de Luis.

[Informe PDF](UnidadII_Actividad4_Informe.pdf) · [Operaciones y respuestas](operaciones.json) · [SELECT final](34-matriz-tras-reinicio.txt) · [SQL](select-final.sql)

## Validación adicional

40 pruebas de integración aprobadas en MySQL 8.4.7 y 1 prueba del contrato GraphQL aprobada: 41 comprobaciones distintas validadas. La prueba del contrato se reejecutó con sus archivos de referencia relativos presentes, después de que el primer recorrido aislado no los encontrara.

[Resumen de validación](validacion-pruebas.json) · [Log original de integración](pytest-mysql.txt) · [Log del contrato corregido](pytest-contrato.txt).
