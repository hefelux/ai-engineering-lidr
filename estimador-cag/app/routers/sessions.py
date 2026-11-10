from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import DetailLevel, OutputFormat, ProjectType, PromptVersion, SessionCreated, SessionEstimationResponse
from app.services.attachments import build_transcript
from app.services.session_service import run_turn
from app.sessions import create_session, get_session

router = APIRouter()


# Crea una sesion vacia, el cliente manda el session_id en cada estimacion
@router.post("/sessions", response_model=SessionCreated)
def new_session():
    session = create_session()
    return {"session_id": session.session_id}


# Un turno de la conversacion. Llega como multipart/form-data porque trae archivos,
# por eso cada campo se declara con Form() o File() y no con un modelo JSON
@router.post("/sessions/{session_id}/estimate", response_model=SessionEstimationResponse)
def estimate_in_session(
    session_id: str,
    transcript: str = Form(min_length=1, max_length=20000),
    project_type: ProjectType = Form(),
    detail_level: DetailLevel = Form(DetailLevel.medium),
    output_format: OutputFormat = Form(OutputFormat.phases_table),
    attachments: list[UploadFile] = File(default=[]),
    prompt_version: PromptVersion = PromptVersion.v1,
):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="La sesión no existe. Crea una nueva con POST /sessions")

    # (nombre, contenido) de cada adjunto
    files = []
    for attachment in attachments:
        files.append((attachment.filename, attachment.file.read()))

    full_transcript = build_transcript(transcript, files)

    form = {
        "project_type": project_type.value,
        "detail_level": detail_level.value,
        "output_format": output_format.value,
    }
    return run_turn(session, form, full_transcript, prompt_version.value)
