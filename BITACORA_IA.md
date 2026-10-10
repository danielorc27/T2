# Bitácora de uso de IA

**Herramienta:** Claude Code (Anthropic), modelo Claude Sonnet 5, trabajando directamente sobre el repositorio (edición de archivos, ejecución de `pytest`/`pip`, lectura del PDF de instrucciones).

## Los tres prompts más relevantes (transcritos, abreviados por espacio)

**1. Implementación de transbordos (Fase 2):**
> "Vamos a implementar la lógica de transbordos de la prueba técnica `tarifas-t2`. [...] Implementa una máquina de estados sencilla y legible para controlar el inicio del viaje y la cantidad de transbordos. Mantén separadas, en lo posible, la clasificación de la validación (tarifa o transbordo), el cálculo del descuento y el redondeo."

**2. Refuerzo de tests contra "pases accidentales"** (ítems 1 y 8 de una lista de 8 objetivos del mismo mensaje):
> "[...] Objetivos: 1. Revisa los 11 tests existentes y confirma que cada uno comprueba el comportamiento que describe, no solamente un resultado que el código actual produce por casualidad. [...] 8. No elimines escenarios válidos únicamente porque fallen con la implementación actual."

**3. Reproducir BUG-17 antes de corregirlo:**
> "Antes de corregir la implementación, agrega una prueba de regresión [...] Ejecuta la prueba y confirma que reproduce el fallo antes de implementar la corrección. Si no lo reproduce, revisa la prueba y el flujo real; no inventes una causa raíz."

## BUG-17: detección y corrección
Se inspeccionó `app/historial.py`: `calculos` era un atributo de **clase**, compartido por todas las tarjetas. Se escribió primero `tests/test_historial.py`, que falló exactamente donde se esperaba (cálculo de la tarjeta B visible en el historial de A), confirmando la causa antes de tocar código. Se aplicó el cambio mínimo (mover la lista a `__init__`) y se reconfirmó con esa prueba y con la suite completa.

## Dependencias y ejecución de pruebas
`pytest` fallaba en la colección de `tests/test_api.py` por un conflicto Starlette/`httpx2` bajo `filterwarnings=["error"]`. Se investigó por inspección del código instalado y bisección de versiones (sin instalar nada a ciegas) hasta encontrar un rango compatible de Starlette y AnyIO. Se fijó `starlette>=0.46.0,<1.2.0` y `anyio>=3.6.2,<4.15`, verificando con `pip check` y con `pytest tests/ -v` real tras cada cambio.

## Casos borde verificados
Transbordo en el límite exacto de 90 minutos, tercera validación en ventana (viaje nuevo), validaciones desordenadas, empate de fecha/hora (desempate por ID), fecha sin zona horaria, ID duplicado, perfil inválido. La lista vacía se probó primero manualmente por HTTP; una auditoría posterior detectó que ningún test automatizado la cubría tras agregar transbordos, y se cerró ese hueco con una prueba dedicada.

## Comprobaciones del usuario y limitaciones pendientes
El usuario corrió el servidor (`uvicorn --reload`) y probó casos clave por Swagger antes de autorizar cambios de código. **Docker se verificó de extremo a extremo en GitHub Codespaces**: `docker compose up --build` construyó la imagen, y se confirmó por HTTP `GET /salud` (200), `POST /tarifas/calcular` con transbordos (200, total $3.700) y el aislamiento de historial entre las tarjetas T-003/T-004 (200, sin mezcla).

## Corrección sobre una propuesta anterior
Los primeros tests de orden cronológico usaban IDs cuyo orden alfabético coincidía por accidente con el cronológico esperado — un ordenamiento incorrecto por ID los habría pasado igual. Se detectó en revisión, se invirtieron los IDs, y se confirmó con un script de simulación que un ordenamiento por ID sí habría fallado con los nuevos datos. También se reemplazó `round()` nativo (redondeo bancario) por `Decimal`+`ROUND_HALF_UP`, verificando numéricamente los dos casos de empate exacto que el PDF exige redondear hacia arriba.

## Qué aportó la persona, no la IA
Exigir que cada test fallara por una razón real y no por casualidad; frenar cambios de dependencias no verificables (rechazar instalar `httpx2` a ciegas); decidir el orden de las fases (entender antes de codificar); y marcar explícitamente qué quedó sin verificar (Docker) en vez de aceptar una afirmación optimista.
