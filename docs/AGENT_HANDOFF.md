# AWF — transferencia de Sprint 2

## S2 PR #35 — rights evidence, implementation tested, legal authority deferred

- Code SHA `cd6c2c885efd1f54da5b9804a41c2a3cc314a5f2`: [push CI run 39540058673](https://github.com/David-std/AWF/actions/runs/39540058673) SUCCESS, 4/4 Ubuntu/Windows × Python 3.12/3.13. Ubuntu Python 3.12 had **440 pytest PASS**, Pyright **0 errors/0 warnings**, Ruff and build pass. The documentation follow-up must be checked at its exact SHA separately.
- Draft [PR #35](https://github.com/David-std/AWF/pull/35) targets `feat/s2-independent-scientific-assessments`. This engineering test is NOT an independent legal or scientific adjudication.

## S2 candidate PR #35 — rights evidence, conditional and independently verified

- Branch `feat/s2-source-rights-provenance`, **based on draft PR #34 exact HEAD
  `1c8f729e75e9fdcb1a6e9054854baabdad8f8f24`**. PR #32, #33 and #34 remain
  in order; do not retarget to main or develop without coordinated stack review.
- Implements `domain/source_rights.py` and `application/commands/source_rights.py`.
  Exact source + segment bytes, a canonical externally pinned rights inventory, per-act
  scope, changes/revocation/expiry, evidence hash and an **independent rights verifier**
  are necessary for positive permissions. No rights-issuer adapter exists; ordinary
  use returns UNKNOWN. Denials and conflicting overlapping grants block.
- `TRAIN_ALLOWED` is *only* a conditional rights-scope conclusion when an externally
  trusted authority is injected, and `training_authorized` remains FALSE. No right
  arises from SPDX names, a CC deed, DOI, public repository or user possession alone.
- No private source files, licences, grants, reviewer notes, keys or AWS ZIP are added
  to git/CI. Uses test-only simulated byte strings and an in-memory fake verifier.
- Remaining: real independent rights authority, verifiable legal chain of title, policy
  revocation infrastructure, separate adjudication of scientific disagreements and
  full review of 168 MUST. No signature role is added in this slice.
- CI evidence for **exact final SHA** must be appended after the latest CI completes;
  never infer PASS from older PRs. See ADR-0028 and SOURCE_RIGHTS_GATE_S2.

## Earlier authoritative handoff and PR #34 baseline

## Authoritative continuation after the PR #34 final CI (2026-10-20; verify again before changes)

- **Repository state verified:** `develop=6888a8f44a3342c61e0d31dc93374ef44a21c174`, `main=a902135b80e96eea17ebb9c229eed065077e809d`. No merge of draft [PR #32](https://github.com/David-std/AWF/pull/32), [PR #33](https://github.com/David-std/AWF/pull/33), or [PR #34](https://github.com/David-std/AWF/pull/34). PR stack: develop → #32 (head `e6846eff`) → #33 (head `7fcd4061`) → #34 (head `34b192a32efd0841a6149d93493d3aa1b19147b3`).
- **Final SHA verified:** [push 39531777710](https://github.com/David-std/AWF/actions/runs/39531777710) and [PR 39531782917](https://github.com/David-std/AWF/actions/runs/39531782917), both 4/4 SUCCESS, Ubuntu/Windows × Python 3.12/3.13. Ubuntu 3.12 420 PASS, Pyright 0 errors/0 warnings, Ruff and build PASS. [PR #34 closure comment](https://github.com/David-std/AWF/pull/34#issuecomment-6306358457) already preserves the completed work and its limits.
- **Current increment:** `SCIENTIFIC_REVIEWER`/ `SCIENTIFIC_RULE_ASSESSMENT`, private source-bound canonical assessment, Ed25519 verification against prior `KNOWLEDGE_REVIEWER` proposal and distinct credentials, external SHA-pinned policy/head, source/run/rule binding, revocation and chronology. [ADR-0027](adr/0027-independent-scientific-assessment-receipts.md), [usage](INDEPENDENT_SCIENTIFIC_ASSESSMENTS_S2.md), AWF-R036, `application/commands/scientific_assessments.py` and `tests/integration/test_independent_scientific_assessments.py`.
- **Non-goals:** The result authenticates scoped records, **not** a human person, independence in the social/scientific sense, scientific truth, licensing, or authorization to train. **168/168 MUST remain UNRESOLVED, 16 DEFERRED_LAB EVAL_ONLY, 0 REVIEW_ATTESTED**, Sprint 2 OPEN. No untrusted data moved into Git/CI. ASUS used only for isolated formatter scratch.
- **Next separately scoped work:** source-specific rights provenance and independent scientific adjudication protocol / disagreement resolution, each with explicit authority, adversarial tests, and a no-training default. No new signature implementation unless shown necessary. Preserve the PR stack; do not force push, rewrite/merge historic owner checkout or alter `main`.
- **Historical caveat:** all references below to PR #30/#31 awaiting merge or PR #32/#33/#34 awaiting CI are past-time entries. This section supersedes them as of this verified cut. The next agent must re-check current GitHub SHA/PR states before acting.


## New provisional incremental branch after PR #33 — ADR-0027

- Draft work planned: `feat/s2-independent-scientific-assessments` stacked on still-draft PR #33 (`7fcd406189762e62ad2186f43f967b1dd4ec2661`). PR #33 stacks on #32; neither has merged. Do not interpret these commits as changes to `develop` or `main`.
- New `SCIENTIFIC_REVIEWER` role and `SCIENTIFIC_RULE_ASSESSMENT` event, with application-only separate actor-credential verification `scientific_assessments.py`. It reuses original signed-proposal validation and exact externally SHA-pinned ledger head. Actual method/evidence/limitations notes are local SQLite evidence bytes, not public text. The assessment opinion `SUPPORT|CONTEST|INCONCLUSIVE` is **not scholarly adjudication**.
- [ADR-0027](adr/0027-independent-scientific-assessment-receipts.md) and [guide](INDEPENDENT_SCIENTIFIC_ASSESSMENTS_S2.md); AWF-R036 candidate. No added CLI option yet; rights and independent real-human review remain deferred. No `REVIEW_ATTESTED`, no TRAIN, S2 remains OPEN, 0/168 MUST.
- **Verified implementation SHA:** `86f71659a47df3ce75b0f4845aa5d8f6a0b86d46`. [Push CI 39531181324](https://github.com/David-std/AWF/actions/runs/39531181324) and [PR CI 39531184711](https://github.com/David-std/AWF/actions/runs/39531184711) both **4/4 SUCCESS** across Ubuntu/Windows × Python 3.12/3.13. Ubuntu 3.12: **420 PASS**; Windows 3.13: **418 PASS, 2 SKIP**. Ruff 0.14.0, Pyright **0 errors/0 warnings** and build passed. This later documentation-only commit also needs CI on its exact SHA before the PR is merge-ready. **No physical ASUS full-suite execution**, only isolated scratch formatting; historic owner checkout untouched. PR #34 remains draft/unmerged.



## Newest provisional increment: stacked PR #33 (2026-10-20)

- Branch `feat/s2-signed-knowledge-review-proposals`, **draft [PR #33](https://github.com/David-std/AWF/pull/33)** targeting the *still-draft* `feat/s2-verify-dossier-evidence-links` of PR #32. Never merge or retarget directly to `develop` before the parent is independently reviewed and integrated.
- New `KNOWLEDGE_REVIEWER` role and `KNOWLEDGE_REVIEW_PROPOSAL` event; `application/commands/authorize_dossiers.py` authenticates the full private template digest, canonical ZIP/rule ID and support receipts with Ed25519 grants and fresh policy/head in one verified snapshot. CLI exposes optional private inventory/policy flags, with default PR #31/#32 behavior unchanged.
- [ADR-0026](adr/0026-signed-knowledge-review-proposals.md), [guide](SIGNED_KNOWLEDGE_PROPOSALS_S2.md), AWF-R035 and synthetic adversarial/CLI tests. No corpus data, private reviewer notes or secrets committed.
- **Epistemic status:** cryptographic permission to sign a proposal snapshot is NOT an authenticated person, reviewer independence, research correctness, a legal rights grant or `REVIEW_ATTESTED`. S2 **OPEN**, 168 MUST unresolved, 16 lab EVAL_ONLY; no neural training.
- **Verified PR #33 code+docs SHA** `994456d3d423f2a9bc59fbf560bbbe3a2c3d0542`: [push CI 39527598797](https://github.com/David-std/AWF/actions/runs/39527598797) and [PR CI 39527604600](https://github.com/David-std/AWF/actions/runs/39527604600), **4/4 SUCCESS** each, Ubuntu/Windows × Python 3.12/3.13. Ubuntu 3.12: **409 PASS**; Windows 3.13: **407 PASS + 2 SKIP**; locked Ruff 0.14 format/lint, Pyright **0 errors/0 warnings**, package build passed. This note itself is a later documentation-only commit and must receive separate CI confirmation. ASUS scratch was used for formatting only, not claimed as a full physical Windows test.



## Current authoritative status after PR #31 (2026-10-20)

- **Verified source cut:** `develop` at `6888a8f44a3342c61e0d31dc93374ef44a21c174`, PR #31 merged. `main` remains `a902135b80e96eea17ebb9c229eed065077e809d`. Older PR #30 conditional-merge notes below are historical, not operational.
- **Sprint:** S2 OPEN; 168 MUST `UNRESOLVED`, 16 DEFERRED_LAB `EVAL_ONLY`, 0 adjudicated. No neural training. Latest successful PR #31 CI: [39510767394](https://github.com/David-std/AWF/actions/runs/39510767394) (4/4 jobs).
- **Next active change:** [draft PR #32](https://github.com/David-std/AWF/pull/32), source-bound private dossier evidence references ([ADR-0025](adr/0025-dossier-evidence-links.md)). **Code commit** `5f10015e0f30fa4d4b81acdfbba674bfd527726f` passed [push CI 39523923437](https://github.com/David-std/AWF/actions/runs/39523923437) and [PR CI 39523930876](https://github.com/David-std/AWF/actions/runs/39523930876), each 4/4 Windows/Linux × Python 3.12/3.13; Ubuntu 3.12 **383 PASS**, Windows 3.13 **381 PASS + 2 SKIP**, Pyright 0 errors, Ruff and build passed. **Draft, not merged**, and the final documentation commit needs its own CI. No physical Windows reproduction was performed; the historical owner checkout was not modified. Event metadata linkage only; external identity, independence, licensing and `REVIEW_ATTESTED` remain open. See [evidence-link guide](DOSSIER_EVIDENCE_LINKS_S2.md).
- **Source custody:** AWS 3.19.1 ZIP stays private; the code and tests use synthetic records only.
- **Tooling:** GitHub connector is authoritative for remote refs; the physical Windows checkout held a historical branch at this cut and HTTPS fetch failed. Do not reset the owner's tree. Run CI on final PR commit; record physical PC tests only if genuinely executed.



## Incremento verificado en PR — autorización firmada de barridos críticos (PR #30)

- **Base remota verificada:** PR #29 fusionada a `develop` en `2275d0018f17de8559a72d8c6cae4e248a1627c0`; `main` sigue en `a902135b80e96eea17ebb9c229eed065077e809d`. Trabajo aislado en Windows, sin modificar checkout original.
- **Contrato:** `ReviewerRole.CRITIC` firma CRITIC_OBSERVATION exclusivamente. `application/commands/authorize_critics.py` recupera CLEAN_SWEEP, exige convergencia e inventario completo, vincula firma con la observación del intento y actor, y usa un snapshot verificado único sobre head externo. Política Ed25519 SHA-pinned, permisos/caducidad/revocación; un head obsoleto falla.
- **Archivos:** [ADR-0023](adr/0023-signed-critic-sweep-authorization.md), [contrato](REVIEWER_AUTH_S2.md), [AWF-R032](REQUIREMENT_TRACEABILITY.md), `tests/integration/test_authorized_critic_sweeps.py`. Pruebas sintéticas específicas: 19 PASS; suite completa ASUS Windows Python 3.12.10 **346 PASS +2 SKIP** (archivo ZIP abierto y permisos POSIX), exit 0; Ruff de archivos modificados y `git diff --check` PASS. Este resultado local no reemplaza CI del SHA definitivo.
- **Límites:** firma obligatoria solo al invocar el gate de autorización; el journal aún admite barridos no firmados para compatibilidad. Verificación de clave, no persona real, aislamiento, competencia o dictamen científico. **0/168 MUST** históricas adjudicadas y 16 DEFERRED_LAB EVAL_ONLY; Sprint 2 abierto. No publicar ZIP AWS privado.
- **Primera publicación y validación remota:** [PR #30](https://github.com/David-std/AWF/pull/30), primer commit `1608f6259c8b343c632f4b1393c3c3063b388dcf`, árbol `32995f2a6de12a4809a2ed041ce7cf124ca28199` idéntico al `git write-tree` local. [GitHub Actions 39503198440](https://github.com/David-std/AWF/actions/runs/39503198440): **4/4** Ubuntu/Windows × Python 3.12/3.13 (Ruff, formato, Pyright, pytest, build). ASUS: worktree adicional creado desde el SHA publicado, **346 PASS +2 SKIP**, 0 fallos. Diff remoto: 10 archivos previstos, 695 adiciones y 5 eliminaciones. `main` sin cambios.
- **Fusión condicionada:** el cierre documental posterior a esta validación necesita nueva CI 4/4 del SHA final, verificación de la rama, revisión de diff y merge exclusivo a `develop`. Registrar el merge/head y resultados en la discusión de PR #30.

## Incremento vigente — transiciones críticas durables (PR #29)

- **Base comprobada:** [PR #28](https://github.com/David-std/AWF/pull/28) fusionada a `develop` en `96fd77f89aa6a46a2cdeb437964230f0de78b2df`; código `d8bce83`, documentación final `85d29c1`, [CI 39374937394](https://github.com/David-std/AWF/actions/runs/39374937394) 4/4 Linux/Windows Python 3.12/3.13; ASUS aislada 308 PASS +2 SKIP. Rama de este incremento: `feat/s2-durable-critic-transitions`, derivada de ese merge. `main` sigue en `a902135b80e96eea17ebb9c229eed065077e809d`, sin cambios.
- **Entrega:** [PR #29](https://github.com/David-std/AWF/pull/29), primer commit de código/documentación `4aa5d5e8ac45eaa34912b22c8e4ad3efbaf3be4d`, árbol `61ce15f075c7b0cf14a55f641172487fb0a084ed` cotejado con el índice local. `SQLiteRevisionJournal.record_clean_sweep` y `.record_external_iteration` persisten dos tipos de intención y commit del esquema 2 con snapshot atómico, CAS, idempotencia y replay. Exigen observaciones reales del ledger del mismo run/revisión, del tipo exacto y posteriores al commit anterior. Un contexto declarado no certifica independencia. [ADR-0022](adr/0022-durable-critic-and-external-iterations.md), [guía](DURABLE_REVISION_S2.md), [AWF-R031](REQUIREMENT_TRACEABILITY.md).
- **Validación del commit `4aa5d5e`:** **329 pytest PASS** en Linux Python 3.12; Pyright 0 errores, Ruff lint/formato PASS, `uv lock --check --offline` y `uv build --offline` PASS, `git diff --check` PASS. Adversariales de reinicio, presupuestos, contaminación cruzada, versión obsoleta, reintento tras avance, interrupción y concurrencia. [GitHub Actions run 39377288572](https://github.com/David-std/AWF/actions/runs/39377288572): **4/4** Ubuntu/Windows × Python 3.12/3.13, con lint, formato, tipos, tests y build. ASUS ROG STRIX Windows Python 3.12.10 en worktree aislado al mismo SHA: **327 PASS, 2 SKIP** por ZIP abierto y permisos POSIX; salida exit 0 y checkout original `feat/s2-evidence-binding` intacto. **Condición de fusión:** CI 4/4 también en el SHA documental final; constancia adicional en la discusión de PR #29.
- **Límites abiertos:** no hay verificación real de identidad o aislamiento de críticos, firma obligatoria por barrido, custodia institucional de checkpoints, aceptación académica ni adjudicación histórica. Estado formal de conocimiento **0/168 `MUST`**, 16 `DEFERRED_LAB` solo `EVAL_ONLY`; Sprint 2 no se cierra con este incremento. Conservar el ZIP original en privado. Próximo incremento: diseñar atestaciones efectivamente ligadas al barrido y continuar adjudicación sustantiva del corpus por reglas con evidencia independiente; la optimización de replay queda condicionada por el perfil de ADR-0021.

Las secciones siguientes constituyen registro de decisiones previas; el apartado anterior prevalece para el estado operativo vigente.

## Perfil de recuperación S2 — PR #28 integrada

- Base: `develop` `f55ae6cde1443cc6dcd7e9e5024c27a1d10954aa` (PR #27 fusionada). `main` `a902135b80e96eea17ebb9c229eed065077e809d` sin cambios al iniciar. Rama: `feat/s2-revision-replay-profile`.
- Entrega: [PR #28](https://github.com/David-std/AWF/pull/28), código `d8bce83a476186eb9f2bc30f37814990df34a5c7`; `scripts/benchmark_revision_replay.py`, pruebas sintéticas, [ADR-0021](adr/0021-revision-replay-profile-before-optimization.md), [resultados y reproducción](REVISION_REPLAY_PROFILE_S2.md), trazabilidad AWF-R030. No se modifica el código de producción ni la semántica de integridad/replay.
- Diagnóstico Linux Python 3.12.14, SQLite 3.53.1: `load` de 1×128 auditorías tuvo mediana 36,434 ms (257 eventos); verificación íntegra 16×16, 52,481 ms mediana (528 eventos), con un outlier de 318,187 ms. Son tres repeticiones sintéticas, no SLO. Codec/replay domina una revisión muy larga; auditoría global domina una lectura puntual con muchas revisiones.
- Validación Linux local: script en seis casos, **310 pytest PASS**, Ruff lint/formato PASS, Pyright 0 errores, `uv lock --check --offline` PASS, `uv build --offline` PASS y `git diff --check` PASS. [Actions run 39374446476](https://github.com/David-std/AWF/actions/runs/39374446476) para `d8bce83`: **4/4** Linux/Windows × Python 3.12/3.13, incluido pytest, formato, tipos y build. ASUS Windows Python 3.12.10 en worktree separado de `d8bce83`: **308 PASS, 2 SKIP** conocidos, y benchmark 1×32 y 4×16 reproducido; checkout original sin cambios. El commit documental de cierre de esta PR requiere su propia CI antes de fusionar.
- Siguiente PR distinto: persistir `CleanSweep` e iteración externa con intent/commit/snapshot, CAS e idempotencia, replay del gate y negativos. S2 continúa abierto: 0/168 MUST adjudicadas, 16 `DEFERRED_LAB` solo `EVAL_ONLY`; corpus histórico privado.

## Integrado S2 — lote atómico de escritura de evidencia (PR #26)

- **Base exacta:** `develop` merge `3f626e2f87e6b17c9e935c95319bdb62777f180d`, PR #25 [CI 39348390792](https://github.com/David-std/AWF/actions/runs/39348390792) 4/4, 287 Linux y 285 Windows +2 SKIP. `main` sigue intacta en `a902135b80e96eea17ebb9c229eed065077e809d`.
- **Integración comprobada:** [PR #26](https://github.com/David-std/AWF/pull/26) fusionada en `develop` con merge commit `c8d77a250683bb77655bb6899bb749cfc5985c61`; feature SHA `9ce48a64f7afd2a3ca37bb48112a4608290b959a`, árbol `c0b74835f2c642de25c3d07740b486f4c51cf53b`, 14 archivos intencionados, 1 commit sobre #25. No se tocó `main`. El corte anterior interrumpido no estaba publicado y se reconstruyó sobre #25 sin perder sus contratos.
- **Contrato:** `EvidenceStorePort.append_batch` recibe `EvidenceAppend` tipados, lote de 1–512 eventos y hasta 8 MiB, compara un `expected_head` opcional bajo `BEGIN IMMEDIATE` y audita todo el ledger solo una vez. El `append` individual reutiliza la ruta. Se cotejan esquemas después de bloquear; cualquier fallo, incluida interrupción del intérprete, revierte el lote. Sin caché confiable ni idempotencia de operación implícita.
- **Vínculo con fuentes:** `record_evidenced_chunks` compara cada `ObservedChunk` con identidad, longitud y SHA del `CanonicalManifest`; la cobertura del total sigue verificándose por separado. No atribuir `READ`, conocimiento ni validez académica a eventos válidos.
- **Validación final Linux:** 303 pytest PASS CPython 3.12.14, Ruff, Pyright 0 errores, `uv lock --check --offline`, `uv build --offline`, diff limpio. Microbenchmark sintético de 16/64/128/256 eventos, tres repeticiones: mejoras 13,23× / 41,09× / 82,93× / 151,41×; no es SLO. [GitHub Actions 39365271054](https://github.com/David-std/AWF/actions/runs/39365271054): 4/4 Linux/Windows × Python 3.12/3.13 aprobados. ASUS Windows Python 3.12.10 en worktree aislado del SHA exacto: **301 PASS y 2 SKIP** conocidos por bloqueo ZIP y permisos POSIX; benchmark 16/64/128: **17,3× / 47,45× / 120,05×**. Checkout original `feat/s2-evidence-binding` limpio.
- **Referencias:** [ADR-0020](adr/0020-atomic-batched-evidence-append.md), [guía de escritura](EVIDENCE_BATCH_APPEND_S2.md), [AWF-R029](REQUIREMENT_TRACEABILITY.md). Evidencia de auditoría detallada registrada como comentario en PR #26. Próximo paso técnico S2: perfilar el replay de historiales extensos y diseñar transiciones durables de barridos críticos; no cambiar contratos de aceptación sin ADR y pruebas.
- **Pendientes estructurales S2:** barridos críticos durables, custodia institucional de checkpoints, perfilado de replay, 136 MUST sin análisis sustantivo y 168 MUST sin adjudicación formal. No publicar ZIP privado, ni comenzar entrenamiento.

## Continuación S2 — lectura de eventos por snapshot verificado (tras PR #24)

- **Base confirmada:** `develop` tras PR #24, merge commit `e32e0ea99e76640133d328548214f0efbae63cfc`; `main` sigue en `a902135b80e96eea17ebb9c229eed065077e809d`. PR #24 cerrada y fusionada con código `dae66ed7057353d521dfab4077b26b9a4a333a86`, [CI 39203570452](https://github.com/David-std/AWF/actions/runs/39203570452) 4/4, 279 Linux y 277 Windows ASUS +2 SKIP, sin modificar worktree original Windows. Incremento actual: [PR #25](https://github.com/David-std/AWF/pull/25), rama `feat/s2-ledger-scaling`, **pendiente de fusionar hasta verificar el SHA final**.
- **Riesgo:** cada `resolve_event` audita O(n) objetos y eventos; en un gate con `m` fragmentos, `m` auditorías repetidas elevan el trabajo aproximadamente a `O(n×m)`. Nunca confiar en un head cacheado entre llamadas para optimizarlo.
- **Solución:** `VerifiedEvidenceReaderPort` y `SQLiteEvidenceLedger.verified_read` auditan todos los objetos y DDL en una única transacción SQLite; resuelven luego digest+metadatos+bytes por recibo sin mezclar heads ante append concurrente. `verify_chunk_coverage`, `verify_audit_receipts` y `verify_progress_claims` comparten contexto, incluso READ anidado. No se relajan las puertas ni se cambia el `resolve_event` público.
- **Primer corte Linux local:** 286 pytest PASS Python 3.12 (7 pruebas nuevas de conteo real de auditorías, lectores concurrentes, head antiguo, estado incompleto y esquema corrupto), Ruff y Pyright 0 errores tras formato. Benchmark sintético Linux CPython 3.12.14, mediana de tres repeticiones: 16 eventos 9,199→0,665 ms (13,84×), 64 eventos 78,185→1,762 ms (44,37×), 128 eventos 249,342→3,328 ms (74,92×), 256 eventos 799,826→5,737 ms (139,42×). Es evidencia local, no SLO ni comparación de hardware. [ADR-0019](adr/0019-verified-evidence-read-snapshots.md), [guía y script reproducible](EVIDENCE_READ_SCALING_S2.md).
- **Evidencia del primer commit publicado:** `bc5d0fdb1d0ff40e24a514562fb9dd8485d75939`. [CI 39347741248](https://github.com/David-std/AWF/actions/runs/39347741248): 4/4 Linux/Windows × Python 3.12/3.13, Ruff/Pyright/pytest/build PASS. ASUS ROG STRIX Windows Python 3.12.10, worktree aislado al SHA exacto: **284 PASS y 2 SKIP** (ZIP abierto/permiso POSIX); rama original `feat/s2-evidence-binding` limpia. Benchmark ASUS con 16/64/128/256 eventos: mejoras sintéticas 15,15× / 49,76× / 35,76× / 153,23×. La segunda revisión explicitó el límite de verificación de firmas externas y añadió un caso adversarial para rechazar lectores reutilizados después del cierre (Linux **287 PASS**); repetir los gates sobre el último SHA antes del merge. No usar ZIP histórico ni publicar datos privados. Riesgos S2 aún abiertos: barridos de críticos durables, real custodia/rotación de checkpoints, replay a escala, 136 MUST sin propuesta sustantiva y adjudicación humana de las 168 MUST. **0/168 REVIEW_ATTESTED**.

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

## S2 — inspección privada de dossiers históricos (PR #31)

- Base desde `develop` fusionado tras PR #30: `c4ee901a34c19f5704b7e6cd9d2c29b9ac6f42ed`; `main` permanece en `a902135b80e96eea17ebb9c229eed065077e809d`. PR #31: https://github.com/David-std/AWF/pull/31.
- Se agregó `awf knowledge inspect-review`, un lector de solo lectura de los expedientes privados creados por `plan-review`. La fuente canónica se reconstruye desde el ZIP original SHA-pinned; el verificador rechaza adulteraciones de campos inmutables, reemplazo/ausencia de lotes, IDs inválidos y propuestas `DEFERRED_LAB` promovidas.
- Resultados posibles: `OPEN`, `PARTIAL`, `PROPOSAL_INCOMPLETE`, `PROPOSAL_DOCUMENTED`. El informe exporta **solo identificadores y nombres de lagunas**, sin fuente privada, notas completas ni declaraciones de evidencia.
- `--require-documented` falla si queda alguna ficha abierta/incompleta. Este gate no es ni pretende ser `REVIEW_ATTESTED`, un derecho de entrenamiento ni verificación científica.
- Código: `src/awf/knowledge/adjudication_dossiers.py`, `src/awf/cli/main.py`; pruebas unitarias e integración; ADR-0024; `docs/KNOWLEDGE_COMPILER_S2.md`.
- Evidencia del commit de código `be9df691c667dfcb9db16037f10d4e8ccd99a97f`: [CI PR 39510436138](https://github.com/David-std/AWF/actions/runs/39510436138) **4/4 SUCCESS**, Ubuntu/Windows × Python 3.12/3.13, **364 pytest PASS en Ubuntu/3.12**, lint, Ruff 0.14.0, Pyright 0 errores, build.
- En ASUS se produjo un directorio **scratch** para comparar formato; la descarga GitHub del worktree aislado falló por conexión HTTPS. No se afirma reproducción local de tests en ASUS. El checkout original en `Downloads/AWF` no se modificó.
- **Estado epistémico:** 0/168 `MUST` adjudicadas, 16 `DEFERRED_LAB` `EVAL_ONLY`; no autorizado ningún modelo ni entrenamiento. Próxima prioridad: atar los IDs de evidencia con eventos reales y revisión firmada por rol, con comprobación independiente y derechos de fuente antes de avanzar el ledger.

