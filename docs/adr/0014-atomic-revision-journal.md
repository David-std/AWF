# ADR-0014 — Estado de revisión y evidencia en una sola transacción local

- **Estado:** aceptada para prototipo estrecho de S2; no autorizada para aceptación académica automática.
- **Fecha:** 2026-10-18.
- **Continuidad:** ADR-0010 a ADR-0013, rama base `feat/s2-evidence-binding` (PR #18).

## Problema

`record_evidenced_audit` inserta un evento y devuelve una nueva instancia inmutable
de `RevisionState`. Si el proceso termina después del append pero antes de que el
llamante conserve el estado, queda evidencia local válida sin un commit de revisión.
Reintentar una solicitud puede duplicar eventos y dos escritores pueden partir de
la misma versión sin detectar el conflicto.

## Decisión

1. Añadir `SQLiteRevisionJournal` sobre **el mismo fichero SQLite** que
   `SQLiteEvidenceLedger`, conservando las tablas y los eventos ya existentes.
   Una tabla `revision_snapshots` almacena instantáneas inmutables, versionadas,
   con hash propio, hash padre, ID de operación, huella de solicitud y enlace al
   evento `REVISION_TRANSITION`.
2. Ejecutar `BEGIN IMMEDIATE` antes de recuperar la versión actual. La evidencia
   `AUDIT_RECEIPT`, su evento `REVISION_TRANSITION` y la instantánea se escriben
   bajo **un solo COMMIT**. Un error, cancelación o terminación previa al COMMIT
   deja la transacción sin confirmar y la recuperación solo ve estados completos.
3. Usar versiones optimistas y `operation_id` estable por revisión. Un reintento
   byte-equivalente devuelve la instantánea del commit existente (`replayed=True`);
   una clave reutilizada con parámetros distintos o una versión obsoleta falla.
4. Recuperar desde las instantáneas ordenadas y comprobar toda la cadena previa
   de eventos y objetos. Cada evento de commit debe corresponder a una fila,
   y cada fila a un evento exacto. Comprobar hashes padre/estado, run, versión,
   payload y el recibo de auditoría unido al evento original.
5. Mantener `RevisionState` y sus operaciones puras. El puerto
   `RevisionJournalPort` ofrece en este corte solo `create`, `record_audit` y
   `load`, sin persistir aún `accept_edit`, hallazgos ni barridos críticos.
   **El camino previo en memoria no se vuelve durable automáticamente.**
6. Preservar el esquema `user_version=1` del ledger de evidencia; la tabla nueva
   es una extensión aditiva, sin eliminar ni convertir eventos históricos.
   Si un trigger de inmutabilidad existente desaparece, se rechaza su lectura,
   sin repararlo silenciosamente.

## Alternativas y consecuencias

| Alternativa | Evaluación |
|---|---|
| JSON de estado + SQLite de eventos | Necesitaría journal de intención, protocolo de recuperación entre dos almacenes y resolver fallos de publicación de archivos |
| Dos bases de datos y coordinación distribuida | Complejidad no justificada para prototipo local |
| Un solo estado mutable sin historial | Pierde replay y detección de versiones históricas eliminadas o alteradas |
| Event sourcing completo | Exige operadores de dominio y migraciones de replay para cada transición; innecesario para el corte de auditoría |
| Instantáneas append-only + evento de commit | Elegida: trazabilidad explícita, CAS transaccional y reconstrucción verificable sin reescribir dominio |

El costo inmediato es duplicar metadatos de estado en snapshots y recorrer el
historial local en cada acceso. Se debe medir y optimizar después, no afirmar
rendimiento constante. Se reutiliza el adaptador del ledger y la librería estándar,
sin añadir ORM, colas ni infraestructura distribuida.

## Fundamentos técnicos

- SQLite, [Isolation in SQLite](https://www.sqlite.org/isolation.html):
  `BEGIN IMMEDIATE` toma el derecho de escritura antes de leer para actualizar.
- SQLite, [Write-Ahead Logging](https://www.sqlite.org/wal.html):
  atomicidad del commit en WAL y recuperación de transacciones incompletas.
- SQLite, [PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous):
  `FULL` conserva las barreras de sincronización del ledger original; las
  garantías efectivas dependen también del sistema de archivos y hardware.

## Pruebas y límites

Pruebas sintéticas verifican reinicio, retry tras respuesta perdida, misma clave
con distinto contenido, versión antigua, ejecución diferente, error provocado
después del evento de auditoría, salida abrupta del proceso antes del commit,
competencia de dos escritores, migración aditiva, pérdida de fila, alteración de
bytes y trigger ausente. La CI multiplataforma verifica la compatibilidad.

**No se demuestra:** identidad o autoridad del evaluador, verdad académica,
independencia entre críticos, seguridad ante un atacante que reescribe la base
y el checkpoint externo, recuperación de transiciones todavía no portadas ni
resistencia a todos los cortes de energía/hardware. `PersistedRevision` es
integridad de estado local, nunca un certificado de `CONVERGED`.

El anclaje externo se acepta en `load(expected_head=...)`, pero la custodia,
rotación y firma de checkpoints queda pendiente. El histórico AWS 3.19.1 y
manuscritos privados siguen fuera de Git.
