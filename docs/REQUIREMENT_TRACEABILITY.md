# Matriz de trazabilidad de AWF — planificación v0.1

**Alcance:** esta tabla captura los requisitos expresados por el usuario y las decisiones del diseño AWF. NO afirma la migración individual de los 184 requisitos históricos de AWS: ese mapeo debe realizarse en S2 contra el ZIP original por ID, estado y evidencia. No confundir compromiso documental con código verificado.

Estados: `DESIGNED` (especificado), `OPEN` (requiere decisión), `IMPLEMENTED` (solo tras test automatizado + demostración), `RESEARCH` (hipótesis). Los estados son independientes por sprint. La importación S2 parcial no demuestra adjudicación del corpus ni ejecución de todas las reglas.

| ID | Requerimiento/decisión | Fuente del proyecto | Evidencia de aceptación prevista | Sprint | Estado |
|---|---|---|---|---|---|
| AWF-R001 | Conservar AWS 3.19.1 exacto con SHA/licencia/provenance, sin importar a ciegas | TDP/AWS y conversación | SHA del ZIP + manifest; derechos de redistribución por revisar | S0/S2 | IMPLEMENTED_PARTIAL |
| AWF-R002 | Mantener arquitectura para migración entre chats/agentes sin pérdida | Solicitud explícita del usuario | Spec completa, ADR, README, handoff, estado verificable | S0 | DESIGNED |
| AWF-R003 | Tipar reglas deterministas/probabilísticas/contextuales, evitar if masivos | Pregunta sobre skills ineficientes | Metadatos de 184 IDs conservados; adjudicación manual y tests por regla pendientes | S2 | IMPLEMENTED_PARTIAL |
| AWF-R004 | Evaluar redundancia, obsolescencia y contradicción de fuentes | Pregunta sobre investigación acumulada | Detectados duplicados normalizados; evaluación semántica/obsolescencia pendiente | S2/S6 | IMPLEMENTED_PARTIAL |
| AWF-R005 | Evitar que LLM se otorgue un PASS sin evidencia | Auditoría AWS | Inyección de falso recibo falla; verificación real sobre bytes | S3 | DESIGNED |
| AWF-R006 | Preservar causalidad, certeza, alcance, tiempo, cifras, citas y atribución | GDText/Meaning Audit | Mutaciones adversariales + gold + medición de falsos negativos | S3 | DESIGNED |
| AWF-R007 | Mantener originales inmutables con hash y rollback | Blueprint | Bytes originales intactos y SHA validado; rollback/diff aún pendiente | S1 | IMPLEMENTED_PARTIAL |
| AWF-R008 | Editor neuronal especializado y baselines abiertos | Comparación Stealth/Phrasly/CoEdIT | Mismo benchmark sobre modelo base y modelo de edición | S4 | DESIGNED |
| AWF-R009 | Entrenar adaptador propio SFT/LoRA/QLoRA, no de cero | Interés ML del usuario | Adapter versionado, dataset card y métricas vs baseline | S5 | DESIGNED |
| AWF-R010 | DPO únicamente con preferencias verificadas y no contaminadas | Literatura sobre rewards | Auditoría de preferencias + ablation; decisión go/no-go | S6 | DESIGNED |
| AWF-R011 | Holdout sellado por grupos y permisos de datasets | Riesgo de contaminación | Tests de no filtración a train/evaluador/embeddings | S3–S6 | DESIGNED |
| AWF-R012 | Editores/modelos intercambiables; sin vendor lock-in | Diseño hexagonal | Pruebas contractuales Dummy/Transformers/API | S1/S4 | DESIGNED |
| AWF-R013 | CQRS ligero, monolito modular, dominio puro | Preferencia de arquitectura estándar | Test de imports/capas + ADR sobre cambio | S0–S2 | DESIGNED |
| AWF-R014 | Calidad académica primero, detectores independientes de aceptación | Objetivos del proyecto | Ningún score de detector revierte falla crítica | S3/S8 | DESIGNED |
| AWF-R015 | Evidencia externa calificada por fecha/snapshot/autoría | Deep Research y fuentes | Source registry y model card con límites | S2/S4 | DESIGNED |
| AWF-R016 | ES/EN medidos por separado y sin trasferencia automática | Proyecto TDP | Reportes separados por idioma/género | S4–S6 | DESIGNED |
| AWF-R017 | Sprint demostrable, testado, sin archivos decorativos | Solicitud del usuario | Demo, tests, changelog, evidencia de CI por sprint | S0–S7 | DESIGNED |
| AWF-R018 | Escalable sin elegir stack web genérico por inercia | Solicitud del usuario | ADR con alternativas/trigger de migración | Continuo | DESIGNED |
| AWF-R019 | Ejecutable local con RTX 4050 y opción de Notebook/Google | Hardware comunicado por usuario | Perfil real de VRAM, OOM, throughput, quotas | S4–S5 | OPEN |
| AWF-R020 | Sin necesidad de compras ni suscripciones en S0–S3 | Restricción de viabilidad | Core/CI/offline ejecutables sin API keys/GPU | S0–S3 | DESIGNED |
| AWF-R021 | Investigación científica y benchmark reproducible, resultados negativos | Comparación de técnicas | Protocolos ablation + CI + reportes con CIs | S4–S8 | DESIGNED |
| AWF-R022 | Licencias, derechos de datasets y privacidad de manuscritos | Riesgo legal | Dataset Cards, permiso por fuente, local_only default | S0–S5 | OPEN |
| AWF-R023 | Código higiénico, tipado y test con principios SOLID aplicados | Solicitud de estándares | Ruff, pyright, pytest, hypothesis, quality gate CI | S0 | DESIGNED |
| AWF-R024 | No exigir una GUI antes de validar núcleo y benchmark | Riesgo de scope | CLI inicial, API posterior, sin React por defecto | S0–S7 | DESIGNED |
| AWF-R025 | Vincular dictámenes S2 a claves y roles de revisores autorizados | Riesgo de suplantación en ledger | Firma Ed25519, política externa fijada por SHA, caducidad/revocación, test de intercambio y CLI | S2 | IMPLEMENTED_PARTIAL |
| AWF-R026 | Detectar truncamiento/reconstrucción SQLite aunque conserve hashes internos | Riesgo de rollback del ledger tras firma de auditoría | Checkpoint externo Ed25519 con policy SHA-pinned, cadena de prefijos y pruebas de rollback/replay; custodia real sigue externa | S2 | IMPLEMENTED_PARTIAL |

## Procedimiento para implementar cada fila

Cada cambio crea relación verificable: `AWF-Rxxx → ADR → código/archivo → tests → commit → demo`. El PR registra evidencias ejecutadas, fallos y exclusiones. Nunca convertir DESIGNED en IMPLEMENTED solo porque existe un módulo vacío.

**AWF-R026:** [ADR-0017](adr/0017-externally-signed-ledger-checkpoints.md) → `domain/checkpoints.py`, `application/commands/checkpoints.py`, `SQLiteEvidenceLedger.verify_anchors` → `tests/integration/test_signed_checkpoints.py` (truncamiento de una instantánea SQLite válida, sustitución de bytes, permisos, firmas, política, JSON, historia y CLI). La aprobación interna no demuestra custodia externa real, disponibilidad de testigo ni tiempo confiable.

## Migración heredada AWS

La suite AWS 3.19.1 documenta 184 requisitos normativos (168 MUST, 16 lab/deferred), 22 comprobaciones semánticas atómicas y 54 casos JSON según la auditoría previa. **Estas cifras son inventario inicial, no cobertura ejecutada en AWF**. La migración exige rastrear IDs/fuentes y escoger `POLICY`, `MODEL_TRAINING`, `RETRIEVAL`, `EVAL_ONLY`, `DEPRECATED_WITH_EVIDENCE` o `UNRESOLVED` sin borrar originales. Para elementos de alto impacto, exigir prueba negativa que demuestre si la regla funciona de verdad.

## Estado verificado S0–S1 (rama de implementación)

- S0: CLI `awf --version`, empaquetado, lint, formato, tipado, tests y build ejecutados en CI (PR #11).
- S1: ingesta Markdown, IR inmutable, hashes, almacenamiento opcional e idempotencia comprobados en PR #12. No se ha implementado todavía la creación de revisiones ni un mecanismo de rollback de revisiones: el almacenamiento original permite conservar bytes, pero no demuestra un historial completo.
- Evidencia: [run S1 39076453243](https://github.com/David-std/AWF/actions/runs/39076453243), SHA `cbd05e9ba242c40eb3de0f6477a313342286860d`.
- Este progreso **no equivale a migrar los 184 requisitos históricos** ni a entrenar AWF. Mantenerlos como plan S2 en adelante.

## Avance controlado S2

- Se dispone de código y pruebas sintéticas para importar el ZIP local fijado por hash y generar un registro metadata-only. **No se han migrado decisiones de cumplimiento de las 168 reglas MUST**: permanecen `UNRESOLVED`.
- Las 16 entradas `DEFERRED_LAB` permanecen `EVAL_ONLY` y no pueden promocionarse a ejecución ni entrenamiento.
- `REVIEW_ATTESTED` documenta autor y razón de una decisión de investigación, pero no garantiza validez técnica, licencias o revisión independiente.
- Véase [ADR-0008](adr/0008-local-knowledge-import.md), [contrato S2](KNOWLEDGE_COMPILER_S2.md) y [PR #13](https://github.com/David-std/AWF/pull/13).

## Prototipo de auditorías DSR-001..015 (evidencia separada de adjudicación)

- ID fuente: `DSR-001..DSR-015` del ledger AWS 3.19.1, conservado solo localmente; archivo de evaluación propio [`STATEFUL_RUNTIME_DSR001_015.md`](reviews/STATEFUL_RUNTIME_DSR001_015.md).
- Implementación candidata: `src/awf/domain/revision_audit.py`; pruebas adversariales: `tests/unit/test_revision_audit_prototype.py`; [PR #15](https://github.com/David-std/AWF/pull/15).
- Evidencia de CI para el commit `e6c1b199599b0e31d25002225d14776eff6c2fdc`: [run 39084850246](https://github.com/David-std/AWF/actions/runs/39084850246), 4/4 jobs verdes, 61 tests por trabajo; 16 pruebas unitarias del módulo ejecutadas en la PC local.
- **Estatus correcto:** `PROTOTYPED_NOT_ADJUDICATED` en AWF, no `REVIEW_ATTESTED`; la matriz privada permanece con 168 `MUST` `UNRESOLVED` y 16 `DEFERRED_LAB` `EVAL_ONLY`.
- Bloqueadores: persistencia durable de resultados, verificación independiente de recibos, demostración de independencia de críticos, inventario completo de controles por documento y manejo de dependencias semánticas/globales.

## Knowledge integrity, DSR-016..032

- Las 17 reglas fueron contrastadas con los dos mecanismos principales y entradas del ledger del ZIP original; mapa por ID en [`KNOWLEDGE_INTEGRITY_DSR016_032.md`](reviews/KNOWLEDGE_INTEGRITY_DSR016_032.md).
- Prototipos independientes del corpus público: `domain/knowledge_integrity.py`, `domain/dependencies.py`, `knowledge/calibration_gate.py` y `knowledge/usage_policy.py`. Se preservó el import anterior de `knowledge/dependency_graph.py` para no romper consumidores.
- Validación del código `5f2f1ac373ca836bd89c21cd5135ae3b0abff1b2`: [CI 39090959008](https://github.com/David-std/AWF/actions/runs/39090959008), 4/4 combinaciones aprobadas, 96 pytest PASS por entorno, lint/tipado/build.
- **No cerrar por conteo de tests:** los 17 siguen `PROTOTYPED_NOT_ADJUDICATED` y el registro privado conserva los 168 `MUST` sin resolución. El modelo comprueba integridad de metadatos, no lectura/competencia, calidad de fuentes, propiedad intelectual ni fidelidad semántica independiente.

## Evidencia durable (S2, infraestructura horizontal)

| Contrato propuesto | Implementación | Evidencia requerida | Estado |
|---|---|---|---|
| Bytes locales por SHA y evento atómico | `domain/evidence.py`, `adapters/persistence/sqlite_evidence.py` | Reabrir después de reinicio; fallos de escritura sin objeto huérfano | PROTOTYPED_TESTED |
| Cadena y autenticidad relativa a checkpoint | `verify(expected_head)` | Tampering, borrado parcial y checkpoint externo divergente | PROTOTYPED_TESTED |
| No equivaler recibo con prueba académica | `external_authenticity_proven=false` en CLI; ADR-0012 | Análisis de límites y tests | STRUCTURAL_BOUNDARY |

Este corte no adjudica automáticamente ningún DSR de las 168 `MUST`; primero debe comprobarse la integración real con los controladores de revisión.

**Evidencia de CI:** commit `e168f482b153ccb172293fd6d8ddfbf91ab780a1`, [run 39096421735](https://github.com/David-std/AWF/actions/runs/39096421735), matriz 4/4 aprobada con 116 tests por trabajo; ver también [ADR-0012](adr/0012-local-evidence-ledger.md). Estado `PROTOTYPED_TESTED` se refiere a integridad y recuperación del almacén, **no** al juicio del revisor ni a las 168 reglas del corpus.

## Enlace a evidencias: recibos de revisión y conocimiento (PR #18)

| Contrato | Código | Evidencia del corte | Estado |
|---|---|---|---|
| Identificar evento completo, no solo checksum de bytes | `EvidenceStorePort.resolve_event`, `SQLiteEvidenceLedger.resolve_event` | Rechazo por run, subject, kind, hash o checkpoint divergente | PROTOTYPED_TESTED |
| Recibos de auditoría no intercambiables ni obsoletos | `record_evidenced_audit`, `verify_audit_receipts` | Slot/alcance, edición conservadora, falta de checks, fallo de persistencia | PROTOTYPED_TESTED |
| Fuentes y fragmentos enlazados a eventos privados reales | `record_evidenced_chunk`, `verify_chunk_coverage` | Inventario completo, source/run/fragment, swap y bare hash | PROTOTYPED_TESTED |
| Etapas `READ` y adjudicaciones con referencias verificables | `record_stage_claim`, `verify_progress_claims` | READ sin inventario, fuente ajena, adjudicación ausente, reinicio y replay | PROTOTYPED_TESTED |
| Independencia, autoría, comprensión y calidad científica | **Fuera del alcance del verificador local** | Exigir juez externo, revisión humana y derechos de datos | UNRESOLVED |

**Pruebas:** código `10352f0369060ba5c08d4b363f8dd2c7f878afd1`; [CI push 39098241783](https://github.com/David-std/AWF/actions/runs/39098241783) y [CI PR 39098245104](https://github.com/David-std/AWF/actions/runs/39098245104), 128 PASS × 4 entornos; PC Windows Python 3.12, 126 PASS, 1 SKIP con pruebas unitarias/integración. Estos resultados no constituyen cumplimiento de las 168 reglas históricas ni evaluación de modelo. [ADR-0013](adr/0013-evidence-bound-receipts.md).

## Persistencia coordinada de estado y evidencia (incremento S2 posterior a PR #18)

| Contrato | Implementación | Evidencia necesaria | Estado |
|---|---|---|---|
| Evidencia de auditoría y snapshot se confirman o revierten juntos | `SQLiteRevisionJournal.record_audit` sobre `SQLiteEvidenceLedger` | Trigger de error y terminación del proceso antes del COMMIT; sin evento huérfano | PROTOTYPED_TESTED_CI |
| Reintento seguro por operación | `operation_id`, huella de solicitud e índice único | Replay tras pérdida de respuesta; misma clave con otros parámetros | PROTOTYPED_TESTED_CI |
| Conflictos de dos escritores | Versiones monotónicas, `BEGIN IMMEDIATE` | Dos escritores con la misma versión; solo un commit | PROTOTYPED_TESTED_CI |
| Recuperación y comprobación del historial | Instantáneas inmutables vinculadas a `REVISION_TRANSITION` | Reinicio, alteración de bytes, trigger ausente o snapshot borrado | PROTOTYPED_TESTED_CI |
| Edición, findings, barridos y juicio académico durable | **No implementados en este corte** | Diseñar comandos independientes y verificar sus dependencias | UNRESOLVED |

No se promocionan DSR-001..032 ni otras reglas a `REVIEW_ATTESTED`. Véanse [ADR-0014](adr/0014-atomic-revision-journal.md) y [contrato de recuperación](DURABLE_REVISION_S2.md). Evidencia: código `88bd75bbfdc218225176dfcc64c4e77a93cf12a8`, [CI 39169111258](https://github.com/David-std/AWF/actions/runs/39169111258), 4/4 entornos, 139 PASS en Ubuntu y 138 PASS + 1 SKIP POSIX en Windows.

## Extensión durable de ediciones y hallazgos S2

| Contrato | Implementación | Caso adversarial | Estado |
|---|---|---|---|
| Ediciones invalidan recibos globales y scopes locales afectados | `SQLiteRevisionJournal.accept_edit` y rutina pura de fingerprints | Vecino alterado, documento obsoleto, presupuesto agotado | PROTOTYPED_TESTED_CI |
| Hallazgos permanecen abiertos hasta resolución explícita | `open_finding` y `resolve_finding` | ID duplicado, resolución inexistente, distinto run | PROTOTYPED_TESTED_CI |
| Intención, commit y estado tienen destino transaccional único | `revision_intent` y `revision_commit` schema 2 | Crash, trigger de fallo, replay, concurrencia, intención huérfana | PROTOTYPED_TESTED_CI |
| Veracidad académica, identidad/roles y sweep independiente | Fuera del corte | Exige firma, permisos, juzgado externo | UNRESOLVED |

Véanse [ADR-0015](adr/0015-durable-edit-and-finding-transitions.md) y
[guía de recuperación](DURABLE_REVISION_S2.md). **0/168 `MUST` adjudicadas**;
16 `DEFERRED_LAB` siguen solo `EVAL_ONLY`.
