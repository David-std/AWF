# ADR-0010 — Prototipo de control de auditorías sin autoverificación

- **Estado:** Aceptado para experimento de dominio S2; no aprobado para producción ni evaluación académica automática.
- **Fecha:** 2026-10-17.
- **Origen:** revisión local del bloque histórico DSR-001..015, sin incorporar código del ZIP al repositorio.
- **Decisión:** iniciar un modelo de estado puro en `awf.domain.revision_audit` sobre `DocumentIR`, con inventario explícito no vacío, recibos de auditoría, huellas de alcance, hallazgos persistentes hasta resolución y barridos de críticos distintos. `RevisionPolicy` es fuente única de 8/12/2 en este prototipo, sin crear aliases heredados como controladores adicionales.
- **Estrategia de invalidación:** `DOCUMENT` por defecto obliga a repetir la auditoría tras cualquier cambio del original. `LOCAL_NEIGHBORS` es una excepción explícita; solo transfiere una auditoría si el contenido propio y sus vecinos coinciden. En ambos casos se registra el vínculo entre hashes de versiones. Esta excepción **no** es prueba de ausencia de referencias cruzadas o efectos semánticos lejanos.
- **Control de convergencia:** ninguno de los estados `OPEN`, `UNKNOWN`, `DIRTY`, recibo ausente, hallazgo material abierto o juicio de crítico repetido puede aprobar. Presupuesto consumido no autoriza `CONVERGED`.
- **Razón para no copiar el runtime antiguo:** su cobertura puede reportar 100% sin inventario esperado y su transición de edición no rellena `dirty_set`; adoptar ambas propiedades propagaría falsos positivos de verificación.
- **Limitaciones deliberadas:** la evidencia se introduce como identificadores de recibos, **no como pruebas criptográficas o juicios de calidad independientes**. La independencia real del crítico, persistencia de eventos, roles edit/audit, totalidad de dependencias, extracción robusta DOCX/PDF y verificación semántica siguen pendientes.
- **Extensión prevista:** conectar almacenamiento transaccional de eventos, generación real y verificación de fuentes solo cuando existan tests de integración y amenaza de privacidad. Mantener este componente como núcleo puro.
- **Pruebas adversariales:** inventario vacío, firma inválida, auditoría incompleta, cambios de contexto, reutilización injustificada, hallazgos sin resolución, críticos duplicados, crítica con diagnóstico heredado, presupuesto agotado y edición sin bytes nuevos.

## Segunda pasada: coherencia de política

Se identificó una inconsistencia de un prototipo inicial: el registrador de barridos consultaba el límite por defecto incluso si el veredicto utilizaba una política personalizada. Se corrigió haciendo pasar la misma `RevisionPolicy` a ambas decisiones, impidiendo la reutilización de recibos de aislamiento y ejecutando explícitamente el límite de iteraciones externas. Nuevos tests prueban la política de 3 críticos, presupuesto externo de 2 iteraciones y rechazo de strings no tipadas como disposiciones de auditoría.

## Auditoría previa a fusión en develop (2026-10-19)

- El veredicto comprueba **primero** los presupuestos agotados: aunque se hayan registrado barridos limpios, consumir el límite de revisión o de iteraciones externas devuelve `BUDGET_EXHAUSTED`, nunca `CONVERGED`.
- Los recuentos `required_checks`/`checks_executed` y límites de política exigen enteros reales, no `bool`, floats o strings; la materialidad de hallazgos también exige booleano.
- `LOCAL_NEIGHBORS` incorpora tipo y nivel de encabezado del bloque y de sus vecinos, además del texto. Cambiar un H1 por H2 invalida el scope. Esto **cambia los fingerprints anteriores**: los recibos locales previos deben revalidarse y nunca promoverse por compatibilidad implícita. Aún falta versionar formalmente los fingerprints al persistir migraciones de producción.
- Se agregan casos adversariales para todos esos límites; el resultado continúa siendo un prototipo de dominio sin verificación académica independiente.
