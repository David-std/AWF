# S2 — Registro atómico por lotes de fragmentos observados

El incremento añade `SQLiteEvidenceLedger.append_batch` y el caso de uso
`record_evidenced_chunks` para registrar varios fragmentos declarados por un
manifiesto. Ambos son APIs Python; el comando CLI existente `evidence append`
continúa registrando un único archivo/evento sin cambios de argumentos.

## Ejemplo sintético

```python
from pathlib import Path

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.bind_evidence import ObservedChunk, record_evidenced_chunks
from awf.domain.knowledge_integrity import SourceInput, build_manifest

store = SQLiteEvidenceLedger(Path(".awf/evidence/synthetic.sqlite"))
store.initialize()
raw = b"abcdefgh"
manifest = build_manifest(
    (SourceInput("ref-1", raw, "private:synthetic"),),
    version="v1", expected_axes=("fidelity",), chunk_bytes=4,
)
head = store.verify().head_digest
receipts = record_evidenced_chunks(
    store=store, manifest=manifest,
    observations=(ObservedChunk("ref-1", "C0001", b"abcd"),
                  ObservedChunk("ref-1", "C0002", b"efgh")),
    run_id="run-1", reader_ref="reader-1", expected_head=head,
)
assert len(receipts) == 2
assert store.verify().events_checked == 2
```

Usar únicamente bytes sintéticos en ejemplos públicos. Los bytes almacenados
en la base son privados; `.awf/` está ignorado en Git. Guardar checkpoints
firmados y sus hashes a través de la política externa ya existente; la
operación no custodia las claves.

## Contratos y recuperación

- Las operaciones son ordenadas: cada evento enlaza el digest anterior,
  incluidos payloads idénticos reutilizados desde un objeto de contenido.
- Una escritura por lotes confirma **todos** los eventos o **ninguno**;
  rechaza anomalías de esquema, cadena, bytes, identidad y límites.
- `expected_head` contrasta un head previamente custodiado (si se dispone de
  él); evita añadir sobre un head obsoleto, no crea confianza externa.
- Un lote parcial puede registrar un subconjunto del manifiesto. La cobertura
  total y los ejes obligatorios se verifican después con
  `verify_chunk_coverage`; registrar eventos no significa `READ` ni `PASS`.
- Si falla una escritura, no reutilizar recibos calculados antes del COMMIT.
  Volver a validar el manifiesto y head antes de reintentar. La API de lote
  **no** ofrece idempotencia por clave de operación; reintentar un lote
  confirmado sin `expected_head` genera eventos nuevos.

Límites: 1–512 eventos, cada uno entre 1 y 524 288 bytes, máximo 8 MiB
por lote. La auditoría existente es O(n) por transacción y permanece
obligatoria; para inventarios mayores, dividir en lotes y usar controles
de cobertura al finalizar.

## Benchmark reproducible

```shell
uv run python scripts/benchmark_evidence_append.py --events 16 64 128 256 --repeats 3
```

Cada medición escribe los mismos bytes sintéticos en **bases temporales
separadas** mediante N llamadas `append` y una `append_batch`. La duración
comprende las escrituras, no la inicialización ni la verificación final; la
verificación íntegra de ambos casos se realiza fuera del cronómetro.

Linux / CPython 3.12.14, 2026-10-20, medianas de tres repeticiones:

| Eventos | N `append` | Un lote | Mejora observada |
|---:|---:|---:|---:|
| 16 | 43,480 ms | 3,286 ms | 13,23× |
| 64 | 175,047 ms | 4,260 ms | 41,09× |
| 128 | 401,947 ms | 4,847 ms | 82,93× |
| 256 | 1008,341 ms | 6,660 ms | 151,41× |

No son SLO ni comparaciones entre máquinas. Falta medir contención, múltiples
procesos, tamaños variados y miles de eventos; también queda pendiente
el perfilado del replay de revisiones.

Decisión: [ADR-0020](adr/0020-atomic-batched-evidence-append.md).
