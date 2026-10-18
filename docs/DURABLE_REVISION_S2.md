# S2 — revisión durable, recuperación y reintentos

`SQLiteRevisionJournal` coordina dos clases de información bajo una transacción
SQLite: los eventos de evidencia y los estados inmutables `RevisionState`.
Su alcance incluye `START`, `AUDIT`, `EDIT`, `FINDING_OPEN` y
`FINDING_RESOLVE`; no reemplaza la API previa en memoria ni habilita
convergencia autónoma.

## Uso del contrato Python

```python
from pathlib import Path

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.domain.revision_audit import AuditSlot, AuditStatus

# Datos sintéticos: sustituir por un documento real que permanezca privado.
document = MarkdownAdapter().parse(b"Synthetic claim.", source_name="demo.md")
journal = SQLiteRevisionJournal(Path(".awf/evidence/ledger.sqlite"))
journal.initialize()
slot = AuditSlot(document.blocks[0].block_id, "sources", required_checks=2)
created = journal.create(
    revision_id="revision-1", operation_id="request-start-1", run_id="run-1",
    document=document, slots=(slot,),
)
committed = journal.record_audit(
    revision_id="revision-1", operation_id="request-audit-1", run_id="run-1",
    document=document, expected_version=created.version, slot_key=slot.key,
    status=AuditStatus.CLEAN, checks_executed=2,
    observation_ref="synthetic:review-note",
)
recovered = journal.load(
    revision_id="revision-1", expected_head=journal.ledger.verify().head_digest,
)
```

El mismo `operation_id` y la misma solicitud pueden repetirse tras una caída
o pérdida de respuesta: se devuelve el commit original con `replayed=True` y
no se duplica el evento. **No reutilizar** esa clave para una operación nueva.
Si otro escritor avanzó la revisión, se rechaza `expected_version` obsoleto.
Cuando se reenvía una operación antigua después de otras más recientes, la
respuesta de replay refleja el estado de aquella operación, no el último;
consultar `load` para trabajar sobre la cabeza actual.

La recuperación vuelve a leer la cadena de evidencias y los estados persistidos.
La ausencia de una fila no es una operación pendiente que pueda aprobarse: si
existe su evento de commit, la discrepancia bloquea el acceso. Si la caída fue
anterior al COMMIT, ni la evidencia ni el nuevo estado se consideran confirmados
y la solicitud puede repetirse con la misma clave.

`load(expected_head=...)` coteja el digest final con un valor **conservado fuera
de la base de datos**; utilizar como head externo uno copiado de la base
potencialmente comprometida no proporciona independencia. La aplicación debe
conservar dicho valor de modo seguro. Este prototipo no firma ni publica heads.

## Edición y hallazgos durables

Tras crear y auditar una revisión con los comandos anteriores:

```python
from awf.domain.revision_audit import RevisionPolicy

revised = MarkdownAdapter().parse(b"A changed synthetic claim.", source_name="demo-v2.md")
edited = journal.accept_edit(
    revision_id="revision-1", operation_id="request-edit-1", run_id="run-1",
    old_document=document, new_document=revised, expected_version=committed.version,
    policy=RevisionPolicy(), observation_ref="review-note:edit-1",
)
finding = journal.open_finding(
    revision_id="revision-1", operation_id="request-find-1", run_id="run-1",
    expected_version=edited.version, finding_id="finding-1", material=True,
    observation_ref="review-note:observation-1",
)
resolved = journal.resolve_finding(
    revision_id="revision-1", operation_id="request-resolve-1", run_id="run-1",
    expected_version=finding.version, finding_id="finding-1",
    observation_ref="review-note:resolution-1",
)
assert journal.load(revision_id="revision-1").state == resolved.state
```

Una transición nueva registra dos eventos `REVISION_TRANSITION` y un snapshot
en una transacción: intención y commit, enlazados por identidad de evento.
La recuperación reproduce las reglas de invalidación y resolución contra
el snapshot precedente. Los commits `START/AUDIT` de esquema 1 se leen sin
conversión; los nuevos usan esquema 2.

Ambos `DocumentIR` deben obtenerse de ingesta cotejada contra los bytes
inmutables. El journal almacena hashes, huellas de IR y fingerprints de
scope, no texto del manuscrito ni prueba de consentimiento humano.
`observation_ref` es una declaración trazable pero no autenticada.
La referencia `event:<digest>` demuestra que quedó registrada, no que sea
científicamente correcta.

## Restricciones deliberadas

- Los snapshots guardan metadatos, hashes, referencias y hallazgos, no el texto
  completo del manuscrito. Permanecen privados y sujetos a los permisos locales.
- `record_evidenced_audit` de PR #18 sigue existiendo para prototipos en memoria;
  no promete coordinación transaccional de estado. El camino durable es
  `SQLiteRevisionJournal.record_audit`.
- No hay comandos durables para barridos de críticos, iteraciones externas ni
  aprobación académica. El estado `CONVERGED` no se autoriza por integridad SQLite.
- Una comprobación positiva de la cadena y de los recibos no prueba competencia,
  identidad, independencia o corrección de los juicios académicos.
- Coste actual O(historial) para integridad; faltan benchmark, backup/restore,
  checkpoint externo firmado, permisos de evaluadores y pruebas de cortes de
  energía sobre el equipo y almacenamiento reales.

Consulta [ADR-0014](adr/0014-atomic-revision-journal.md) para la transacción
original y [ADR-0015](adr/0015-durable-edit-and-finding-transitions.md) para
la extensión y sus límites.
