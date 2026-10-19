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
