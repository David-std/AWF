# ADR-0013 — Enlace de recibos a eventos concretos, no a hashes sueltos

- **Estado:** prototipo verificable del Sprint 2, aún no autorización de ejecución autónoma.
- **Fecha:** 2026-10-17.
- **Fuente previa:** ADR-0010 (auditoría), ADR-0011 (integridad del conocimiento) y ADR-0012 (ledger local SQLite).

## Problema

El ledger de ADR-0012 almacena evidencia, pero las puertas anteriores aceptaban `evidence_ref` como una cadena arbitraria. Incluso una referencia por SHA-256 a contenido existente no prueba que corresponda a la misma operación, revisión, sujeto o ejecución. Una nueva sesión podría reutilizar un resultado no aplicable; tampoco bastaría para distinguir fragmentos de texto idénticos atribuidos a fuentes diferentes.

## Decisión

1. Cada recibo enlazado usa `event:<64 hex>`, el **digest del evento** que une `run_id`, `subject_id`, `EvidenceKind`, contenido y posición en la cadena. No aceptar un SHA de contenido desnudo como comprobación del recibo.
2. `EvidenceStorePort.resolve_event` obtiene evento y bytes del almacén en **una sola transacción de lectura** y verifica toda la cadena; opcionalmente coteja el `expected_head` conservado de forma independiente.
3. `record_evidenced_audit` primero valida mediante la función de dominio pura, luego persiste el payload canónico con ID de tarea, hash de artefacto y alcance, estado, comprobaciones ejecutadas y referencia de observación. Si falla la persistencia, el estado anterior no se muta. El registro de observación es declarativo, no prueba de independencia.
4. `verify_audit_receipts` comprueba todos los slots previstos, no solo los que aparezcan espontáneamente. Rechaza `OPEN`, dirty, artefactos obsoletos, ámbito incorrecto, estado o número de comprobaciones diferentes. También rechaza duplicados de slots o recibos y claves dirty ajenas al inventario, que podrían ocultar un estado inconsistente. Permite traslado local solo cuando la huella del alcance sigue vigente y conserva la procedencia original.
5. `record_evidenced_chunk` conserva bytes del fragmento en local; `verify_chunk_coverage` exige que cada `ChunkReceipt` apunte al evento de tipo `SOURCE_CHUNK` con el ID de referencia, fragmento y ejecución esperados. Las observaciones sobre ejes se vinculan al tipo `AUDIT_RECEIPT` y a su eje específico. La comprobación estructural `assess_coverage` se vuelve a ejecutar: ausencia, duplicación, cambio o error de un fragmento bloquea `complete`.
6. `record_stage_claim` no acepta `complete_chunk_coverage=True` ni resultados `UNDERSTOOD`/`APPLICABLE` como simples booleanos. Para READ vuelve a consultar el inventario y el ledger; para comprensión/aplicabilidad exige un evento de adjudicación diferente, con tipo, contexto y sujeto verificados. En `verify_progress_claims`, READ exige nuevamente los mismos recibos/manifest; no basta leer un `stage=READ` previamente guardado. Todas las etapas de una progresión deben pertenecer a **la misma ejecución**: combinar eventos auténticos de ejecuciones distintas no demuestra una progresión válida.
7. Los módulos de dominio permanecen independientes del almacenamiento; los límites efectos/IO se gestionan desde la capa de aplicación.

## Amenazas y límites

- El sistema ofrece **vinculación verificable de metadatos y bytes locales**, no firmas, prueba de lectura humana, autenticidad de evaluador, validez de razonamiento, independencia de crítico o calidad editorial. `independent_adjudication_proven` es siempre `False` en este corte.
- `UNDERSTOOD` contiene un evento de adjudicación registrado, **pero no se demuestra** que provenga de un humano cualificado ni de un experimento con respuestas selladas. El gate automático final debe requerir esa revisión confiable.
- El checkpoint opcional evita aceptar un prefijo internamente consistente cuando un hash final previo se conservó externamente; sin ese anclaje, un atacante con acceso total puede reescribir la base.
- Sin control transaccional conjunto entre el ledger y el estado de revisión, una caída después del append puede dejar **eventos válidos sin vincular a un estado confirmado**. Son auditables pero no conceden aprobación. Persistencia del estado de revisión y recuperación coordinada quedan para un siguiente corte.
- Verificar la cadena completa por referencia tiene costo potencial O(n²) para muchos fragmentos. Se necesita benchmark, vistas transaccionales de lectura y verificación por lotes antes de grandes corpus.
- Por privacidad, solo se utilizan bytes sintéticos en pruebas publicadas. El ZIP histórico no se publica, sus reglas no se promueven y los datos de entrenamiento requieren un permiso separado.

## Aceptación

Pruebas adversariales: referencia sin evento, intercambio entre fragmentos/operaciones, tipo o ejecución incorrectos, mezcla de etapas de ejecuciones distintas, duplicación de recibos o dirty keys ajenas, artefacto obsoleto, alcance inconsistente, tarea ausente, falta de calibración real, transición READ sin fragmentos comprobables, distinto checkpoint, pérdida de evidencia, reinicio del proceso, escritura fallida sin mutar estado puro. CI Linux/Windows × Python 3.12/3.13 y reproducción local con datos sintéticos.
