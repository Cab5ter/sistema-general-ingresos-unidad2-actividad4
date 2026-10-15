SELECT r.code AS rol, p.code AS permiso, rp.is_active FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code;
