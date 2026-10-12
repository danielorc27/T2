from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator, model_validator


class Perfil(str, Enum):
    GENERAL = "general"
    ESTUDIANTE = "estudiante"
    ADULTO_MAYOR = "adulto_mayor"


class Validacion(BaseModel):
    id: str
    estacion: str
    fecha_hora: datetime

    @field_validator("fecha_hora")
    @classmethod
    def _fecha_hora_debe_tener_zona_horaria(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None:
            raise ValueError("fecha_hora debe incluir zona horaria (offset explícito)")
        return valor


class SolicitudTarifa(BaseModel):
    tarjeta: str
    perfil: Perfil = Perfil.GENERAL
    validaciones: list[Validacion]

    @model_validator(mode="after")
    def _sin_ids_duplicados(self) -> "SolicitudTarifa":
        ids = [v.id for v in self.validaciones]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "las validaciones no pueden repetir el mismo id en una misma solicitud"
            )
        return self


class Cobro(BaseModel):
    validacion_id: str
    fecha_hora: datetime
    tipo: str
    valor: int


class RespuestaTarifa(BaseModel):
    tarjeta: str
    perfil: Perfil
    cobros: list[Cobro]
    total: int
