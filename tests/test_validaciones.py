"""Tests de las validaciones del contrato HTTP (Fase 3).

Construyen SolicitudTarifa directamente, sin TestClient, para no quedar
bloqueados por el conflicto Starlette/httpx2 ya documentado aparte. Los
datos se pasan como dict (igual que llegaria el JSON de un request real)
para ejercitar el parseo real de Pydantic, no solo tipos de Python ya
construidos.
"""

import pytest
from pydantic import ValidationError

from app.modelos import Perfil, SolicitudTarifa


def _validacion(id_="v1", fecha_hora="2025-03-10T07:00:00-05:00", estacion="E01"):
    return {"id": id_, "estacion": estacion, "fecha_hora": fecha_hora}


def test_1_perfil_invalido_produce_validation_error():
    with pytest.raises(ValidationError):
        SolicitudTarifa(tarjeta="T1", perfil="vip", validaciones=[])


def test_2_fecha_hora_sin_zona_horaria_produce_validation_error():
    with pytest.raises(ValidationError):
        SolicitudTarifa(
            tarjeta="T1",
            validaciones=[_validacion(fecha_hora="2025-03-10T07:00:00")],
        )


def test_3_fecha_hora_con_zona_horaria_se_acepta():
    # Incluye el sufijo Z (UTC) ademas del offset explicito -05:00.
    solicitud = SolicitudTarifa(
        tarjeta="T1",
        validaciones=[
            _validacion("v1", "2025-03-10T07:00:00-05:00"),
            _validacion("v2", "2025-03-10T07:00:00Z"),
        ],
    )
    assert solicitud.validaciones[0].fecha_hora.tzinfo is not None
    assert solicitud.validaciones[1].fecha_hora.tzinfo is not None


def test_4_ids_duplicados_producen_validation_error():
    with pytest.raises(ValidationError):
        SolicitudTarifa(
            tarjeta="T1",
            validaciones=[
                _validacion("v1", "2025-03-10T07:00:00-05:00"),
                _validacion("v1", "2025-03-10T08:00:00-05:00"),
            ],
        )


def test_5_ids_distintos_se_aceptan():
    solicitud = SolicitudTarifa(
        tarjeta="T1",
        validaciones=[
            _validacion("v1", "2025-03-10T07:00:00-05:00"),
            _validacion("v2", "2025-03-10T08:00:00-05:00"),
        ],
    )
    assert [v.id for v in solicitud.validaciones] == ["v1", "v2"]


def test_6_perfil_omitido_toma_general_por_defecto():
    solicitud = SolicitudTarifa(tarjeta="T1", validaciones=[])
    assert solicitud.perfil == Perfil.GENERAL


def test_7_lista_vacia_de_validaciones_se_acepta():
    solicitud = SolicitudTarifa(tarjeta="T1", validaciones=[])
    assert solicitud.validaciones == []
