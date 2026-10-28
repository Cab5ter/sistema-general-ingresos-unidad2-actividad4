# Evidencias · Unidad II · Actividad 7

**Equipo:** Enrique Zavala, Marcelo Medina y Dylan Vazquez Soriano.

Todos los casos se ejecutaron por HTTP GraphQL contra bases MySQL temporales independientes. Las expectativas están escritas a partir de los datos, sin invocar el servicio para construir los valores esperados.

| Caso | Estado real | Resultado obtenido y comprobado | Regla comprobada |
|---|---|---|---|
| B01 | PASÓ | Banco 1800.00; Caja -200.00; Ahorro 0.00; general 1600.00; 1 cuenta en rojo. Filas idénticas antes/después. | El saldo inicial proviene de movimientos previos; consultar no escribe. |
| B02 | PASÓ | Banco el 28: apertura 2800.00, ingresos 0.00, egresos 1000.00, profit -1000.00, cierre 1800.00, sin rojo. | Profit negativo no implica saldo final negativo. |
| B03 | PASÓ | Lista vacía; importes 0.00; accountsInRed 0; isInRed false. | Una empresa sin cuentas tiene un resultado definido. |
| B04 | PASÓ | Apertura 10.00; ingresos 50.01; cierre 60.01. El ingreso de 999.00 del 31 queda fuera. | Inicio incluido, fin exclusivo; incluye también 23:59:59.999999. |
| B05 | PASÓ | Operación del 27 a las 12:00 UTC, capturada después: ingreso y cierre del 27 por 20.00. | Se usa transactionDate normalizada a UTC, no capturedAt. |
| B06 | PASÓ | Ingresos 0.30, egresos 0.30, profit y cierre 0.00, sin rojo. | 0.10 + 0.20 - 0.30 se calcula exactamente. |
| B07 | PASÓ | Se inactiva un egreso de 1000.00: Banco cierra en 2800.00; permanecen seis filas. | Solo el movimiento desactivado deja de participar. |
| B08 | PASÓ | Banco desactivado conserva 1800.00 y el general 1600.00; isActive false. | El estado de la cuenta y sus relaciones no borra el historial. |
| B09 | PASÓ | Se agrega otro concepto permitido y el balance general no cambia. | No se multiplican movimientos por relaciones cuenta-concepto. |
| B10 | PASÓ | Ambas consultas rechazan intervalo invertido, fecha inexistente y fecha máxima sin día siguiente. | Las fechas inválidas no producen un balance ni escrituras. |
| B11 | PASÓ | Ambas consultas rechazan ausencia de token, firma alterada y vencimiento. | La identidad se valida antes de devolver datos. |
| B12 | PASÓ | Cuenta ajena e inexistente: Cuenta no disponible. General de A: 1600.00, solo sus tres cuentas. | La empresa se toma de la membresía y se aplica en SQL. |
| B13 | PASÓ | CONSULTA lee Banco y general; createTransaction devuelve FORBIDDEN sin escrituras. | Lectura de balances no concede permiso de captura. |
| B14 | PASÓ | El mismo token pierde acceso a ambas consultas al quitar transactions.read; vuelve a leer tras restaurar. | Los permisos se consultan en la BD y no se congelan en el JWT. |
| B15 | PASÓ | Egreso positivo de 50.00 guardado; cuenta y general cierran en -50.00; 1 cuenta en rojo. | Se permite sobregiro y se detecta con closingBalance < 0. |

Suite completa: **109 pruebas**, 0 fallos, 0 errores, 0 omitidas.

- [Salida de pytest](evidencias/pytest-mysql.txt)
- [Reporte JUnit](evidencias/pytest-mysql.xml)
- [Operaciones, variables, respuestas y estado por caso](evidencias/graphql-mysql.json)
- [Respuestas iniciales del laboratorio](evidencias/referencia-http.json)
- [Ambiente real de ejecución](evidencias/ambiente.json)

B01 comprueba también una única agregación para el general, orden por ID y las cuatro igualdades del enunciado. Las pruebas adicionales comprueban rechazo de precisión adicional y montos inválidos, totales mayores al límite de una transacción, historial de capturista inactivo y migración MySQL sin redondear.

La preparación de B07 y B08 está en tests/test_balances.py y opera solo sobre su base temporal. El fixture restaura el aislamiento creando otra base para el siguiente caso; B14 además restaura explícitamente su permiso.

Se ejecutaron Banco y el general en la interfaz GraphiQL local con variables y Authorization Bearer. No se adjuntan capturas gráficas: el panel no mostraba el resultado completo y la herramienta de captura de Windows detuvo el acceso al no poder verificar la URL. La evidencia entregada son las respuestas JSON y los registros automatizados, sin imágenes simuladas ni tokens vigentes.

Reproducción: seguir README.md de esta carpeta. Los IDs de esta ejecución se guardan en ids.json; el preparador los regenera para cada instalación.
