-- Ejecutar ANTES y DESPUÉS de cada intento desde otra conexión MySQL.
-- Sustituir la marca por el nombre/shortDescription que se envió en la petición.
SELECT COUNT(*) AS total_cuentas FROM accounts;
SELECT COUNT(*) AS filas_del_intento FROM accounts WHERE name = 'MARCA_DEL_INTENTO';
SELECT COUNT(*) AS total_movimientos FROM transactions;
SELECT COUNT(*) AS filas_del_intento FROM transactions WHERE short_description = 'MARCA_DEL_INTENTO';

-- La fila del intento rechazado permanece en cero y el total no crece.
-- Pedro conserva una sola asignación activa, CAPTURISTA después del caso 6.
SELECT cur.id, u.name, r.code, cur.is_active
FROM company_user_roles cur
JOIN roles r ON r.id = cur.role_id
JOIN company_users cu ON cu.id = cur.company_user_id
JOIN users u ON u.id = cu.user_id
WHERE u.email = 'pedro.actividad4@example.com'
ORDER BY cur.id;
