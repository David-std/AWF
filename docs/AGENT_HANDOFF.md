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
