"""Tests de la maquina de estados de transbordo (Encargo 1).

Llaman directamente a `calcular_tarifa` porque la logica de viaje y
transbordo vive en app/tarifas.py, no en la capa HTTP (eso ya lo cubre
tests/test_api.py). Todas usan perfil "general" (0% descuento) para
aislar el estado del viaje del problema de redondeo, que es un bug
aparte (ver NOTAS.md / hallazgos de redondeo).

Cada test encadena aserciones sobre TODOS los cobros relevantes, no
solo el ultimo: el objetivo es que un test solo pueda pasar si la
secuencia completa de estados (tarifa -> transbordo -> transbordo
gratis -> viaje nuevo, etc.) es correcta, y no "por accidente" porque
la implementacion actual cobra tarifa a todo sin importar el estado.
"""

from datetime import datetime, timedelta, timezone

from app.config import TARIFA_BASE, VALOR_TRANSBORDO, VENTANA_TRANSBORDO_MIN
from app.modelos import Perfil, RespuestaTarifa, SolicitudTarifa, Validacion
from app.tarifas import calcular_tarifa

BASE = datetime(2025, 3, 10, 7, 0, 0, tzinfo=timezone(timedelta(hours=-5)))


def _en(minutos: float) -> datetime:
    return BASE + timedelta(minutes=minutos)


def _validacion(id_: str, minutos: float, estacion: str = "E01") -> Validacion:
    return Validacion(id=id_, estacion=estacion, fecha_hora=_en(minutos))


def _calcular(validaciones: list[Validacion], perfil: Perfil = Perfil.GENERAL) -> RespuestaTarifa:
    solicitud = SolicitudTarifa(tarjeta="T-TRANSBORDO", perfil=perfil, validaciones=validaciones)
    return calcular_tarifa(solicitud)


def test_1_primera_validacion_paga_tarifa_base():
    respuesta = _calcular([_validacion("v1", 0)])
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[0].valor == TARIFA_BASE


def test_2_primer_transbordo_cobra_valor_transbordo():
    respuesta = _calcular([_validacion("v1", 0), _validacion("v2", 30)])
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO


def test_3_segundo_transbordo_es_gratuito():
    respuesta = _calcular(
        [_validacion("v1", 0), _validacion("v2", 30), _validacion("v3", 60)]
    )
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO
    assert respuesta.cobros[2].tipo == "transbordo_gratis"
    assert respuesta.cobros[2].valor == 0


def test_4_tercera_validacion_dentro_de_ventana_inicia_viaje_nuevo():
    # La secuencia pasa explicitamente por el primer transbordo (v2) y el
    # segundo transbordo gratuito (v3) antes de la validacion que ya no
    # tiene cupo (v4): asi el test solo pasa si los 4 estados encadenan
    # bien, no solo si la ultima validacion cae en "tarifa".
    respuesta = _calcular(
        [
            _validacion("v1", 0),
            _validacion("v2", 10),
            _validacion("v3", 20),
            _validacion("v4", 30),
        ]
    )
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[0].valor == TARIFA_BASE
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO
    assert respuesta.cobros[2].tipo == "transbordo_gratis"
    assert respuesta.cobros[2].valor == 0
    assert respuesta.cobros[3].tipo == "tarifa"
    assert respuesta.cobros[3].valor == TARIFA_BASE


def test_5_transbordo_exactamente_a_los_90_minutos():
    # Limite incluido: a los 90 minutos exactos todavia debe ser transbordo.
    respuesta = _calcular(
        [_validacion("v1", 0), _validacion("v2", VENTANA_TRANSBORDO_MIN)]
    )
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO


def test_6_validacion_posterior_a_90_minutos_inicia_viaje_nuevo():
    # v2 primero demuestra que el transbordo SI puede ocurrir (minuto 60,
    # dentro de ventana); v3 llega a los 91 minutos del ancla original
    # (minuto 0), ya fuera de ventana, y debe iniciar viaje nuevo. Sin el
    # paso intermedio (v2), este test pasaria "gratis" con la
    # implementacion actual, que siempre cobra tarifa a todo.
    respuesta = _calcular(
        [
            _validacion("v1", 0),
            _validacion("v2", 60),
            _validacion("v3", VENTANA_TRANSBORDO_MIN + 1),
        ]
    )
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO
    assert respuesta.cobros[2].tipo == "tarifa"
    assert respuesta.cobros[2].valor == TARIFA_BASE


def test_7_ventana_se_mide_desde_primera_validacion_no_desde_ultimo_transbordo():
    # v3 esta a 30 min de v2 (seria transbordo con ventana deslizante) pero
    # a 100 min de v1, que es cuando empezo el viaje: debe pagar tarifa base.
    respuesta = _calcular(
        [_validacion("v1", 0), _validacion("v2", 70), _validacion("v3", 100)]
    )
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO
    assert respuesta.cobros[2].tipo == "tarifa"
    assert respuesta.cobros[2].valor == TARIFA_BASE


def test_8_validaciones_fuera_de_orden_responden_en_orden_cronologico():
    # "zeta" es la validacion mas temprana (minuto 0) y "alfa" la mas
    # tardia (minuto 30): alfabeticamente quedan al reves que
    # cronologicamente. Un ordenamiento incorrecto por `id` daria
    # ["alfa", "zeta"] -el inverso del esperado- en vez del orden
    # cronologico real, y este test lo detectaria.
    respuesta = _calcular([_validacion("alfa", 30), _validacion("zeta", 0)])
    assert [c.validacion_id for c in respuesta.cobros] == ["zeta", "alfa"]
    assert respuesta.cobros[0].tipo == "tarifa"
    assert respuesta.cobros[1].tipo == "transbordo"
    assert respuesta.cobros[1].valor == VALOR_TRANSBORDO


def test_9_misma_fecha_hora_desempata_por_id():
    respuesta = _calcular([_validacion("v2", 0), _validacion("v1", 0)])
    assert [c.validacion_id for c in respuesta.cobros] == ["v1", "v2"]


def test_10_conserva_ids_originales_al_reordenar():
    # "zulu-0" es la validacion mas temprana (minuto 0) y "alfa-30" la
    # mas tardia (minuto 30): alfabeticamente quedan al reves que
    # cronologicamente. Un ordenamiento incorrecto por `id` daria
    # ["alfa-30", "zulu-0"] -el inverso del esperado- en vez de
    # preservar el orden cronologico real.
    respuesta = _calcular(
        [_validacion("alfa-30", 30), _validacion("zulu-0", 0)]
    )
    assert [c.validacion_id for c in respuesta.cobros] == ["zulu-0", "alfa-30"]


def test_11_estado_de_viaje_no_persiste_entre_llamadas():
    # No es parte de la lista numerada del encargo, pero la instruccion
    # es explicita: "el estado del viaje comienza desde cero en cada
    # solicitud". La 1a solicitud deja un viaje abierto (v1 tarifa, v2
    # transbordo a los 10 min). La 2a solicitud, de la MISMA tarjeta,
    # trae una sola validacion solo 5 minutos despues de la ultima
    # validacion de la 1a solicitud: si el estado (ancla + contador)
    # sobreviviera entre llamadas -por un atributo de clase o una
    # variable de modulo compartida, el mismo tipo de error que BUG-17
    # en historial.py- esa validacion se cobraria como transbordo en vez
    # de tarifa base.
    primera = _calcular([_validacion("v1", 0), _validacion("v2", 10)])
    assert primera.cobros[0].tipo == "tarifa"
    assert primera.cobros[1].tipo == "transbordo"

    segunda = _calcular([_validacion("v3", 15)])
    assert segunda.cobros[0].tipo == "tarifa"
    assert segunda.cobros[0].valor == TARIFA_BASE
