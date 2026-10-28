# Sistema General de Ingresos · Unidad II · Actividad 7

Balances por cuenta y balance general por período, profit y números rojos. Continúa el proyecto de la actividad 6 y conserva su JWT, cuatro roles, diez permisos y configuración atómica de permisos.

**Integrantes:** Enrique Zavala, Marcelo Medina y Dylan Vazquez Soriano.

- [Actividad 7: instalación, migración, datos, pruebas y entrega](docs/unidad2-actividad7/README.md)
- [Consultas GraphQL y login](docs/unidad2-actividad7/operaciones.graphql)
- [Variables para Banco, Caja, Ahorro y general](docs/unidad2-actividad7/variables)
- [Evidencias B01-B15](docs/unidad2-actividad7/evidencias.md)
- [Explicación con los números de Banco y Caja](docs/unidad2-actividad7/explicacion.md)

MySQL usa `Numeric(12,2)` y agregaciones SQL; Python calcula con `Decimal`. El nuevo `accountBalance` requiere fechas y devuelve un objeto. Antes de iniciar sobre una base de actividades anteriores, ejecuta la migración validada descrita en la guía: no redondea importes históricos.

## Autenticación conservada de la actividad 6

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
