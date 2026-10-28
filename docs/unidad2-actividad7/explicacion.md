# Saldo inicial, profit, saldo final y números rojos

Período: **26 al 30 de octubre de 2026**, días completos UTC. Moneda: **MXN**.

| Cuenta | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---|---:|---:|---:|---:|---:|---|
| Banco | 1,000.00 | 3,000.00 | 2,200.00 | 800.00 | 1,800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| General | 1,000.00 | 3,500.00 | 2,900.00 | 600.00 | 1,600.00 | No |

El **saldo inicial** es el dinero acumulado antes del primer día consultado. Banco tiene 1,000.00 por el ingreso de apertura del 25. Ese ingreso no se suma a los ingresos del período 26-30.

El **profit** es ingresos menos egresos dentro del período. Banco recibe 3,000.00 y gasta 1,200.00 + 1,000.00: su profit es 800.00. El **saldo final** añade el saldo inicial: 1,000.00 + 800.00 = 1,800.00. Por eso profit y saldo final no son sinónimos.

Caja no tiene saldo inicial. Recibe 500.00 y gasta 700.00, por lo que su profit y su saldo final son -200.00. Está **en números rojos** porque su saldo final es menor que cero. Ahorro está en cero y no está en rojo.

El general cierra en 1,600.00 y `isInRed` es `false`, pero `accountsInRed` es `1` debido a Caja. Un total positivo no elimina el déficit de una cuenta.

Al consultar **solo Banco el 28**, el saldo inicial cambia a 2,800.00: 1,000.00 + 3,000.00 - 1,200.00. Ese día no hay ingresos y hay un egreso de 1,000.00. El profit es -1,000.00, el saldo final es 1,800.00 y no está en rojo. Un profit negativo no implica un saldo final negativo.

Aquí profit es un importe operativo, no un porcentaje ni una utilidad contable completa. El balance general resume cuentas del sistema; no es un estado de activos, pasivos y capital.
