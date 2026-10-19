# S2 — eventos de evidencia vinculados a contratos

El prototipo de [ADR-0013](adr/0013-evidence-bound-receipts.md) conecta el ledger local con recibos de auditoría y de fuentes. No existe aún un editor neuronal ni un verificador académico externo operativo.

## API de aplicación

`awf.application.commands.bind_evidence` implementa:

- `record_evidenced_audit`: primero valida el estado inmutable y después inserta un evento con contenido canónico.
- `verify_audit_receipts`: compara cada recibo actual con un evento exacto del ledger, su contenido y el inventario del documento.
- `record_evidenced_chunk` y `verify_chunk_coverage`: vinculan fragmentos al origen, sujeto y sesión declarados.
- `record_stage_claim` y `verify_progress_claims`: registran etapas epistémicas, comprueban evidencia de READ desde manifest/fragmentos y exigen una fuente de adjudicación independiente en el ledger para las etapas de comprensión y aplicabilidad.

Los eventos se identifican como `event:<digest>`, no como `sha256:<payload>`. La consulta `resolve_event` de la capa de persistencia compara ejecución, sujeto, tipo de evidencia, integridad de la cadena, objeto y opcionalmente el hash final guardado fuera de SQLite.

### Modelo de resultado

El objeto `EvidenceGateResult` informa `checked`, `unverified`, `local_integrity_passed` e `independent_adjudication_proven`. **Este último permanece falso por diseño:** ninguna evidencia local demuestra por sí misma que las decisiones del evaluador fueran correctas.

### Restricciones de aceptación

No promocionar `local_integrity_passed=True` a `CONVERGED` o aprobación académica. Para una evaluación real todavía se necesitan control de identidad, firmas/checkpoints independientes, evaluadores autorizados, persistencia coordinada de estado y revisión empírica de los casos con adjudicación. No exportar fragmentos originales ni respuestas de holdout a GitHub.
