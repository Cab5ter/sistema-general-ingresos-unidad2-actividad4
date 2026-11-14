# Guion de la demostración · Parcial III

Duración aproximada: 5 minutos. Equipo: Enrique Zavala, Marcelo Medina, Leonard Balmes, Armando Cen y Dylan Vazquez Soriano.

## Antes de entrar al salón

- [ ] MySQL arriba y API corriendo en `127.0.0.1:8007`.
- [ ] Datos de laboratorio restaurados: `python -m app.demo_activity7 --restore`.
- [ ] Dashboard sirviéndose en `127.0.0.1:5500`.
- [ ] Contraseña del administrador a la mano (`.activity7-credentials.json`).
- [ ] Una pestaña con GraphiQL abierta, sin sesión iniciada en el dashboard.
- [ ] El token dura 30 minutos: iniciar sesión **durante** la demo, no antes.

## Pasos

| # | Quién | Qué se muestra | Qué se dice |
|---|---|---|---|
| 1 | Integración | Pantalla de login. Entrar con `admin.actividad7@example.com`. | "El cliente llama a la mutación `login` y guarda el token solo en `sessionStorage`." |
| 2 | Frontend | Dashboard abierto con el período 26 al 30 de octubre. | "Encabezado, controles, indicadores, riesgo y detalle: son los cinco bloques del boceto." |
| 3 | Frontend | Indicadores: 1,000.00 / 3,500.00 / 2,900.00 / 600.00 / 1,600.00. | "Cada tarjeta es un campo de `generalBalance`: `openingBalance`, `totalIncome`, `totalExpense`, `profit` y `closingBalance`. Nada se calcula en el navegador." |
| 4 | Backend | Misma consulta en GraphiQL con el Bearer token. | "Mismos datos y fechas, mismas cifras: el dashboard no tiene otro cálculo." |
| 5 | Diseño | Caja con -200.00 en rojo; "General en rojo: No"; "Cuentas en rojo: 1". | "Una cuenta puede estar en rojo y el general no. Con un saldo total de 1,600.00, Caja sigue en déficit." |
| 6 | Frontend | Cambiar "Hasta" al 28 de octubre. | "Los números y la etiqueta del período cambian juntos: saldo final 2,300.00 y cero cuentas en rojo." |
| 7 | Frontend | Cambiar a 29 al 30 de octubre. | "Aquí el profit es -700.00 pero el saldo final sigue en 1,600.00: profit negativo no es saldo en rojo." |
| 8 | Backend | Poner "Desde" posterior a "Hasta". | "Sin llamar al API, el dashboard avisa que las fechas son inválidas." |
| 9 | Integración | Cerrar sesión. | "Se borra el token y se vuelve al login." |

Si sobra tiempo: alterar el token en DevTools y pulsar Actualizar para mostrar el regreso al login por token inválido.

## Si algo falla

- **"Sin conexión con el API":** el API no está corriendo o CORS no permite el origen. Reiniciar uvicorn y revisar que el dashboard esté en `127.0.0.1:5500`.
- **Los números no coinciden:** correr `python -m app.demo_activity7 --restore` y volver a consultar 26–30 de octubre.
- **El login falla:** revisar la contraseña en `.activity7-credentials.json`.
- **La sesión expiró (30 minutos):** iniciar sesión otra vez.

## Preguntas que pueden hacernos

- **¿De dónde sale cada número?** Del campo de `generalBalance` con el mismo nombre; al pasar el cursor sobre una tarjeta aparece el campo.
- **¿Por qué el dashboard no pide `companyId`?** La empresa va dentro del token; el servidor la lee de ahí.
- **¿Qué pasa sin permiso?** El API responde `FORBIDDEN` y el dashboard muestra "Acceso denegado" en lugar de números en cero.
- **¿Por qué no se recalcula en el cliente?** Para que el backend sea la única fuente de verdad.