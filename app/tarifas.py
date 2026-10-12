"""Cálculo de lo que se le cobra a una tarjeta por sus validaciones."""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.config import (
    DESCUENTOS,
    MULTIPLO_REDONDEO,
    TARIFA_BASE,
    VALOR_TRANSBORDO,
    VENTANA_TRANSBORDO_MIN,
)
from app.modelos import Cobro, Perfil, RespuestaTarifa, SolicitudTarifa, Validacion


def _con_descuento(valor: Decimal, perfil: Perfil) -> Decimal:
    descuento = Decimal(DESCUENTOS[perfil.value]) / 100
    return valor * (1 - descuento)


def _redondeado_al_multiplo_mas_cercano(valor: Decimal) -> int:
    # round() nativo redondea los empates al par más cercano (banker's
    # rounding): 6.5 -> 6. El contrato exige empates hacia arriba, por
    # eso se usa Decimal + ROUND_HALF_UP en vez de round().
    multiplos = (valor / MULTIPLO_REDONDEO).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(multiplos) * MULTIPLO_REDONDEO


def aplicar_descuento(valor: int, perfil: Perfil) -> int:
    """Aplica el descuento del perfil y redondea al múltiplo de 50 más cercano."""
    return _redondeado_al_multiplo_mas_cercano(_con_descuento(Decimal(valor), perfil))


def _clasificar(
    fecha_hora: datetime,
    ancla_viaje: datetime | None,
    transbordos_en_viaje: int,
) -> tuple[str, int, datetime, int]:
    """Decide si `fecha_hora` abre un viaje nuevo o es un transbordo del
    viaje en curso.

    La ventana de 90 minutos se mide siempre desde `ancla_viaje` (la
    primera validación del viaje), nunca desde la última validación.
    Al tercer evento dentro de la ventana ya no queda cupo de
    transbordo, así que se trata como el inicio de un viaje nuevo.

    Devuelve (tipo, valor_base, nueva_ancla, nuevo_contador).
    """
    dentro_de_ventana = ancla_viaje is not None and (
        fecha_hora - ancla_viaje <= timedelta(minutes=VENTANA_TRANSBORDO_MIN)
    )
    if dentro_de_ventana and transbordos_en_viaje < 2:
        contador = transbordos_en_viaje + 1
        if contador == 1:
            return "transbordo", VALOR_TRANSBORDO, ancla_viaje, contador
        return "transbordo_gratis", 0, ancla_viaje, contador
    return "tarifa", TARIFA_BASE, fecha_hora, 0


def calcular_tarifa(solicitud: SolicitudTarifa) -> RespuestaTarifa:
    # Las validaciones pueden llegar desordenadas (buses que sincronizan
    # cuando hay señal); la máquina de estados necesita el orden
    # cronológico real. Empates exactos de fecha_hora se desempatan por
    # id (ver tests/test_transbordos.py).
    validaciones_ordenadas: list[Validacion] = sorted(
        solicitud.validaciones, key=lambda v: (v.fecha_hora, v.id)
    )

    cobros = []
    ancla_viaje: datetime | None = None
    transbordos_en_viaje = 0

    for validacion in validaciones_ordenadas:
        tipo, valor_base, ancla_viaje, transbordos_en_viaje = _clasificar(
            validacion.fecha_hora, ancla_viaje, transbordos_en_viaje
        )
        cobros.append(
            Cobro(
                validacion_id=validacion.id,
                fecha_hora=validacion.fecha_hora,
                tipo=tipo,
                valor=aplicar_descuento(valor_base, solicitud.perfil),
            )
        )

    total = sum(c.valor for c in cobros)
    return RespuestaTarifa(
        tarjeta=solicitud.tarjeta,
        perfil=solicitud.perfil,
        cobros=cobros,
        total=total,
    )
