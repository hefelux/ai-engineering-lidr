# Pruebas de carga del CAG

Dónde se rompe el estimador de la sesión 5 cuando la conversación se alarga y los adjuntos crecen. Los datos están en `results.csv` (una fila por turno) y las tablas salen de `uv run python -m evals.stress.summary`.

## Cómo se corrió

| Parámetro | Valor |
|---|---|
| Modelo | `claude-haiku-5-5`, sin razonamiento (`thinking` desactivado) |
| Escenarios | growing, pivot y contradiction, de 20 turnos cada uno |
| Adjuntos | 0, 5, 20, 50 y 100 KB de texto, en el turno 1 |
| Repeticiones | 3 por combinación, 45 conversaciones |
| Filas en el CSV | 900 |
| Presupuesto de latencia | 8.000 ms por llamada de estimación |
| Presupuesto de costo | US$ 0,002 por llamada de estimación |
| Duración y costo total | 35 minutos con 3 conversaciones a la vez, US$ 1,77 |

```
uv run python -m evals.stress.run --http http://localhost:8000 \
  --scenarios growing,pivot,contradiction --attachment-sizes 0,5,20,50,100 \
  --repeats 3 --output evals/stress/results.csv
```

### Lo que este CAG no tiene

El enunciado supone resumen acumulativo, anclas, tier dinámico y caché semántica. Este estimador no los tiene porque el enunciado de la sesión 5 los puso en "Lo que no entra". La memoria es solo la ventana de 6 turnos (`MAX_TURNS=6`) más el `project_metadata` (nombre, equipo, tecnologías y alcance), que actualiza un extractor después de cada turno. Por eso `anchors_count` y `summary_chars` son siempre 0, `cache_hit_kind` es siempre "none" y `last_resolved_tier` es "none". Esas piezas no se agregaron antes de medir, porque el ejercicio pide medir sin cambiar el sistema. Lo único que se agregó es lo que pide el ejercicio para observar: el evento `turn_observed` y `GET /sessions/{id}`.

El tope de adjunto también es distinto: 20.000 caracteres por archivo (`MAX_CHARS_PER_FILE`), no 60.000.

### Decisiones

- **Las métricas van en `evals/stress/metrics.py`.** El estimador no tenía un `evals/metrics.py` previo, y estas métricas miran el evento `turn_observed` y el estado de la sesión, no la estimación.
- **`turn_observed` se lee de `GET /sessions/{id}`.** La sesión guarda el último evento y el runner lo pide después de cada turno. Es una llamada más, no depende de dónde se escriban los logs y trae el `project_metadata` que necesita `MemoryDriftMetric`. El evento también se escribe en el log con structlog.
- **`MemoryDriftMetric` busca en summary, anchors y metadata,** como pide el enunciado. Aparte, el CSV dice si cada dato sigue en la ventana (`watch_in_window`), para ver cuándo se pierde.

## 1. Tabla resumen

Una fila por escenario y tamaño de adjunto (3 repeticiones × 20 turnos = 60 filas). El costo incluye la llamada que actualiza el metadata.

| Escenario | KB | n | P50 ms | P95 ms | Costo total US$ | Caché exacta | Caché semántica | Recall medio | Dentro de latencia | Dentro de costo |
|---|---|---|---|---|---|---|---|---|---|---|
| growing | 0 | 60 | 4379 | 6781 | 0.1016 | 0% | 0% | 100% | 100% | 78% |
| growing | 5 | 60 | 4773 | 7192 | 0.1124 | 0% | 0% | 97% | 98% | 75% |
| growing | 20 | 60 | 5187 | 7937 | 0.1187 | 0% | 0% | 97% | 95% | 72% |
| growing | 50 | 60 | 6389 | 7093 | 0.1418 | 0% | 0% | 99% | 100% | 50% |
| growing | 100 | 60 | 5940 | 7045 | 0.1324 | 0% | 0% | 98% | 100% | 65% |
| pivot | 0 | 60 | 4835 | 7008 | 0.1005 | 0% | 0% | 100% | 100% | 82% |
| pivot | 5 | 60 | 4759 | 7054 | 0.1102 | 0% | 0% | 100% | 97% | 90% |
| pivot | 20 | 60 | 5007 | 6774 | 0.1201 | 0% | 0% | 100% | 100% | 88% |
| pivot | 50 | 60 | 4640 | 6556 | 0.1153 | 0% | 0% | 100% | 100% | 87% |
| pivot | 100 | 60 | 5188 | 6810 | 0.1267 | 0% | 0% | 100% | 100% | 83% |
| contradiction | 0 | 60 | 4990 | 7039 | 0.1122 | 0% | 0% | 60% | 100% | 75% |
| contradiction | 5 | 60 | 5641 | 6831 | 0.1240 | 0% | 0% | 60% | 98% | 65% |
| contradiction | 20 | 60 | 4769 | 6987 | 0.1212 | 0% | 0% | 60% | 100% | 88% |
| contradiction | 50 | 60 | 4531 | 6555 | 0.1157 | 0% | 0% | 60% | 100% | 97% |
| contradiction | 100 | 60 | 4528 | 6899 | 0.1192 | 0% | 0% | 60% | 100% | 87% |

En total: P50 de 4.976 ms y P95 de 7.037 ms. Solo 7 de 900 llamadas pasaron los 8.000 ms, todas desde el turno 13. Una conversación de 20 turnos cuesta en promedio US$ 0,039, y la llamada del extractor es el 19% de eso.

## 2. Las tres curvas

### Latencia contra tokens de entrada

| tokens_in | n | P50 ms | P95 ms |
|---|---|---|---|
| 0-1999 | 9 | 3424 | 3986 |
| 2000-3999 | 29 | 3279 | 5375 |
| 4000-5999 | 54 | 3322 | 4210 |
| 6000-7999 | 198 | 4418 | 5229 |
| 8000-9999 | 261 | 5471 | 6555 |
| 10000-11999 | 200 | 6517 | 7361 |
| 12000-13999 | 128 | 6465 | 7724 |
| 14000-15999 | 21 | 4665 | 5227 |

La latencia se duplica entre 4.000 y 10.000 tokens de entrada. El último tramo tiene pocas filas, todas de los turnos 5 y 6 con el adjunto grande todavía en la ventana. Ahí el modelo escribe 1.142 tokens de salida en promedio, contra 1.575 del tramo anterior, y la latencia baja. La latencia depende tanto de lo que el modelo escribe como de lo que lee.

### Costo acumulado contra turno

Promedio de las 15 conversaciones de cada escenario, en US$:

| Turno | growing | pivot | contradiction |
|---|---|---|---|
| 1 | 0.0018 | 0.0018 | 0.0018 |
| 3 | 0.0047 | 0.0048 | 0.0049 |
| 6 | 0.0103 | 0.0102 | 0.0105 |
| 10 | 0.0172 | 0.0169 | 0.0173 |
| 20 | 0.0405 | 0.0382 | 0.0395 |

Turno por turno, sin adjunto (promedio de los tres escenarios):

| Turno | tokens_in | tokens_out | Costo del turno US$ | Latencia ms | Mensajes en la ventana |
|---|---|---|---|---|---|
| 1 | 1708 | 626 | 0.00067 | 3335 | 2 |
| 3 | 3282 | 780 | 0.00095 | 3195 | 6 |
| 6 | 5982 | 950 | 0.00135 | 3651 | 12 |
| 7 | 6288 | 1031 | 0.00144 | 3871 | 12 |
| 10 | 7406 | 1321 | 0.00176 | 4683 | 12 |
| 13 | 8879 | 1631 | 0.00214 | 5899 | 12 |
| 20 | 11722 | 1822 | 0.00251 | 6439 | 12 |

Desde el turno 6 la ventana no crece más (12 mensajes), pero los tokens de entrada siguen subiendo. Las respuestas del modelo se alargan turno a turno (de 626 a 1.822 tokens), porque cada vez vuelve a estimar todo el proyecto, y esas respuestas vuelven en el historial.

### Memoria contra N

Porcentaje de los hechos que deberían seguir vivos y que están en summary, anchors o metadata:

| N (turno) | growing | pivot | contradiction |
|---|---|---|---|
| 1 | 100% | 100% | 100% |
| 3 | 100% | 100% | 100% |
| 6 | 100% | 100% | 50% |
| 10 | 100% | 100% | 50% |
| 20 | 90% | 100% | 50% |

Cuándo está cada dato, en las 15 conversaciones de cada escenario:

| Dato | En el metadata | En la ventana |
|---|---|---|
| Nombre Nimbus (growing) | turnos 1 a 20, 100% | 1 a 20 en casi todas, porque el modelo lo repite en sus respuestas |
| React Native (pivot) | 1 a 4, después 1 de 15 lo deja junto a Flutter | hasta el turno 10 |
| Flutter (pivot) | desde el 5, 100% | desde el 5 |
| Presupuesto 30000 (contradiction) | nunca | turnos 3 a 8 |
| Presupuesto 80000 (contradiction) | nunca | turnos 8 a 13 |

En growing, el 90% del turno 20 viene de la lista de tecnologías. Datadog, dicha en el turno 19, no entró al metadata en 6 de 15 conversaciones. Google Calendar, S3 y Redis faltaron en 2 o 3 conversaciones desde el turno siguiente a nombrarlas. El extractor reescribe la lista completa en cada turno y a veces se le queda una afuera.

## 3. Adjuntos grandes

Primer turno de cada conversación, con el mismo texto y el mismo `project_type`. Cada PDF trae un dato al principio (Stripe) y otro al final (Kafka).

| KB | n | Caracteres que llegan | tokens_in | P50 ms | P95 ms | Costo del turno US$ | Stripe en la respuesta | Kafka en la respuesta |
|---|---|---|---|---|---|---|---|---|
| 0 | 9 | 0 | 1708 | 3424 | 3986 | 0.00067 | - | - |
| 5 | 9 | 5213 | 3710 | 4436 | 5569 | 0.00126 | 100% | 100% |
| 20 | 9 | 20038 | 9307 | 4708 | 5531 | 0.00236 | 100% | 0% |
| 50 | 9 | 20038 | 9307 | 4430 | 5248 | 0.00236 | 100% | 0% |
| 100 | 9 | 20039 | 9307 | 4525 | 4855 | 0.00235 | 89% | 0% |

Desde 20 KB el adjunto se corta en 20.000 caracteres. Por eso 20, 50 y 100 KB dan exactamente los mismos tokens y el mismo costo, y el dato del final no llega nunca al modelo. Con 100 KB, el modelo lee solo el primer 20% del documento. El adjunto también se queda en la ventana los 6 turnos siguientes: con 100 KB, el turno 6 manda 14.346 tokens, y el turno 7, cuando el adjunto ya salió, baja a 6.970.

## 4. Dónde empieza a romperse mi CAG y por qué

Lo primero que se rompe es la memoria, y se rompe sin avisar. Lo que tiene un campo en el `project_metadata` aguanta los 20 turnos: el nombre Nimbus sigue en el 100% de las conversaciones, y Flutter reemplazó a React Native en 14 de 15. Lo que no tiene campo vive solo en la ventana de 6 turnos. El presupuesto de 30.000 € desaparece en el turno 9 y el de 80.000 € en el turno 14. En el turno 20, cuando se pide la estimación "con el presupuesto vigente", ninguna de las 15 conversaciones lo tiene, y el recall del escenario contradiction se queda en 50% desde el turno 6. Lo mismo pasa con los adjuntos: desde 20 KB, el dato del final del documento no llegó al modelo en ninguna de las 27 conversaciones, y la API respondió 200 todas las veces. Ninguna prueba se pone roja y ninguna llamada falla. Es degradación silenciosa, y es más peligrosa que un error, porque la estimación sale con el mismo formato y la misma seguridad, pero con datos de menos.

El costo y la latencia crecen, pero a esta escala no rompen. El turno 20 manda 6,9 veces los tokens de entrada del turno 1 (de 1.708 a 11.722) y cuesta 3,7 veces más (de US$ 0,00067 a US$ 0,00251). La latencia pasa de 3,3 s a 6,4 s, y el P95 queda en 7,0 s, bajo el presupuesto de 8 s en el 99% de las llamadas. El presupuesto de US$ 0,002 por llamada sí se rompe, cada vez más desde el turno 13: en el turno 20, el 60% de las llamadas lo pasa. La ventana limita los mensajes, pero no su largo. La dimensión que domina la degradación es la pérdida de memoria. El caso límite que justifica pasar a RAG es un proyecto con datos que no caben en campos fijos (presupuestos, acuerdos, decisiones que cambian) o con documentos de más de 20.000 caracteres. Este CAG no puede recuperarlos cuando salen de la ventana o quedan fuera del corte, ni puede avisar que los perdió. Un RAG los buscaría en el turno en que se necesitan, dentro del documento completo.
