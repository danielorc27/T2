"""Prueba de regresion de BUG-17: el historial no debe mezclar tarjetas.

Prueba el modulo app.historial directamente (sin TestClient), igual que
test_tarifas.py/test_transbordos.py, para aislar el comportamiento del
historial de la capa HTTP.
"""

from datetime import datetime, timedelta, timezone

from app.historial import obtener_historial
from app.modelos import Cobro, Perfil, RespuestaTarifa

FECHA = datetime(2025, 3, 10, 7, 0, 0, tzinfo=timezone(timedelta(hours=-5)))


def _respuesta(tarjeta: str, valor: int) -> RespuestaTarifa:
    return RespuestaTarifa(
        tarjeta=tarjeta,
        perfil=Perfil.GENERAL,
        cobros=[Cobro(validacion_id="v1", fecha_hora=FECHA, tipo="tarifa", valor=valor)],
        total=valor,
    )


def test_historial_no_mezcla_calculos_entre_tarjetas():
    historial_a = obtener_historial("TARJETA-A-REGRESION-BUG17")
    historial_b = obtener_historial("TARJETA-B-REGRESION-BUG17")

    historial_a.registrar(_respuesta("TARJETA-A-REGRESION-BUG17", 3200))
    historial_b.registrar(_respuesta("TARJETA-B-REGRESION-BUG17", 500))

    calculos_a = historial_a.listar()
    calculos_b = historial_b.listar()

    # los registros propios de cada tarjeta SI deben aparecer
    assert any(c.tarjeta == "TARJETA-A-REGRESION-BUG17" for c in calculos_a)
    assert any(c.tarjeta == "TARJETA-B-REGRESION-BUG17" for c in calculos_b)

    # los registros de la OTRA tarjeta NO deben aparecer
    assert all(c.tarjeta != "TARJETA-B-REGRESION-BUG17" for c in calculos_a)
    assert all(c.tarjeta != "TARJETA-A-REGRESION-BUG17" for c in calculos_b)
