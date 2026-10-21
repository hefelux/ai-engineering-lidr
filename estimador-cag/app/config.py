from pydantic_settings import BaseSettings, SettingsConfigDict

# Variables de entorno que usa la app (se leen del .env)
class Settings(BaseSettings):

    # Lee el archivo .env y si una variable esta vacia usa el valor por defecto
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # API keys de los proveedores
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Proveedor y modelo a usar
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Entorno y nivel de logs
    app_env: str = "development"
    log_level: str = "DEBUG"


# Instancia que se importa desde el resto del proyecto
settings = Settings()
