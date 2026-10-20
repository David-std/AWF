# Sprint 2 — perfil reproducible del replay de revisiones

Medición exploratoria **sin cambiar el runtime**. El script solo crea datos
sintéticos bajo `TemporaryDirectory` y no lee AWS 3.19.1, manuscritos ni `.awf/`.

```bash
uv sync --locked
uv run python scripts/benchmark_revision_replay.py \
  --cases 1:32 1:64 4:16 8:16 1:128 16:16 --repeats 3
```

Cada caso `R:A` crea R revisiones y A auditorías limpias por revisión, con un
slot obligatorio, una sola fuente de texto sintética, `operation_id` únicos y
eventos `START`/`AUDIT_RECEIPT`/`REVISION_TRANSITION` reales. El estado y la
cadena se verifican; errores detienen el ensayo. Se cronometra, tras un warmup:

- **`replay_only`:** reconstrucción tipada de una revisión desde una transacción
  interna. Diagnóstico únicamente, **no** API que el usuario deba adoptar.
- **`verified_load_one`:** `load(expected_head=...)` con revisión completa de
  DDL, eventos, objetos y estados de una revisión.
- **`verified_all_revisions`:** verificación íntegra del ledger y de todas las
  revisiones en el mismo snapshot de lectura.

Memoria es máximo atribuido por `tracemalloc` durante otra ejecución, no RSS;
consultas SQL son llamadas perfiladas en una invocación adicional de `load`.
No se mide la creación de los fixtures ni coste de hardware persistente.

## Observaciones locales iniciales

Linux x86-64, CPython 3.12.14, SQLite 3.53.1, 20 de octubre de 2026;
mediana de tres ejecuciones por caso. Los números en milisegundos no son un
SLO ni necesariamente extrapolables al PC Windows del usuario.

| Revisiones × auditorías | Eventos | Replay una revisión | `load` completo | Verificar todas |
|---|---:|---:|---:|---:|
| 1 × 32 | 65 | 4,268 | 5,287 | 5,666 |
| 1 × 64 | 129 | 10,927 | 13,095 | 11,202 |
| 1 × 128 | 257 | 23,737 | 36,434 | 29,466 |
| 4 × 16 | 132 | 3,099 | 4,683 | 10,793 |
| 8 × 16 | 264 | 2,665 | 7,188 | 21,556 |
| 16 × 16 | 528 | 3,112 | 25,102 | 52,481 |

El último caso tuvo una ejecución de 318,187 ms al verificar todo; las demás
estuvieron entre 47,202 y 52,481 ms. La dispersión impide extrapolar una
latencia p95. Para 1 × 128, el perfil local midió 530 llamadas SQL en `load`
y ~2,55 MiB de memoria trazada de pico; codificar/decodificar 129 estados
representó parte sustancial del tiempo. Para 16 × 16, la auditoría del ledger
global dominó `load` de una sola revisión. Esas proporciones dependen de la
distribución de revisiones, no solo del número total de eventos.

## Conclusión operativa

No hay aún presupuesto de latencia ni distribución real de trabajo que permita
priorizar una optimización con garantías. Se conserva replay exhaustivo,
`BEGIN` coherente, CAS, validación de DDL y los checkpoints externos.

Las mejoras candidatas posteriores son agrupación de consultas del replay,
sin omitir ninguna verificación, y reducción de asignaciones intermedias; deben
compararse con estos datos en Linux y Windows al mismo SHA y con pruebas de
tamper/corrupción, WAL, concurrencia y restauración. Próximo incremento separado:
barridos críticos e iteraciones externas durables (ADR futura separada).
