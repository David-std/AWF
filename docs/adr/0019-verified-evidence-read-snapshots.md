# ADR-0019 — Lectura de evidencias verificada una vez por snapshot

- **Estado:** incremento S2 medido, aún no objetivo de latencia en producción.
- **Fecha:** 2026-10-20 (UTC).
- **Base:** ADR-0012, ADR-0013, ADR-0017 y ADR-0018; `develop` tras PR #24.

## Problema y riesgo de integridad

`resolve_event` revalida el esquema, la cadena completa de eventos y **todos**
los bytes almacenados antes de resolver un evento. Esta garantía es correcta
para consultas individuales. Sin embargo, los flujos de cobertura, auditoría
y progreso llaman `resolve_event` para cada recibo, repitiendo la auditoría
completa `m` veces para `m` recibos sobre `n` eventos y objetos. Para `m≈n`,
el trabajo pasa a ser aproximadamente cuadrático.

Omitir auditorías por medio de un caché persistente de head sería peligroso:
la base podría haberse alterado entre llamadas o reemplazado por un prefijo
internamente coherente. Leer recibos en transacciones separadas también puede
mezclar varios heads mientras otros procesos escriben.

## Decisión y contratos

1. `EvidenceStorePort.verified_read` entrega un
   `VerifiedEvidenceReaderPort` **solo durante** un contexto acotado. La
   implementación SQLite abre una transacción `BEGIN`, comprueba la definición
   real de tablas/triggers y audita todos los eventos, objetos, hashes y claves
   externas esperadas **dentro de esa misma transacción**.
2. Después de la auditoría, la lectura individual del contexto consulta un
   evento por digest y vuelve a contrastar identidad, payload, longitud y
   hash, sin repetir el recorrido completo. Sigue rechazando un digest
   inexistente, incorrecto o asignado a otro run/sujeto/tipo; el caso de uso
   contrasta esos metadatos por recibo.
3. `verify_chunk_coverage`, `verify_audit_receipts` y
   `verify_progress_claims`, incluyendo el `READ` anidado, usan **una** vista
   de lectura por operación. Si falla el head confiable o la integridad, no
   se confirma ningún recibo; las puertas siguen devolviendo un resultado
   conservador e identificando recibos inválidos cuando hay contexto seguro.
4. `resolve_event` conserva su firma pública y continúa comprobando el
   historial completo para llamadas individuales. No se almacenan cabezas
   autorizadas ni reportes reutilizables tras cerrar el contexto.
5. Un append WAL concurrente **no** cambia retroactivamente la vista abierta.
   Si el usuario exige comprobar que un checkpoint es el head *actual después*
   de la lectura, debe validar una nueva transacción; la lectura prueba el
   head fijado **durante** esa operación, no una ausencia futura de escrituras.

## Alternativas

| Alternativa | Evaluación |
|---|---|
| Saltarse verificación y confiar en índice de digest | Rechazada: bytes y esquemas adulterados podrían quedar sin detectar |
| Cachear el digest del último head entre solicitudes | Rechazada: no protege frente a tampering, rollback ni cambios entre llamadas |
| Resolver cada evento con su propia auditoría | Seguro pero crece aproximadamente con `n × m`; queda para consultas aisladas |
| Resolver muchos eventos dentro de una única transacción previamente auditada | Elegida: conserva el costo `O(n + m)` aproximado y una vista coherente |

## Pruebas y límites

- Contar llamadas reales a `_audit_transaction`: una para 48 fragmentos, una
  para ocho recibos de auditoría y una para etapas con READ y 16 fragmentos.
- Durante una verificación de etapas, un escritor agrega evidencia nueva:
  la operación permanece en el head firmado inicialmente; una operación
  posterior con el antiguo head falla cerrada.
- Detectar cambio de trigger, digest inexistente, head equivocado, run/sujeto
  intercambiados y payload incompatible; preservar resultados conservadores.
- Benchmark reproducible con `scripts/benchmark_evidence_reader.py`, bytes
  sintéticos y volúmenes de 16, 64, 128 eventos; no se leen manuscritos.

**Límites:** la auditoría completa sigue siendo `O(n)` por operación de alto
nivel y `append` todavía audita todo el historial antes de escribir; el replay
de revisiones también merece medición separada. El contexto conserva un lector
WAL temporalmente, por lo que un trabajo de millones de fragmentos necesitará
límites de duración/paginación antes de declararse escalable. Estos cambios no
demuestran custodia independiente, autenticidad de un evaluador, verdad de una
fuente ni adjudicación académica. **0/168 MUST** formalmente resueltas.
