# Sanity check de los embeddings

Modelo: `text-embedding-3-small` (1536 dimensiones). Resultados de `scripts/compare.py`, el 2026-11-24. Dentro y fuera del contenedor dieron los mismos valores.

| Pareja | Texto 1 | Texto 2 | Se esperaba | Similitud coseno |
|---|---|---|---|---|
| A | OAuth 2.0 authentication backend with JWT tokens for fintech mobile app | Authorization service using JSON Web Tokens for a banking application | > 0.6 | **0.5957** |
| B | OAuth 2.0 authentication backend with JWT tokens for fintech mobile app | Database migration from MySQL to PostgreSQL with zero downtime | < 0.4 | **0.1920** |
| C | Backend services | API development | sin expectativa | **0.5407** |

## Comentario

- El modelo separa bien lo cercano de lo lejano: A queda 0.40 por encima de B, y B cumple con margen.
- A queda justo bajo el 0.6. La pareja dice lo mismo con otras palabras («JWT» y «JSON Web Tokens», «fintech» y «banking») y comparte pocos términos literales.
- Lo que más me llama la atención es C: dos frases de dos palabras casi sin contenido dan 0.54, muy cerca de A.
- Por eso un umbral fijo como 0.6 no sirve igual para textos cortos y largos. Habría que calibrarlo con fragmentos parecidos a los reales, como los de los presupuestos.
