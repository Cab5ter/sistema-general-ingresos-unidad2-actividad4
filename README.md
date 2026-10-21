# Sistema General de Ingresos · Unidad II · Actividad 6

Control de acceso con JWT firmado por el servidor. Continúa las actividades 1 a 5 y conserva la matriz de cuatro roles, los diez permisos y la configuración atómica de listas de permisos.

`login` verifica el hash y devuelve un token HS256 de 30 minutos con `companyUserId`, `companyId` y `exp`. Las operaciones protegidas reciben `Authorization: Bearer ...`; el esquema ya no acepta `actorCompanyUserId`. El rol y los permisos se consultan en la base en cada petición, por lo que el token de Pedro funciona con su rol nuevo sin repetir el login.

- [Inicio, autenticación y los nueve casos de la actividad 6](docs/unidad2-actividad6/README.md)
- [Operaciones de la actividad 6](docs/unidad2-actividad6/operaciones.graphql)
- [Comprobaciones SQL de los rechazos](docs/unidad2-actividad6/comprobaciones.sql)
- [Ejemplo de ambiente sin secretos](.env.docker.example)

Las evidencias nuevas se generan en la ruta indicada por `EVIDENCE_DIR` (por defecto, `entrega/evidencias-actividad6/`, ignorada por Git). Los tokens y las contraseñas se ocultan en el registro y las capturas. Las carpetas de evidencias anteriores se conservan como historial de las actividades previas.

Documentación anterior:

- [Instrucciones y operaciones de la actividad 5](docs/unidad2-actividad5/README.md)
- [Investigación con fuentes oficiales](docs/unidad2-actividad5/investigacion.md)
- [Casos E01-E10 y evidencias](docs/unidad2-actividad5/evidencias.md)
- [Operaciones GraphQL](docs/unidad2-actividad5/operaciones.graphql)
- [Contrato completo](schema.graphql)
- [Documentación anterior conservada](docs/README-unidad2-actividad4.md)

Repositorio: https://github.com/Cab5ter/sistema-general-ingresos-unidad2-actividad4

**Integrantes del equipo:** Enrique Zavala y Marcelo Medina.
