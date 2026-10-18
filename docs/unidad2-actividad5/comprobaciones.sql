-- Solo lectura: conservar IDs, pares y estados para comparar antes/después.
SELECT rp.id AS relacion_id, r.code AS rol, p.code AS permiso,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp JOIN roles r ON r.id=rp.role_id
JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code;
SELECT role_id,permission_id,COUNT(*) AS repeticiones FROM role_permissions
GROUP BY role_id,permission_id HAVING COUNT(*)>1;
SELECT code,is_active FROM roles ORDER BY code;
SELECT code,is_active FROM permissions ORDER BY code;
-- E06: ejecutar cada preparación POR SEPARADO y restaurar tras sus dos peticiones.
-- Solo en la base de laboratorio; no se desactiva ADMINISTRADOR ni roles.read/write.
UPDATE roles SET is_active=0 WHERE code='CAPTURISTA';
-- Ejecutar preview y set, comprobar errors y que el SELECT de relaciones no cambió.
UPDATE roles SET is_active=1 WHERE code='CAPTURISTA';
UPDATE permissions SET is_active=0 WHERE code='accounts.write';
-- Ejecutar preview y set con S1; comprobar errors y SELECT sin cambios.
UPDATE permissions SET is_active=1 WHERE code='accounts.write';
