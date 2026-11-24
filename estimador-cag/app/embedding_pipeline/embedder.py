import time

import structlog
from openai import OpenAI, RateLimitError

from app.config import settings
from app.embedding_pipeline.schemas import Chunk, EmbeddedChunk

logger = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"

# Precio de text-embedding-3-small: US$ 0,02 por millon de tokens de entrada
# Revisado en noviembre de 2026, cambia con el tiempo
PRICE_PER_MILLION_TOKENS_USD = 0.02

# Cuantos fragmentos van en cada llamada a la API
BATCH_SIZE = 100

# Esperas (en segundos) antes de cada reintento cuando la API responde 429
RETRY_WAITS = [1, 2, 4]


def estimate_cost(tokens):
    return tokens * PRICE_PER_MILLION_TOKENS_USD / 1_000_000


class OpenAIEmbedder:

    def __init__(self, client=None):
        # el cliente se puede pasar desde afuera (por ejemplo uno falso en las pruebas)
        self.client = client or OpenAI(api_key=settings.openai_api_key)
        self.model = EMBEDDING_MODEL

    def embed_one(self, text: str) -> list[float]:
        vectors, _ = self._call_api([text])
        return vectors[0]

    def embed_many(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        embedded = []
        # recorre los fragmentos de a BATCH_SIZE
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            texts = [chunk.text for chunk in batch]

            started = time.perf_counter()
            vectors, tokens = self._call_api(texts)
            latency_ms = round((time.perf_counter() - started) * 1000)

            logger.info("embedding_batch", chunks=len(batch), tokens=tokens, latency_ms=latency_ms)

            for chunk, vector in zip(batch, vectors):
                embedded.append(EmbeddedChunk(**chunk.model_dump(), embedding=vector))
        return embedded

    # Una llamada a la API. Si responde 429 (RateLimitError) espera y reintenta
    # hasta 3 veces. Cualquier otro error sigue hacia arriba
    def _call_api(self, texts):
        attempt = 0
        while True:
            try:
                response = self.client.embeddings.create(model=self.model, input=texts)
                break
            except RateLimitError:
                if attempt == len(RETRY_WAITS):
                    raise
                wait = RETRY_WAITS[attempt]
                logger.warning("embedding_rate_limited", attempt=attempt + 1, wait_s=wait)
                time.sleep(wait)
                attempt += 1

        # la API devuelve los vectores en el mismo orden que los textos
        vectors = [item.embedding for item in response.data]
        return vectors, response.usage.total_tokens
