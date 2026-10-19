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

## Procedimiento para implementar cada fila

Cada cambio crea relación verificable: `AWF-Rxxx → ADR → código/archivo → tests → commit → demo`. El PR registra evidencias ejecutadas, fallos y exclusiones. Nunca convertir DESIGNED en IMPLEMENTED solo porque existe un módulo vacío.

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
