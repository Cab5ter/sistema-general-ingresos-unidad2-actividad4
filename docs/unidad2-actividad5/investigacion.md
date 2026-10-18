# Investigación aplicada: configuración completa de permisos

## 1. Identidad, decisiones y configuración

Autenticar comprueba quién intenta entrar. En nuestro sistema, login verifica una contraseña contra su hash Argon2id y devuelve un token. Autorizar responde si una petición concreta puede realizar una acción. Configurar permisos establece las acciones asociadas a un puesto. Aunque las tres ideas se relacionan, cambiar una lista no verifica la identidad de quien solicita el cambio. Por ejemplo, añadir accounts.write a CAPTURISTA permite crear cuentas a las personas con ese rol; no demuestra que quien abrió GraphiQL sea Ana.

actorCompanyUserId identifica una membresía de laboratorio. Como el cliente puede escribir otro número, su presencia no constituye una prueba de identidad. Reutilizamos exigir_permiso para consultar el estado persistido de usuario, empresa, membresía, rol, relación y permiso. La comprobación exige roles.read al consultar y roles.write al modificar. No basta ocultar un botón: una llamada directa debe pasar la misma decisión. La integración de identidad autenticada queda fuera del alcance de esta actividad. Se conserva el login existente y no se publican credenciales en evidencias. Aplicación de la fuente: la guía oficial de autorización de GraphQL ubica estas decisiones en la lógica del servidor; aquí seguimos el servicio existente.

## 2. Pruebas repetibles con variables, alias y fragmentos

Las variables separan el documento de los datos. La misma operación se puede ejecutar en otra base cambiando el JSON, sin editar sus campos. Esto importa porque los IDs no son universales. El alias distingue dos resultados del mismo campo: cuentas y movimientos representan dos filtros diferentes de permissionCatalog. El fragmento reutiliza una selección consistente. Ninguno de estos recursos concede permisos ni elimina las validaciones del servidor. Aplicamos la guía de consultas de GraphQL en esta operación propia, incluida en operaciones.graphql:

```graphql
query ExplorarCatalogo($actor: ID!) {
  cuentas: permissionCatalog(actorCompanyUserId: $actor, resource: ACCOUNTS) {
    ...DatosPermiso
  }
  movimientos: permissionCatalog(actorCompanyUserId: $actor, resource: TRANSACTIONS) {
    ...DatosPermiso
  }
}
fragment DatosPermiso on Permission { id code name }
```

Los archivos actor.json, s0.json y s1.json conservan los datos reales del laboratorio. Seleccionar operationName permite ejecutar una operación de un documento con varias definiciones. Guardamos petición, variables y respuesta junto con SQL, porque HTTP 200 puede acompañar errors y no demuestra persistencia.

## 3. Qué comprueba GraphQL y qué comprueba Python

PermissionResource limita los recursos a cinco valores. PAYMENTS se rechaza antes de ejecutar el resolver. Strawberry transforma el enum de Python en ese contrato y un input agrupa roleId y permissionIds. El tipo [ID!]! exige una lista no nula y elementos no nulos, pero no una longitud mínima: [] cumple el contrato. Por ello [] representa una decisión explícita de retirar todas las concesiones de Capturista.

Un ID válido para GraphQL todavía puede no existir en MySQL. En Python comprobamos identificadores positivos, existencia, estado activo, rol permitido y duplicados. Convertimos cada ID al formato numérico del proyecto antes de detectar repeticiones: el número 3 y el texto "3" designan el mismo registro. Ambas operaciones rechazan ADMINISTRADOR. Aplicamos las páginas de enums e inputs de Strawberry declarando @strawberry.enum y @strawberry.input, mientras el servicio compartido conserva las reglas de negocio. También filtramos Permission.is_active desde una consulta SQL; no construimos un catálogo fijo que pudiera ignorar cambios persistidos.

## 4. Atomicidad, repetición y comprobación

Atomicidad significa que todas las modificaciones de una lista se confirman o ninguna persiste. Idempotencia significa que repetir la misma lista deja el mismo resultado final. Son propiedades distintas: una operación puede confirmar un lote completo y aun así insertar duplicados al repetirse. En nuestra actualización calculamos diferencias, reactivamos filas históricas y usamos el índice único del par. La segunda aplicación devuelve changed: false y no activa ni desactiva relaciones.

Aplicamos la guía de transacciones de SQLAlchemy usando la sesión existente, un flush y un único commit al salir correctamente del contexto. La prueba E07 provoca una excepción después de enviar escrituras mediante flush. Una sesión nueva comprueba que el rollback conservó los mismos IDs, pares y estados. Varias mutaciones en una petición no crean una transacción común: cada resolver del proyecto confirma su propia sesión. Tampoco la previsualización reserva el estado: al aplicar volvemos a consultar y validar. Finalmente, el arranque cuenta relaciones históricas, incluidas las inactivas, para no confundir una lista deliberadamente vacía con un rol sin inicializar.

## Fuentes oficiales consultadas

Fecha de consulta de todas las fuentes: 17 de octubre de 2026.

- GraphQL, Authorization: https://graphql.org/learn/authorization/
- GraphQL, Queries: https://graphql.org/learn/queries/
- Strawberry, Enums: https://strawberry.rocks/docs/types/enums
- Strawberry, Input types: https://strawberry.rocks/docs/types/input-types
- SQLAlchemy 2.0, Transactions and Connection Management: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
