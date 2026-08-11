from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion via variables de entorno (ver .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Base de datos. SQLite local en dev; en produccion usar una URL persistente
    # (ver README: Render free tier borra el disco, usar Turso/libsql).
    database_url: str = "sqlite:///./finanzas.db"

    # Enable Banking (Open Banking / PSD2).
    eb_application_id: str
    eb_private_key_pem: str

    # Auth de la app (multiusuario: cada usuario tiene su fila en `users`).
    app_jwt_secret: str
    # Solo se usa como semilla puntual en la migracion a multiusuario (para
    # preservar la contraseña del usuario original); la app ya no la lee.
    app_password_hash: str = ""

    # URLs publicas para CORS y para el redirect_url que se registra en Enable Banking.
    frontend_origin: str = "http://localhost:3000"
    backend_public_url: str = "http://localhost:8000"

    # Monitorizacion de errores (opcional). Vacio = Sentry desactivado.
    sentry_dsn: str = ""

    # Envio de emails (recuperar contraseña), via Resend. Vacio = la funcion
    # queda "activa" a nivel de API pero no llega a enviar nada (se loguea).
    resend_api_key: str = ""
    resend_from_email: str = "Finanzas <onboarding@resend.dev>"

    # Codigo de invitacion para registrarse (opcional). Vacio = registro abierto.
    registration_invite_code: str = ""

    @property
    def eb_redirect_url(self) -> str:
        return f"{self.backend_public_url.rstrip('/')}/api/banks/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
