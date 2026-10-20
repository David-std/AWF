# AWF — transferencia de Sprint 2

## Continuación S2 — lectura de eventos por snapshot verificado (tras PR #24)

- **Base confirmada:** `develop` tras PR #24, merge commit `e32e0ea99e76640133d328548214f0efbae63cfc`; `main` sigue en `a902135b80e96eea17ebb9c229eed065077e809d`. PR #24 cerrada y fusionada con código `dae66ed7057353d521dfab4077b26b9a4a333a86`, [CI 39203570452](https://github.com/David-std/AWF/actions/runs/39203570452) 4/4, 279 Linux y 277 Windows ASUS +2 SKIP, sin modificar worktree original Windows. Incremento actual: [PR #25](https://github.com/David-std/AWF/pull/25), rama `feat/s2-ledger-scaling`, **pendiente de fusionar hasta verificar el SHA final**.
- **Riesgo:** cada `resolve_event` audita O(n) objetos y eventos; en un gate con `m` fragmentos, `m` auditorías repetidas elevan el trabajo aproximadamente a `O(n×m)`. Nunca confiar en un head cacheado entre llamadas para optimizarlo.
- **Solución:** `VerifiedEvidenceReaderPort` y `SQLiteEvidenceLedger.verified_read` auditan todos los objetos y DDL en una única transacción SQLite; resuelven luego digest+metadatos+bytes por recibo sin mezclar heads ante append concurrente. `verify_chunk_coverage`, `verify_audit_receipts` y `verify_progress_claims` comparten contexto, incluso READ anidado. No se relajan las puertas ni se cambia el `resolve_event` público.
- **Primer corte Linux local:** 286 pytest PASS Python 3.12 (7 pruebas nuevas de conteo real de auditorías, lectores concurrentes, head antiguo, estado incompleto y esquema corrupto), Ruff y Pyright 0 errores tras formato. Benchmark sintético Linux CPython 3.12.14, mediana de tres repeticiones: 16 eventos 9,199→0,665 ms (13,84×), 64 eventos 78,185→1,762 ms (44,37×), 128 eventos 249,342→3,328 ms (74,92×), 256 eventos 799,826→5,737 ms (139,42×). Es evidencia local, no SLO ni comparación de hardware. [ADR-0019](adr/0019-verified-evidence-read-snapshots.md), [guía y script reproducible](EVIDENCE_READ_SCALING_S2.md).
- **Evidencia del primer commit publicado:** `bc5d0fdb1d0ff40e24a514562fb9dd8485d75939`. [CI 39347741248](https://github.com/David-std/AWF/actions/runs/39347741248): 4/4 Linux/Windows × Python 3.12/3.13, Ruff/Pyright/pytest/build PASS. ASUS ROG STRIX Windows Python 3.12.10, worktree aislado al SHA exacto: **284 PASS y 2 SKIP** (ZIP abierto/permiso POSIX); rama original `feat/s2-evidence-binding` limpia. Benchmark ASUS con 16/64/128/256 eventos: mejoras sintéticas 15,15× / 49,76× / 35,76× / 153,23×. El último ajuste es **documental** para preservar estas mediciones: repetir gates sobre el SHA final antes de merge. No usar ZIP histórico ni publicar datos privados. Riesgos S2 aún abiertos: barridos de críticos durables, real custodia/rotación de checkpoints, replay a escala, 136 MUST sin propuesta sustantiva y adjudicación humana de las 168 MUST. **0/168 REVIEW_ATTESTED**.

**Actualización vigente: 2026-10-20 (UTC).** Las siguientes secciones documentan cortes anteriores sin alterar su trazabilidad.

## Continuación S2 — recuperación SQLite ligada a checkpoint firmado (tras PR #23)

- **Base exacta:** `develop` commit de fusión PR #23 `484b911b1b754909786510273cee6218825258d9`, `main` sin tocar `a902135b80e96eea17ebb9c229eed065077e809d`. [PR #24](https://github.com/David-std/AWF/pull/24), rama `feat/s2-verified-sqlite-backups`, sin fusionar hasta validar el último SHA.
- **Contratos:** `SnapshotReceipt` DTO, `SnapshotWriterPort`, `create_verified_snapshot` exigen firma/política/último hash de checkpoint por testigo externo y `require_current_head=True`; el adaptador usa `sqlite3.backup`, audita snapshot completo y publica solo a un destino nuevo con hardlink atómico (nunca sobrescribe datos preexistentes).
- **Protección adicional:** `SQLiteRevisionJournal.verify_all_revisions` valida esquema/triggers, evidencia y replay completo de *cada* revisión en un snapshot único; el mero hecho de que los eventos SHA sean válidos no permite restaurar un `RevisionState` adulterado.
- **Primer corte publicado `f0d4a73bac3bcf6c7ed35506595e55383b1c4fec`:** 278 pruebas PASS Python 3.12 Linux, Ruff/Pyright 0 errores, `uv lock --check`, `uv build --offline` y 4/4 trabajos GitHub Actions correctos ([run 39203237173](https://github.com/David-std/AWF/actions/runs/39203237173)); equipo Windows autorizado, worktree aislado exacto, 276 PASS y 2 SKIP por bloqueo ZIP y prueba de permisos POSIX. Tras la validación se añadió una prueba adicional contra creación concurrente del destino justo al publicar: repetir gates y reproducción Windows sobre el SHA final antes del merge. Pruebas adversariales sintéticas sin ZIP histórico. [ADR-0018](adr/0018-wal-aware-signed-backup-recovery.md), [guía de snapshot](VERIFIED_SNAPSHOTS_S2.md).
- **Punto S2 pendiente:** permisos/custodia reales de terceros, política de rotación de claves, cutover y RPO/RTO, barridos críticos durables, perfilado del replay para muchos documentos y adjudicación sustantiva de 168 MUST. Ningún resultado de copia autentica verdad académica; `0/168 REVIEW_ATTESTED` permanece inalterado.

**Actualización vigente: 2026-10-19 (UTC).** La bitácora anterior permanece por trazabilidad histórica; los SHA y resultados de esta sección prevalecen al continuar.

## Continuación de S2: checkpoint de ledger firmado (incremento tras PR #22)

- **Base exacta:** `develop` `6fc0f5fde290f4febe4acae1689f387d5d22a02c` (PR #22 fusionada); `main` conservada `a902135b80e96eea17ebb9c229eed065077e809d`. Rama propuesta: `feat/s2-signed-checkpoints`. No fusionar ni reescribir `main`.
- **Contrato nuevo:** `CheckpointClaim`/`SignedLedgerCheckpoint` y `CheckpointTrustPolicy` de custodios, independientes de roles científicos. `verify_signed_checkpoint` exige SHA-256 externo de último checkpoint y política; historia completa firmada, ascendente y con prefijos comprobados; `SQLiteEvidenceLedger.verify_anchors` audita en una sola transacción para evitar mezclar snapshots bajo concurrencia.
- **CLI:** `awf evidence checkpoint-propose` genera solo una propuesta para firmante fuera de AWF. `checkpoint-verify` valida firma, contexto, revocación, historia y bytes del SQLite; `external_custody_proven=false` explícito. Ninguna clave privada se guarda ni se envía. Véanse [ADR-0017](adr/0017-externally-signed-ledger-checkpoints.md) y [guía operativa](SIGNED_CHECKPOINTS_S2.md).
- **Primera validación publicada:** [PR #23](https://github.com/David-std/AWF/pull/23), código `c4355719d86c38049ff7a3a022e28bd7efbb4fb0`, [GitHub Actions 39196974344](https://github.com/David-std/AWF/actions/runs/39196974344), **4/4 jobs SUCCESS** Ubuntu/Windows × Python 3.12/3.13 con pytest, Ruff, Pyright, lock y build. Linux Python 3.12: **260 PASS**, incluidas 18 iteraciones Hypothesis; Windows Python 3.12 en ASUS ROG STRIX: **258 PASS, 2 SKIP** (ZIP abierto bloqueado por Windows y permisos POSIX), exit code 0, worktree detached del SHA exacto; rama original `feat/s2-evidence-binding` y worktree original sin cambios. Se ajustó luego la lectura de DDL al interior de la misma transacción que la auditoría; **requiere CI/Windows del nuevo SHA antes de merge**.
- **Pendiente S2:** custodia externa institucional de últimos hashes y claves, política de rotación histórica/versiones, copias SQLite coherentes con backup/restore y pruebas de fallo/recuperación, barridos críticos durables y rendimiento por lotes, más adjudicación académica real. **0/168 MUST**, 16 lab-only `EVAL_ONLY`.

**Actualización vigente: 2026-10-19 (UTC).** La bitácora de ramas/comprobaciones que sigue documenta estados anteriores, no sustituye la base exacta de este incremento.

## Continuación de S2: atestaciones de evaluador (incremento posterior a #21)

- **Punto de partida:** `develop` en `6d489f4640fd3e7bca636b790cf006997624e1f4` (PR #21 fusionada), con `main` conservada en `a902135b80e96eea17ebb9c229eed065077e809d`. Este incremento debe revisarse y fusionarse mediante PR a `develop`, nunca como modificación directa de `main`.
- **Contrato añadido:** `domain/reviewer_auth.py` establece declaración canónica, roles y permisos por evento/run/sujeto; `application/commands/authorize_review.py` verifica permisos y recibos con un puerto criptográfico; `adapters/security/ed25519_reviewer.py` implementa Ed25519. `awf evidence attest` y `attest-verify` admiten/verifican declaraciones firmadas con una política cuya huella debe proceder de fuera del almacén. `EvidenceKind.REVIEW_ATTESTATION` es aditivo.
- **Calidad local comprobada:** 220 pruebas completas en Linux Python 3.12 (incluye nuevos casos de firma alterada, cambio de evento/contexto, grant revocado/vencido, inventario de auditorías, READ y etapas de conocimiento, CLI), Ruff, Pyright, `uv lock --check` y `uv build` sin errores. CI multiplataforma de este incremento queda como condición de fusión, no se infiere de la validación local.
- **Decisión y guía:** [ADR-0016](adr/0016-signed-reviewer-authorization.md) y [autorización S2](REVIEWER_AUTH_S2.md). Las claves privadas no se almacenan ni publican. Una clave autorizada no prueba identidad civil, independencia entre críticos, calidad científica ni hora externa confiable. `independent_adjudication_proven=False` se conserva.
- **Cierre pendiente de Sprint 2:** checkpoint/firma externa del ledger, custodia y revocación/rotación institucional de claves, durabilidad de barridos críticos, pruebas de backup/restore, benchmark de verificación por lotes y adjudicación formal del corpus. Estado formal **0/168 `MUST`**, 16 lab-only `EVAL_ONLY`.

**Actualización vigente: 2026-10-19 (UTC).** Sprint 2 permanece parcial. Las secciones fechadas más abajo son una bitácora histórica; sus indicaciones antiguas sobre PR «sin fusionar», ramas operativas y siguientes pasos **han quedado sustituidas** por este apartado.

## Estado vigente — integración revisada en `develop`

- `main` se conserva en `a902135b80e96eea17ebb9c229eed065077e809d`. Se creó `develop` desde ese commit y se fusionaron secuencialmente, por merge commit, las once PR [#10](https://github.com/David-std/AWF/pull/10) a [#20](https://github.com/David-std/AWF/pull/20). Todas figuran `closed/merged`, con base final `develop`; ninguna se fusionó a `main`.
- HEAD exacto de `develop`: `26a937ebf647fd438ed703ac0e3a9c94aabc09c7`, cierre de PR #20. La integración conservó sin pérdida las correcciones de cada revisión y resolvió explícitamente conflictos en las PR #14, #17 y #20. Los contratos rectores son `AGENTS.md`, [arquitectura 0.1](architecture/ARCHITECTURE_SPEC_0_1.md), [decision lock](architecture/DECISIONS_LOCK.yaml) y ADR-0006 a ADR-0015.
- Resultado final: **196 pytest PASS** en Linux Python 3.12 para el árbol integrado, Ruff lint/formato y Pyright sin errores. PR #20, commit `cdd8de2304fd24ced17490aaa815a84e78e10307`, [Actions 39186482215](https://github.com/David-std/AWF/actions/runs/39186482215): **4/4 jobs SUCCESS** en Ubuntu/Windows con Python 3.12/3.13. El SHA del árbol integrado se contrastó antes de publicar la resolución de conflictos.
- Validación adicional con Desktop Commander en el equipo autorizado ASUS ROG STRIX, en worktree aislado de `develop` al mismo SHA: **194 PASS, 2 SKIP** en Windows Python 3.12; una omisión requiere POSIX y la otra es una restricción documentada de archivos ZIP abiertos en Windows. La rama de trabajo preexistente `feat/s2-evidence-binding` quedó intacta. `hypothesis==6.142.4` se instaló solo en `.audit_test_deps` del worktree temporal.
- Garantías revisadas: exportes privados atómicos de DocumentIR y workbench, decisiones históricas `REVIEW_PROPOSED` separadas de `REVIEW_ATTESTED`, rechazo de entradas/schemas manipulados, preservación conservadora de auditorías/fragmentos, cadena SQLite comprobada contra triggers falsificados, contexto de ejecución coherente y replay de `START`, `AUDIT`, `EDIT`, `FINDING_OPEN`, `FINDING_RESOLVE` con commit coordinado y secuencia causal de eventos.
- **Estado del corpus inalterado:** 184 entradas (168 `MUST`, 16 `DEFERRED_LAB`), **0/168 formalmente adjudicadas**. Existen análisis preliminares para 32; faltan 136 análisis sustantivos. Las 16 lab-only siguen `EVAL_ONLY`; ni pruebas verdes ni recibos SQLite promueven reglas a `REVIEW_ATTESTED`.
- **Siguientes prioridades S2:** (1) identidad, roles y autorización verificables de evaluadores; (2) checkpoint firmado o custodiado fuera de SQLite, rotación y restauración de backups; (3) transacciones durables para barridos críticos/iteraciones externas si se pretende automatizar convergencia; (4) medición y optimización de la verificación de muchos fragmentos; (5) adjudicación de reglas con fuente, permisos, falsadores y revisión humana independiente. Mantener cerrada la puerta a entrenamiento y a declaraciones de validez académica hasta resolver estas condiciones.

## Registro histórico — información anterior a la integración

Fecha del primer corte: 2026-10-17 (Lima). Estado histórico: **Sprint 2 parcial; revisión técnica de reglas todavía abierta**.

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

## S2 — continuación: edición y findings durables (PR incremental)

- Base exacta PR #19 `feat/s2-atomic-revision-journal`, HEAD
  `69768493f91aef4fa9d8ad5b6bddc9c8123bbfa3`, abierta sobre #18;
  la cadena de PRs #10–#19 continúa sin fusionar.
- [PR #20](https://github.com/David-std/AWF/pull/20), rama
  `feat/s2-durable-edit-findings`, commit de código inicial
  `139247cddf2e5365569bac66528d8c1c1dc49c6b`. Se amplía el journal
  con transiciones de edición y hallazgos y replay de esquema 2 sin migración
  destructiva del esquema 1. Intención, commit y snapshot son atómicos.
- `tests/integration/test_revision_transitions.py` usa solo documentos
  sintéticos. Verificación scratch Linux Python 3.12: **154 pytest PASS**,
  Ruff check/format PASS, Pyright 0 errores, `uv lock --check`, `uv build`
  y `git diff --check` PASS.
- GitHub Actions de `53fdb7f2bf73d5cc9bf4562f3504a48ecf0b4e4d`:
  [run 39174723908](https://github.com/David-std/AWF/actions/runs/39174723908)
  **SUCCESS (4/4)**. Ubuntu Python 3.12/3.13: 154 PASS cada uno; Windows
  Python 3.12/3.13: **153 PASS, 1 SKIP** cada uno (prueba de permisos POSIX).
  Ruff, Pyright, lockfile, CLI smoke y build aprobados en los cuatro entornos.
  No se ejecutó una prueba adicional en la PC ASUS durante este corte.
- [ADR-0015](adr/0015-durable-edit-and-finding-transitions.md) y
  [guía durable](DURABLE_REVISION_S2.md) precisan los límites: evidencia
  registrada no equivale a autorización humana, veracidad académica ni
  autenticidad de `DocumentIR` contra los bytes originales.
- Faltan comandos durables de sweep/iteración externa, verificador independiente
  de roles/identidad, checkpoint externo, medición de rendimiento, backup y
  la adjudicación científica de los 136 MUST restantes.
- **Estado formal inalterado:** 0 de 168 MUST adjudicadas; 16 DEFERRED_LAB
  solo EVAL_ONLY. El ZIP AWS histórico sigue exclusivamente en el equipo
  autorizado, sin publicar.
