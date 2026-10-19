# S2 — Knowledge Compiler local

Este módulo es un **primer corte funcional** de Sprint 2. No integra contenido histórico en el repositorio. El ZIP `academic_writing_suite_v3_19_1_product(1).zip` se conserva exclusivamente en tu ordenador.

## Ejecución con el archivo local

```shell
awf knowledge import "/ruta/local/academic_writing_suite_v3_19_1_product(1).zip" \
  --manifest provenance/source-manifest.json
awf knowledge audit .awf/knowledge/registry_<12-digitos-del-sha>.json \
  --archive "/ruta/local/academic_writing_suite_v3_19_1_product(1).zip"
```

Puedes elegir `--output .awf/knowledge/mi-registro.json` para evitar buscar el nombre. La salida incluye ID, hash del enunciado, estado, dominio, fuentes internas y clasificación, **sin texto de reglas ni manuscritos**. No se sube ningún dato.

La primera importación reconocida con el ZIP correcto crea 184 registros: 168 `UNRESOLVED` y 16 `EVAL_ONLY`. Esto **no significa 184 reglas adjudicadas**; la clasificación editorial aún está pendiente, precisamente para no asumir que todo el corpus antiguo debe convertirse en código o entrenamiento.

## Review overlay local opcional

```json
{
  "source_sha256": "HASH_REAL_DEL_ZIP",
  "decisions": [
    {
      "id": "DSR-001",
      "disposition": "KEEP_AS_CODE",
      "reviewer": "revisor",
      "reason": "Existe una comprobación reproducible y una prueba adversarial específica."
    }
  ]
}
```

La justificación debe ser concreta. Las disposiciones disponibles son `KEEP_AS_CODE`, `KEEP_AS_CONTEXT`, `TRAIN`, `EVAL_ONLY` y `REMOVE_FROM_ACTIVE`; estas etiquetas describen decisiones de investigación, **no constituyen permiso de redistribución ni entrenamiento**. No se pueden promocionar entradas `DEFERRED_LAB` a ejecución.

## Separación de garantías

- Digest del ZIP: identidad exacta de bytes respecto del manifiesto.
- Digest de regla: identidad de enunciado normalizado, no respaldo académico.
- Importación: integridad estructural y ausencia de omisiones.
- `REVIEW_PROPOSED`: propuesta de clasificación y motivo atribuido a un revisor declarado, **no** una adjudicación formal, autorización de uso ni permiso de entrenamiento. Una cadena de nombre y razón no demuestra identidad.
- `REVIEW_ATTESTED`: **reservado**; el importador v1 no lo produce y la auditoría v1 rechaza registros que reclamen ese estatus porque todavía no hay verificación independiente ni evidencias ligadas por regla.
- `knowledge audit`: consistencia del reporte, no prueba de que cada revisión sea correcta.
- Duplicados: coincidencia textual; contradicciones semánticas **no** implementadas.

## Pendientes del Sprint 2

Integrar revisión basada en casos, clasificar/justificar los 168 `MUST` uno por uno, inventariar licencias del corpus, detectar conflictos con evidencia, cerrar dependencias explícitas, construir dataset card y decidir almacenamiento transaccional por necesidades reales. Deben mantenerse visibles como pendientes incluso cuando la CI esté verde.

**Endurecimiento previo a fusión (2026-10-19):** overlays preexistentes que antes generaban `REVIEW_ATTESTED` ahora generan `REVIEW_PROPOSED` al reimportarse. Los reportes antiguos que afirman attestation sin evidencias independientes se rechazan, por lo que deben reconstruirse a partir del ZIP local fijado. La prohibición de promocionar `DEFERRED_LAB` se verifica también al auditar un JSON alterado manualmente. Esta migración es intencionalmente no destructiva: no se reescribe el ZIP ni el registro histórico original.
