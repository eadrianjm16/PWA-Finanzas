"""Envio de emails transaccionales via Resend. Sin RESEND_API_KEY configurada,
la funcion no falla (para no romper el flujo de "olvide mi contraseña" con un
500) - simplemente no llega a enviar nada, y queda logueado para depurar."""

import logging

import httpx

from ..config import settings

logger = logging.getLogger("finanzas.email")

RESEND_URL = "https://api.resend.com/emails"


async def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY no configurada: no se envio el email de recuperación a %s", to_email)
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": "Recupera tu contraseña — Finanzas",
                "html": (
                    f"<p>Has pedido restablecer tu contraseña.</p>"
                    f'<p><a href="{reset_url}">Haz clic aquí para elegir una nueva contraseña</a> '
                    f"(caduca en 30 minutos).</p>"
                    f"<p>Si no fuiste tú, ignora este email.</p>"
                ),
            },
        )
        if response.status_code >= 400:
            logger.error("Resend devolvió %s al enviar a %s: %s", response.status_code, to_email, response.text)
