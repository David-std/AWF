# Auditoría de transferencia: DSR-001..DSR-015 (AWS 3.19.1 → AWF)

**Estado:** evaluación técnica preliminar y *prototipo aislado*, no adjudicación final ni cierre de una regla del corpus. No se publica texto del ZIP histórico ni ejemplos privados. Documento derivado de la inspección local autorizada de la versión SHA-256 `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c` y sus verificadores históricos.

**Fuentes históricas inspeccionadas localmente:** `runtime/artifact_ledger.py`, `runtime/audit_controller.py`, `runtime/dirty_graph.py`, `runtime/fresh_critic.py`, `runtime/runtime_policy.json`, `tools/stateful_selftest.py`, `tools/stateful_final_gate_selftest.py` y las 15 entradas correspondientes del ledger. Estos archivos siguen exclusivamente en el ZIP local. Su estado `IMPLEMENTED` es una afirmación del paquete heredado, no una aprobación de AWF.

## Hallazgos de transferencia

1. La función histórica de cobertura devuelve `1.0` con cero comprobaciones aplicables registradas; así que el cumplimiento de toda la cobertura no puede derivarse del inventario de auditorías *observadas*. AWF debe exigir un inventario esperado no vacío y probar que cada chequeo exigido fue ejecutado.
2. La función histórica de edición detecta cambios de texto/contexto e invalida ciertos recibos, pero no actualiza automáticamente `dirty_set`; el código de autoensayo vacía ese conjunto explícitamente. AWF actualiza estado sucio en la misma transición que acepta la nueva versión.
3. La auditoría histórica se relaciona con un hash de artefacto y hashes locales, mientras reutiliza auditorías distantes. AWF **solo** revalida una auditoría anterior sobre el artefacto actual cuando su alcance expresamente acotado tiene la misma huella de dependencia; el recibo reanudado registra el hash de origen y la nueva versión. Por defecto, el alcance es **DOCUMENT**.
4. Las comprobaciones previas sobre `critic_id`, `inherited_findings` y `clean_sweeps` validan recibos declarativos; no demuestran que el evaluador fuera verdaderamente independiente. AWF exige identificadores distintos y evidencia de aislamiento, pero mantiene la independencia real como **pendiente de verificación externa**.
5. Los autoensayos históricos resultan pertinentes, pero no constituyen controles de calidad académica. No se ha demostrado un porcentaje de reducción de detectores ni un desempeño de una red neuronal mediante estos contratos.

## Trazabilidad por requisito (15/15; decisiones *propuestas*)

| ID | Disposición técnica propuesta | Trabajo verificable en el prototipo | Brecha pendiente antes de considerar migrado |
|---|---|---|---|
| DSR-001 | `KEEP_AS_CODE` candidata | Hash original, alcance de auditoría y validación de versión actual | Recibos firmados o verificador independiente del resultado |
| DSR-002 | `KEEP_AS_CODE` candidata | Una edición invalida automáticamente recibos dependientes | Grafo de dependencias editoriales completo, no solo documento/vecindad |
| DSR-003 | `KEEP_AS_CODE` candidata | Estados `AUDIT_REQUIRED` vs `EDIT_REVIEW_REQUIRED` | Scheduler completo `AUDIT_ONLY`/`EDIT` y separación de roles |
| DSR-004 | `KEEP_AS_CODE` candidata | Hallazgo OPEN permanece hasta resolución explícita | Persistencia durable y adjudicación de evidencia |
| DSR-005 | `KEEP_AS_CODE` condicionada | Recibo de evaluación requiere referencia a contexto aislado | Comprobar realmente contexto fresco y no herencia de diagnóstico |
| DSR-006 | `KEEP_AS_CODE` candidata | Dos críticos con IDs distintos, hashes actuales y evidencia | Evidencia de independencia más allá de IDs declarados |
| DSR-007 | `KEEP_AS_CODE` candidata | Nuevas ediciones restablecen la secuencia de críticos | Ampliar a todos los artefactos derivados/ediciones externas |
| DSR-008 | `KEEP_AS_CODE` candidata | Sin inventario esperado/recibos/estado limpio no hay convergencia | Demostrar que inventario de ejes y fuentes exigidos está completo |
| DSR-009 | `KEEP_AS_CODE` condicionada | Reutilización con fingerprint vecinal idéntico y linaje | Demostrar ausencia de dependencias globales por eje antes de usar alcance local |
| DSR-010 | `KEEP_AS_CODE` candidata | Recibos ligados a versión vigente en lugar de un número de pasada | Implementación real de todas las familias de ejes del pipeline |
| DSR-011 | `KEEP_AS_CODE` condicionada | Un tipo de política y un controlador funcional del prototipo | Revisar aliases y eliminar cualquier segundo scheduler real |
| DSR-012 | `KEEP_AS_CODE` condicionada | Constantes iniciales 8 ciclos, 12 iteraciones externas, 2 barridos | Comprobar alcance y política de iteraciones externas, compatibilidad de aliases |
| DSR-013 | `KEEP_AS_CODE` candidata | Presupuesto agotado produce `BUDGET_EXHAUSTED`, no PASS | Tiempos y presupuestos externos con informes explícitos |
| DSR-014 | `KEEP_AS_CODE` condicionada | Historial de eventos tipado en estado inmutable (solo memoria) | Journal durable/atómico, restauración y reinicio de proceso |
| DSR-015 | `KEEP_AS_CONTEXT` candidata | No implementado en el prototipo | Reconstruir paquetes de ejecución con conocimiento íntegro y dependencia auditada |

Estas son hipótesis de transferencia **sin `REVIEW_ATTESTED`**: aún no se ha registrado una decisión de revisión fundamentada por ID, autorizado derechos de entrenamiento ni validado el comportamiento dentro de un sistema completo.

## Contrato y límites del prototipo

`src/awf/domain/revision_audit.py` representa un núcleo de estado **independiente del LLM y del ZIP**; usa la `DocumentIR` de Sprint 1. No es todavía una API/CLI de producción ni un motor de evaluación semántica. Para validar una auditoría se necesitan ejes, bloques, trabajo obligatorio y referencias de evidencia. Los registros de las pruebas son simulados y no equivalen a opiniones humanas calificadas.

Una edición invalida los recibos globales; un recibo local solo se conserva si el texto propio y vecinos siguen idénticos y si el ámbito local fue elegido explícitamente. Los resultados semánticos, dependencias entre referencias, persistencia y seguridad de acceso siguen pendientes.

**Métricas de verificación exigidas antes de elevar estado:**
- `expected_work > 0`; nunca aceptar un `PASS` por denominador vacío.
- `all_expected_audits_current == true`, con hashes de documento/alcance.
- `dirty_count == 0`; `open_material_findings == 0`.
- `distinct_clean_critics >= 2` y todos vinculados a la versión actual.
- `false_passes_on_adversarial_cases == 0` para los negativos conocidos.
- Historial duradero y verificación independiente de evidencia cuando el prototipo se convierta en componente de producción.

No confundir la tasa de pruebas automatizadas aprobadas con validez de la revisión lingüística, de un detector o de sus fuentes.

## Endurecimiento del prototipo (segunda pasada)

El control de `max_external_iterations` ahora tiene una transición tipada que incrementa el contador y bloquea nuevas iteraciones cuando se agota la cuota. El número de barridos independientes es configurable a través de una sola política; la inserción de un tercer barrido no queda bloqueada indebidamente por los valores por defecto. Se rechazan explícitamente recibos con identidad de crítico repetida, referencia de aislamiento reutilizada y estados de auditoría entregados como cadenas sin tipar. Estas barreras **no** prueban independencia real, calidad lingüística ni cumplimiento de todo el corpus.
