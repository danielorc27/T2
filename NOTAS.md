# NOTAS TÉCNICAS — TARIFAS INTEGRADAS

## 1. Solución implementada

Se implementó `POST /tarifas/calcular` para calcular tarifas integradas según las validaciones recibidas. La tarifa base es de $3.200; el primer transbordo cuesta $500 y el segundo es gratuito. La ventana de transbordo es de 90 minutos, inclusive, contados desde la primera validación del viaje. Después de dos transbordos, la siguiente validación inicia un nuevo viaje con tarifa base.

## 2. Decisiones técnicas

- **Descuentos:** general (0 %), estudiante (35 %) y adulto mayor (55 %).
- **Redondeo:** se utiliza `Decimal` con `ROUND_HALF_UP` para redondear cada cobro al múltiplo de $50 más cercano, con empates hacia arriba.
- **Orden:** las validaciones se procesan cronológicamente; en caso de empate de fecha y hora, se utiliza el ID como segundo criterio.
- **Estado del viaje:** el ancla temporal y el contador de transbordos se mantienen durante cada cálculo, sin depender de consultas al historial anterior.
- **Validaciones:** perfil inválido, fecha sin zona horaria e IDs duplicados producen HTTP 422. La lista vacía devuelve HTTP 200, cobros vacíos y total cero.

## 3. Historial y pruebas

Se corrigió BUG-17 aislando la lista de cálculos en cada instancia de `HistorialTarjeta`, evitando que una tarjeta muestre operaciones de otra.

La suite automatizada se ejecutó con `pytest tests/ -v`: **25 pruebas aprobadas, sin errores ni warnings reportados**. Se conserva la configuración `filterwarnings = ["error"]`.

## 4. Ejecución

Con las dependencias instaladas, ejecutar:

```bash
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `http://localhost:8000/docs`.

El proyecto incluye configuración Docker Compose para construir y ejecutar el servicio mediante `docker compose up --build`. **Se verificó en GitHub Codespaces**: la imagen se construyó, Swagger abrió en `/docs`, y se confirmó por HTTP `GET /salud` (200, `{"estado":"ok"}`), `POST /tarifas/calcular` con transbordos (200, tarifa $3.200 + transbordo $500 + transbordo gratuito $0 = total $3.700) y el aislamiento del historial entre las tarjetas T-003 y T-004 (200, sin mezcla de cálculos).

## 5. Observaciones

El desempate por ID es un criterio técnico definido para garantizar un orden determinista cuando varias validaciones tienen la misma fecha y hora.

## 6. Casos borde identificados y resolución

- **Validación exactamente en el minuto 90:** el transbordo todavía aplica (el límite de la ventana es inclusivo).
- **Tercera validación dentro de la ventana de transbordo:** no se cobra como transbordo; inicia un nuevo viaje con tarifa base.
- **Empates al redondear** (p. ej. $325, $225): se redondean hacia arriba al múltiplo de $50 más cercano, en vez del redondeo bancario de `round()`.
- **Validaciones recibidas desordenadas:** se procesan en orden cronológico; en empates exactos de fecha y hora se desempata por ID.
- **Lista vacía, fechas sin zona horaria e IDs duplicados:** cubiertos explícitamente (200 con cobros vacíos, 422 y 422 respectivamente).
- **Aislamiento del historial entre tarjetas (BUG-17):** corregido y cubierto con una prueba de regresión dedicada.

## 7. Qué dejaría para producción

- Desplegar y validar en el entorno de producción real: lo verificado hasta ahora es `docker compose up --build` en GitHub Codespaces, no en el entorno de producción definitivo.
- Evaluar pruebas adicionales de integración y de operación en el entorno real de despliegue.
- Revisar necesidades de observabilidad, registro de errores y configuración por ambiente — no implementadas todavía, solo identificadas como pendientes.
