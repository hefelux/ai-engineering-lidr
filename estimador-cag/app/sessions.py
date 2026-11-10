"""Sesiones de conversacion del estimador.

Todo vive en un diccionario en la memoria del proceso. Si se reinicia el
servicio se pierden las sesiones. Por ahora se acepta asi: es una sola
instancia, las conversaciones son cortas y no hay que guardar nada a largo plazo.
Si mas adelante hay varias instancias o hay que retomar conversaciones, se pasa a
Redis o a una base de datos.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.config import settings


class ProjectMetadata(BaseModel):
    """Lo que sabemos del proyecto. Va aparte del historial y se manda en el system."""

    project_name: str | None = None
    assumed_team_size: int | None = None
    mentioned_technologies: list[str] = []
    agreed_scope: str | None = None

    def is_empty(self):
        return (
            self.project_name is None
            and self.assumed_team_size is None
            and len(self.mentioned_technologies) == 0
            and self.agreed_scope is None
        )


class ConversationHistory:
    """Mensajes de la conversacion con ventana deslizante.

    Un turno es un par user + assistant. Si hay mas de max_turns se borran los
    mas viejos. El system prompt no se guarda aca: se arma de nuevo en cada
    llamada con el project_metadata actual y siempre va primero.
    """

    def __init__(self, max_turns=None):
        if max_turns is None:
            max_turns = settings.max_turns
        self.max_turns = max_turns
        self.messages = []

    def add_user(self, text):
        self.messages.append({"role": "user", "content": text})
        # el turno nuevo cuenta, asi que se borran los pares viejos que sobran
        while self.count_turns() > self.max_turns:
            del self.messages[0:2]

    def add_assistant(self, text):
        self.messages.append({"role": "assistant", "content": text})

    # si falla el LLM se saca la pregunta que quedo sin respuesta
    def remove_last_user(self):
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages.pop()

    # cuenta los mensajes del usuario (cada uno abre un turno)
    def count_turns(self):
        total = 0
        for message in self.messages:
            if message["role"] == "user":
                total += 1
        return total

    def to_messages_list(self, system_prompt):
        """Lista lista para la API: el system primero y despues los turnos."""
        return [{"role": "system", "content": system_prompt}] + self.messages


class Session:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.history = ConversationHistory()
        self.metadata = ProjectMetadata()


# session_id -> Session
SESSIONS = {}


def create_session():
    session = Session()
    SESSIONS[session.session_id] = session
    return session


# devuelve None si la sesion no existe (o se perdio con un reinicio)
def get_session(session_id):
    return SESSIONS.get(session_id)
