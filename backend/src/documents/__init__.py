"""Geração de documentos jurídicos — JusBot."""

from .notificacao import NotificacaoError, gerar_notificacao
from .schemas import DadosCaso, NotificacaoResult

__all__ = ["DadosCaso", "NotificacaoResult", "NotificacaoError", "gerar_notificacao"]
