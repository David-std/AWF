# S2 — Perfilado de lecturas de evidencia sin debilitar su integridad

El verificador de recibos ahora puede compartir un único snapshot SQLite
previamente auditado durante la revisión de múltiples fragmentos y estados.
La operación sigue comprobando **todos** los hashes del ledger y objetos antes
de confiar en cualquiera de sus resultados.

## Comparación reproducible

Desde el árbol de AWF, con Python 3.12 y dependencias instaladas:

```shell
uv run python scripts/benchmark_evidence_reader.py --events 16 64 128 --repeats 3
```

El script construye una base temporal con bytes **sintéticos**, resuelve todos
los eventos primero mediante `resolve_event` individual (auditoría completa
por llamada) y después mediante `verified_read` (una auditoría y `m` lecturas).
Comprueba la igualdad de los bytes resueltos en ambos recorridos. Devuelve
medianas por tamaño, versión de Python y plataforma. No mide la validez
académica ni expone datos originales.

Primer resultado local observado el 2026-10-20, Linux / CPython 3.12.14:

| Eventos | Auditoría por llamada | Un snapshot auditado | Mejora observada |
|---:|---:|---:|---:|
| 16 | 9,199 ms | 0,665 ms | 13,84× |
| 64 | 78,185 ms | 1,762 ms | 44,37× |
| 128 | 249,342 ms | 3,328 ms | 74,92× |
| 256 | 799,826 ms | 5,737 ms | 139,42× |

Las cifras son de un equipo y un conjunto artificial pequeños; no son una
garantía de throughput, p95 ni rendimiento con WAL bajo contención. Para un
objetivo operativo real faltan perfilar equipos, discos, WAL grande, miles de
eventos, tamaños de payload diversos y el replay por documento.

## Contrato para consumidores de aplicación

`EvidenceStorePort.verified_read(expected_head=...)` produce un
`VerifiedEvidenceReaderPort` solo dentro de `with`. Cada `resolve_event` dentro
de él mantiene las mismas verificaciones de identidad, bytes y metadatos que
la ruta individual, pero comparte la auditoría completa de su transacción.
No conservar el lector fuera del contexto ni transferirlo entre hilos.

`verify_chunk_coverage`, `verify_audit_receipts` y `verify_progress_claims`
adoptan el contexto internamente. Un escritor puede añadir eventos después de
que comenzó la lectura; la transacción no los incorpora de forma parcial.
Cuando se requiera el head vigente al finalizar, iniciar otra validación
firmada. Un resultado local nunca autoriza adjudicación científica ni
certifica que un agente leyó o entendió los fragmentos.

Decisión: [ADR-0019](adr/0019-verified-evidence-read-snapshots.md).
