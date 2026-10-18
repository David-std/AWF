# S2 — revisión durable, recuperación y reintentos

`SQLiteRevisionJournal` coordina dos clases de información bajo una transacción
SQLite: los eventos de evidencia y los estados inmutables `RevisionState`.
**Su alcance es únicamente `START` y `AUDIT`**; no reemplaza la API previa
en memoria ni habilita convergencia autónoma.

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

## Restricciones deliberadas

- Los snapshots guardan metadatos, hashes, referencias y hallazgos, no el texto
  completo del manuscrito. Permanecen privados y sujetos a los permisos locales.
- `record_evidenced_audit` de PR #18 sigue existiendo para prototipos en memoria;
  no promete coordinación transaccional de estado. El camino durable es
  `SQLiteRevisionJournal.record_audit`.
- Aún no hay comandos durables para edición, findings, barridos de críticos ni
  cambios de política. No continuar una de esas operaciones como si estuviera
  confirmada a través de este journal.
- Una comprobación positiva de la cadena y de los recibos no prueba competencia,
  identidad, independencia o corrección de los juicios académicos.
- Coste actual O(historial) para integridad; faltan benchmark, backup/restore,
  checkpoint externo firmado, permisos de evaluadores y pruebas de cortes de
  energía sobre el equipo y almacenamiento reales.

Consulta [ADR-0014](adr/0014-atomic-revision-journal.md) para la decisión y
sus alternativas.
