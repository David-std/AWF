# ADR-0020 — Lotes atómicos de evidencia con auditoría de escritura única

- **Estado:** implementado y probado en rama S2; integración condicionada a CI y Windows.
- **Fecha:** 2026-10-20 (UTC).
- **Base:** PR #25 en `develop`; ADR-0012, ADR-0013, ADR-0017 y ADR-0019.

## Problema

La operación pública `append` audita toda la cadena y todos los blobs en cada
evento. Al observar muchos fragmentos de una misma fuente, cada inserción
vuelve a recorrer las anteriores, con costo acumulado aproximadamente
cuadrático para un lote. Además, el contrato de esquema se comprobaba antes
de `BEGIN IMMEDIATE`: podía cambiar entre esa lectura y la adquisición del
bloqueo. Los fragmentos eran persistidos individualmente; si la operación
de alto nivel fallaba a mitad de inventario, dejaba un prefijo confirmado.

## Decisión

1. Añadir `EvidenceAppend` como solicitud tipada, y
   `EvidenceStorePort.append_batch(entries, expected_head=None)` como operación
   **acotada y atómica**. Hasta 512 eventos y 8 MiB sumados, con el máximo
   preexistente de 512 KiB por evento; el lote vacío o inválido falla sin
   escribir. `append` delega a este mismo camino con un solo evento.
2. Ejecutar `BEGIN IMMEDIATE` **antes** de comprobar esquema, integridad
   referencial, bytes y cadena; auditar el historial una sola vez, contrastar
   el `expected_head` dentro del bloqueo y crear cada evento con el head
   resultante del anterior. `COMMIT` solo al terminar el lote. Toda excepción,
   incluida interrupción del intérprete, causa `ROLLBACK` explícito.
3. Mantener `expected_head` opcional por compatibilidad. Sin él, escritores
   concurrentes quedan serializados, pero ambos pueden añadir sus eventos;
   con un head externo obsoleto, la segunda escritura falla sin mutación.
   Un head suministrado por el mismo SQLite no acredita custodia o firma.
4. `record_evidenced_chunks` permite fragmentos parciales de un
   `CanonicalManifest`, pero contrasta identidad, longitud y SHA-256 de
   **cada** fragmento antes de llamar al adaptador. La verificación de
   cobertura completa sigue ocurriendo después, con
   `verify_chunk_coverage`. No se afirma que se leyó ni entendió la fuente.
5. El diario de revisión conserva su propia transacción coordinada y
   `_append_in_transaction`; el lote no crea una segunda ruta de
   persistencia ni un caché de heads. Se mueve al interior de la transacción
   la validación de esquema en `_write`/`load` del diario y `retrieve` del
   ledger, eliminando la misma ventana entre DDL y lectura/escritura.
   Las auditorías de lectura siguen íntegramente operativas según ADR-0019.

## Alternativas

| Alternativa | Evaluación |
|---|---|
| Suprimir auditorías de escritura por head cacheado | Rechazada; permitiría aceptar corrupción o truncación local |
| Auditar cada fragmento y compensar si falla otro | Rechazada; prefijos observables y fallos de compensación |
| Insertar todos los eventos en una sola transacción auditada | Elegida; reduce auditorías conservando cadena, bloqueo y rollback |
| Reemplazar SQLite por cola/servicio independiente | Rechazada; introduce coordinación distribuida sin necesidad medida |

## Evidencia de aceptación y límites

Las pruebas comprueban contador real de auditorías, orden, contenido deduplicado,
inserción abortada en medio, `KeyboardInterrupt`, esquema adulterado,
tampering previo, dos escritores concurrentes, head obsoleto, límites y
fragmentos con hash/identidad alterados; hay propiedades para secuencias de
payloads sintéticos y benchmark reproducible.

El costo por lote todavía incluye **una auditoría O(n)** del ledger completo
antes de escribir. No se prueba rendimiento bajo múltiples procesos,
volúmenes de gigabytes, contingencia prolongada de WAL, custodia real de
checkpoints ni autenticidad académica. Las 168 reglas MUST siguen sin
adjudicación formal y S2 no habilita entrenamiento neuronal.
