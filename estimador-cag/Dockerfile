FROM python:3.11-slim

# uv para instalar las dependencias igual que en local
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

WORKDIR /app

# primero las dependencias, asi no se reinstalan si solo cambia el codigo
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
