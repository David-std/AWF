# AWF — transferencia de Sprint 2

Fecha de validación: 2026-10-17 (Lima). Estado: **Sprint 2 parcial; revisión técnica de reglas todavía abierta**.

## Estado exacto del repositorio

- Repositorio: `David-std/AWF`. Rama operativa local: `feat/s2-review-workbench`.
- Cadena de PRs **sin fusionar**: #10 (arquitectura) → #11 (S0) → #12 (S1) → #13 (importador S2) → [#14 (workbench S2)](https://github.com/David-std/AWF/pull/14).
- Último commit con código y tests CI verificados: `9c65157243f15f689fde325157679bf35882753c`.
- Verificaciones externas de ese commit: [PR CI 39082696174](https://github.com/David-std/AWF/actions/runs/39082696174) y [push CI 39082693013](https://github.com/David-std/AWF/actions/runs/39082693013); ambas `SUCCESS`, matriz Ubuntu/Windows × Python 3.12/3.13, **45 tests pasados por job** (Ruff, Pyright, pytest y build).
- No existen todavía editor neuronal, entrenamiento, verificador semántico de documentos, UI/API ni inferencia de producción.

## Fuente histórica local: no publicar

- ZIP existente en la carpeta Descargas del equipo autorizado: `academic_writing_suite_v3_19_1_product.zip` (mismo contenido del artefacto histórico suministrado previamente con el nombre `...(1).zip`).
- SHA-256 verificado: `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`.
- Ledger original: `academic_writing_suite/runtime/deep_spec_requirement_ledger.json`; versión 3.19.1; 184 requisitos (168 `MUST` + 16 `DEFERRED_LAB`).
- Ruta de evidencia real: 770 referencias a implementaciones históricas; 681 archivos y 89 directorios localizados dentro del ZIP, cero faltantes. Esto prueba localización, **no correcto funcionamiento ni portabilidad a AWF**.
- No subir ZIP, corpus, borradores privados, casos internos ni salida textual de las fichas a GitHub.

## Código y ejecución verificados

- `awf knowledge import`: importación desde archivo local validado por SHA; crea `.awf/knowledge/registry.json` con metadatos únicamente. Auditoría local devolvió `valid: true`, `archive_sha256_verified: true`; reimportación byte-identical.
- `awf knowledge plan-review`: prepara fichas completas por dominio sin aprobarlas. Comando validado:

```powershell
awf knowledge plan-review "RUTA_LOCAL_AL_ZIP_3_19_1.zip" --batch-size 12
```

- Carpeta generada: `.awf/knowledge/review-ccff7d4f8c67-b12/`, con **20 lotes + manifest**.
- Comprobaciones locales: 184 fichas y 184 IDs únicos; 149 con contrato histórico mecánico, 19 estructuralmente acotados y 16 laboratorios diferidos; campos de procedencia, métrica de aceptación y prueba negativa presentes para todas; contenido textual ausente del `manifest.json`; 0 propuestas marcadas como revisadas; `.awf` ignorado por Git; working tree limpio.
- Dominios: 9 dominios de `MUST` y 2 de `DEFERRED_LAB`.

## Pendientes reales y límites

1. **Revisión sustantiva de las 168 MUST:** contraste del código/test histórico, evidencia científica y aplicabilidad al diseño AWF. Estado actual: **168 UNRESOLVED**, no 168 implementadas en AWF.
2. Decidir con justificación por regla: `KEEP_AS_CODE`, `KEEP_AS_CONTEXT`, `EVAL_ONLY`, `TRAIN`, `REMOVE_FROM_ACTIVE` o `UNRESOLVED`; 16 `DEFERRED_LAB` siguen solo `EVAL_ONLY`.
3. No es suficiente marcar un campo `review_template` como aprobado. Faltan reglas de adjudicación con pruebas falsables, licencias y permisos de entrenamiento, resolución documentada de contradicciones y evaluación independiente de calidad.
4. La cuenta Git local no puede hacer `git push` al repositorio `David-std/AWF` (403: credencial `David-std2`); se publica vía **conector de GitHub**. No modificar credenciales del usuario.
5. Las PR están apiladas, no fusionadas en `main`. Su integración requiere rebasar/ajustar las bases en orden.

## Próxima unidad de trabajo

Auditar el dominio `stateful_runtime` (15 requisitos) desde los lotes privados; para cada ID recuperar la prueba histórica correspondiente, clasificar su transferibilidad a AWF y definir casos negativos nuevos. Registrar **propuestas asistidas**, no `REVIEW_ATTESTED` sin una decisión de revisión documentada. Después continuar por dominios, no por cuotas de palabras o reglas arbitrarias.

## Continuación validada: prototipo DSR-001..015

- **Código y revisión:** [PR #15](https://github.com/David-std/AWF/pull/15), apilada sobre PR #14, commit del prototipo `e6c1b199599b0e31d25002225d14776eff6c2fdc`.
- **GitHub CI del commit de código:** [pull_request 39084850246](https://github.com/David-std/AWF/actions/runs/39084850246) y [push 39084847049](https://github.com/David-std/AWF/actions/runs/39084847049), ambos SUCCESS. Cuatro trabajos: Ubuntu/Windows × Python 3.12/3.13; **61 pytest PASS por trabajo**, además de Ruff, Pyright, y build.
- **Prueba local adicional:** rama `feat/s2-stateful-audit-prototype` en `Downloads/AWF`; Python 3.12, `PYTHONPATH=src python -m pytest -q tests/unit/test_revision_audit_prototype.py`: **16 passed**; árbol de trabajo limpio.
- **Fuente histórica:** las reglas DSR-001..015 y sus rutas/pruebas se consultaron en el ZIP local, sin publicar sus fuentes. Análisis derivado en [`docs/reviews/STATEFUL_RUNTIME_DSR001_015.md`](reviews/STATEFUL_RUNTIME_DSR001_015.md); [ADR-0010](adr/0010-revision-audit-prototype.md).
- **Prototipo:** `awf.domain.revision_audit` contiene estados inmutables, tareas explícitas, hashes de dependencia, auditorías acotadas al documento, hallazgos persistentes en memoria hasta resolución, reinicio de críticos después de ediciones, rechazo de críticos repetidos, presupuestos 8/12/2 configurables y rechazo de convergencia con comprobaciones pendientes.
- **Advertencias:** la referencia a una evidencia no verifica que esta exista o sea científicamente correcta; las referencias de aislamiento no demuestran independencia real; el alcance local no certifica ausencia de dependencias semánticas; el historial no tiene persistencia durable todavía.
- **Estado formal:** las 15 reglas están **mapeadas a propuestas de migración**, ninguna recibe `REVIEW_ATTESTED` por haber pasado los tests. El resto de los 168 MUST y los 16 DEFERRED_LAB mantienen sus estados conservadores.
- **Siguiente trabajo:** primero implementar verificación externa de recibos y persistencia del estado con pruebas de recuperación/rollback, o continuar revisión de `knowledge_integrity` (17 requisitos) conforme al roadmap. No desplegar ni entrenar sobre esta base antes de resolver los riesgos.

## S2 — knowledge_integrity DSR-016..032: corte técnico validado

- Rama `feat/s2-knowledge-integrity`, [PR #16](https://github.com/David-std/AWF/pull/16), apilada sobre PR #15. **No fusionar por separado antes de PR #10–#15.**
- El análisis completo de los 17 IDs está en [`docs/reviews/KNOWLEDGE_INTEGRITY_DSR016_032.md`](reviews/KNOWLEDGE_INTEGRITY_DSR016_032.md) y la decisión técnica en [ADR-0011](adr/0011-knowledge-integrity-gates.md).
- Fuente inspeccionada sin publicarla: ZIP local `academic_writing_suite_v3_19_1_product.zip`, hash `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`. 17 requisitos, 12 de pretensión histórica mecánica y 5 estructurales acotados.
- Brecha legacy identificada: `knowledge_coverage.make_receipt()` construye cobertura de lecturas desde el manifiesto en lugar de registrar observación real de fragmentos. Esto puede representar un falso PASS epistémico.
- Código nuevo: `src/awf/domain/knowledge_integrity.py`, `src/awf/domain/dependencies.py`, `src/awf/knowledge/calibration_gate.py`, `src/awf/knowledge/usage_policy.py`; se mantuvo compatibilidad del import `awf.knowledge.dependency_graph` como reexport.
- Pruebas: `tests/unit/test_knowledge_integrity.py`, `test_knowledge_calibration_gate.py`, `test_knowledge_usage_policy.py` (35 casos del nuevo bloque después de segunda pasada).
- Commit de código `5f2f1ac373ca836bd89c21cd5135ae3b0abff1b2`; [CI PR](https://github.com/David-std/AWF/actions/runs/39090959008) y [CI push](https://github.com/David-std/AWF/actions/runs/39090955229) aprobadas, **4/4 jobs, 96 tests cada uno**, Ruff/Pyright (0 errores)/build.
- **Estado del ledger privado sin cambio:** 168 MUST `UNRESOLVED`, 16 `DEFERRED_LAB` `EVAL_ONLY`. Los 17 tienen propuestas de migración pero ninguno recibe `REVIEW_ATTESTED` automáticamente.
- **Limitaciones:** referencias `evidence_ref` y dictámenes de calibración aún son declarativos, sin firmas ni verificadores independientes; no hay demostración de verdadera lectura/comprensión, veracidad científica, licencias, aislamiento fuerte del holdout ni aprendizaje neuronal.
- **Siguiente hito:** almacenamiento de evidencias inmutable y comprobación real del registro de fragmentos, identificación de corpus autorizado y revisión científica de calibración antes de conectar esta puerta al editor neuronal.

## S2 — evidencia durable (primer corte probado)

- Nueva rama `feat/s2-evidence-ledger`, apilada sobre PR #16, fuente de trabajo `src/awf/domain/evidence.py` y adaptador `src/awf/adapters/persistence/sqlite_evidence.py`.
- Puerto `EvidenceStorePort` y CLI `awf evidence append/verify` para registros sintéticos privados; original y ZIP histórico no enviados.
- [ADR-0012](adr/0012-local-evidence-ledger.md) documenta por qué usar SQLite ahora es distinto del caso exportador JSON de ADR-0008.
- Garantía: atomicidad y hashes comprobados; **no firmas, identidad externa ni pruebas de conocimiento real**. Las etapas anteriores aún no consumen automáticamente el ledger.
- **Implementación verificada:** [PR #17](https://github.com/David-std/AWF/pull/17), commit de código `e168f482b153ccb172293fd6d8ddfbf91ab780a1`; CI [push run 39096421735](https://github.com/David-std/AWF/actions/runs/39096421735) y [PR run 39096425185](https://github.com/David-std/AWF/actions/runs/39096425185) con matriz Linux/Windows y Python 3.12/3.13, **116 tests aprobados por trabajo**, Pyright 0 errores, Ruff y build aprobados.
- **Pruebas locales en la versión final:** ASUS ROG STRIX, Python 3.12, `python -m pytest -q tests/unit tests/integration`: **114 PASS, 1 SKIP** (permisos POSIX no aplicables a Windows). `python -m pytest -q` con el `python` por defecto (Python 3.14) no pudo recolectar las pruebas de propiedades porque falta `hypothesis` en ese intérprete. La CI sí instaló dependencias y ejecutó los 116 tests completos por cada entorno.
- **Smoke local de CLI:** `awf evidence append` con texto sintético generó un evento y `awf evidence verify` confirmó 1 evento y 1 objeto. `claims_independently_verified=false` y `external_authenticity_proven=false`; `.awf/evidence/smoke.sqlite` ignorado por Git, árbol limpio. No se usó el ZIP histórico.
- **Alcance:** la evidencia guardada queda vinculada a un hash y evento en la base local. **No se conecta automáticamente** con la comprobación semántica de `revision_audit` ni la calibración de `knowledge_integrity`; nadie debe interpretarlo como independencia externa o conocimiento demostrado.
- **Siguiente fase:** integrar un verificador externo de evidencias/identidad y recibos tipados del controlador, más ensayo de recuperación desde backup con checkpoint separado; ningún dato histórico privado se sube al repositorio.

## S2 — binding de recibos a evidencias (prototipo validado)

- Rama `feat/s2-evidence-binding`, derivada de PR #17. Nuevas funciones `application/commands/bind_evidence.py` y `EvidenceStorePort.resolve_event` con adaptador SQLite. Contratos descritos en [ADR-0013](adr/0013-evidence-bound-receipts.md).
- Los resultados son verificaciones locales de integridad; `independent_adjudication_proven=False` de forma explícita. Ninguna de las 168 MUST históricas queda adjudicada por esta prueba.
- Tests sintéticos de replay/swap/subject/run/stage, lectura de bytes, recibos locales, reinicio y rollback en `tests/integration/test_evidence_binding.py`.
- **Corte de código verificado:** commit `10352f0369060ba5c08d4b363f8dd2c7f878afd1`, [PR #18](https://github.com/David-std/AWF/pull/18), [CI push 39098241783](https://github.com/David-std/AWF/actions/runs/39098241783) y [CI PR 39098245104](https://github.com/David-std/AWF/actions/runs/39098245104), ambos SUCCESS. Matriz Ubuntu/Windows × Python 3.12/3.13, 4/4 aprobada, **128 tests por trabajo**, lint/formato/tipado (Pyright 0 errores)/build.
- **Prueba local en Windows:** rama `feat/s2-evidence-binding` sincronizada al código del commit indicado; Python 3.12: `pytest -q tests/unit tests/integration` dio **126 PASS y 1 SKIP** (permisos POSIX no aplicables a Windows). Git limpio al terminar pruebas.
- **Garantías acotadas:** el evento, tipo, sesión, sujeto y bytes se vuelven a contrastar. `local_integrity_passed` no es juicio semántico; `independent_adjudication_proven` permanece `False`. Una declaración local de un crítico no constituye evaluación independiente.
- **Deuda prioritaria:** permisos y control de identidad de evaluadores, checkpoints externos contra truncación, coordinación durable entre transiciones de estado y append al ledger, aislamiento de holdouts, rendimiento de relectura O(n) y pruebas de recuperación ante crash real.
- **Estado formal:** 168 `MUST` sin adjudicación y 16 `DEFERRED_LAB` solo evaluación. PR #18 apilada sobre #17 y anteriores, todavía **no fusionada a main**. El ZIP AWS 3.19.1 y corpus históricos continúan únicamente en local.

## S2 — siguiente corte: journal coordinado de revisión (incremento en validación)

- Base comprobada: PR #18 `feat/s2-evidence-binding`, HEAD `7600f6fcb18a66e9ffbd25aa026cd1363244877e`, CI `39098469988` exitosa. Se conserva la cadena de PR sin fusionar.
- Cambio: `SQLiteRevisionJournal` añade snapshots append-only a la misma base de evidencia. Los eventos `AUDIT_RECEIPT`, `REVISION_TRANSITION` y el estado de revisión se confirman mediante un solo `COMMIT`; una clave idempotente y versión esperada controlan replay/concurrencia. Se verifica el historial al reabrir.
- Superficies nuevas: `adapters/persistence/sqlite_revision.py`, `revision_codec.py`, `RevisionJournalPort`, `PersistedRevision`, `tests/integration/test_durable_revision.py`, [ADR-0014](adr/0014-atomic-revision-journal.md), [contrato S2](DURABLE_REVISION_S2.md).
- Implementación publicada: [PR #19](https://github.com/David-std/AWF/pull/19), rama `feat/s2-atomic-revision-journal`, base exacta PR #18 `7600f6fcb18a66e9ffbd25aa026cd1363244877e`; commit de código y documentos iniciales `88bd75bbfdc218225176dfcc64c4e77a93cf12a8`.
- Validación en scratch Linux Python 3.12: **139 pytest PASS** (128 anteriores + 11 de crash, rollback, idempotencia, integridad y concurrencia). `uv lock --check`, Ruff check/format, Pyright 0 errores/advertencias, `uv build` y diff-check, todos PASS.
- Validación del commit `88bd75b` en GitHub Actions: [workflow 39169111258](https://github.com/David-std/AWF/actions/runs/39169111258) **SUCCESS**, 4/4 jobs: Ubuntu Python 3.12/3.13 **139 PASS** cada uno; Windows Python 3.12/3.13 **138 PASS y 1 SKIP** (prueba de permisos POSIX). Ruff, Pyright y build PASS en todos. No se repitieron pruebas en el ASUS ROG STRIX durante este corte; CI Windows sí comprobó compatibilidad multiplataforma.
- **Alcance limitado:** solamente `START` y `AUDIT` son transiciones durables. No se ha migrado `accept_edit`, findings, barridos de críticos ni etapas de conocimiento a este journal; el helper previo `record_evidenced_audit` conserva semántica en memoria. No existe autorización de `CONVERGED` por integridad SQLite.
- Pendientes después de estabilizar este corte: autoridad/roles de evaluadores y checkpoints externos; durabilidad de otras transiciones; backup/restore y medición O(n); análisis sustantivo de las 136 reglas `MUST` no examinadas. **0 de 168 `MUST` adjudicadas**; las 16 lab-only continúan `EVAL_ONLY`; ZIP histórico local.
- **Siguiente paso mínimo:** revisar PR #19 sin fusionarla aisladamente; diseñar la persistencia de transiciones adicionales con pruebas de invalidez/rollback, o separar el siguiente incremento de identidad de evaluadores y anclaje independiente. Mantener abierto S2.
