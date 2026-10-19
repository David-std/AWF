# ADR-0012 — Libro transaccional local de evidencias

- **Estado:** aceptada para prototipo S2, **no para certificación externa**.
- **Fecha:** 2026-10-17.
- **Contexto:** Las revisiones DSR-001..015 y DSR-016..032 introdujeron `evidence_ref`, pero no existe todavía una comprobación durable de los bytes a los que apuntan esas referencias. La identidad de una fuente o una decisión de modelo no equivale a la autenticidad de una prueba.

## Decisión

Implementar `SQLiteEvidenceLedger` con **SQLite estándar de Python** y sin dependencias de ORM. Una transacción `BEGIN IMMEDIATE` guarda los bytes de una evidencia y un evento tipado; si la inserción del evento falla, se revierte también el objeto. El libro contiene:

1. `evidence_objects`, almacenados por SHA-256 y longitud, en un BLOB local.
2. `events`, ordenados por secuencia sin huecos, con clase, ejecución, sujeto, hash de evidencia, UTC, hash anterior y digest canónico del evento.
3. Triggers de prohibición de `UPDATE` y `DELETE` para evitar modificaciones accidentales desde SQL.
4. `verify()` recorre **todos** los eventos y objetos, comprueba referencias, hashes, longitud, secuencia, versiones de esquema y definiciones efectivas de tablas y triggers. No basta que un disparador conserve su nombre: un reemplazo sin `RAISE(ABORT)` invalida el contrato. La comparación omite únicamente `IF NOT EXISTS`, que no modifica su operación.
5. `--expected-head` acepta un digest conservado **fuera de la base de datos**, útil para detectar una restauración a un prefijo válido del historial. Sin un head externo, una truncación completa y coherente del final no es detectable.
6. WAL, `synchronous=FULL` y `foreign_keys=ON` para durabilidad local y concurrencia básica. No hay API remota, almacenamiento en nube ni cifrado gestionado por AWF.

## Justificación frente a ADR-0008

ADR-0008 aplazó SQLite mientras solo había archivos JSON exportados. **Ahora existe una operación que exige atomicidad entre la evidencia y su evento**, además de recuperación tras reinicios y verificación por versión. Estos requisitos justifican SQLite. Mantener `registry_store.py` para los exportes de metadatos; no migrar a una base de datos todo el sistema ni introducir SQLAlchemy/Alembic en este sprint.

## Protección, alcance y amenazas

- La ubicación predeterminada `.awf/evidence/ledger.sqlite` se ignora en Git, incluidos sidecars WAL/SHM. Los originales y el ZIP histórico **no se copian ni se publican**.
- Cada evidencia tiene tamaño entre 1 y 512 KiB. Se recomienda almacenar registros/fragmentos necesarios, **no corpus completos**, manuscritos íntegros o secretos de acceso.
- El CLI no imprime el contenido de la evidencia, solo el digest, secuencia, estado y ruta del almacén. La protección ante archivos simbólicos y sobreescritura de la fuente evita varios errores comunes.
- El hash encadenado es **integridad relativa a un checkpoint confiable**, no firma digital. Un atacante con permisos suficientes puede reconstruir la base, alterar el código/verificador o sustituir el head. Los timestamps son declaraciones del reloj local.
- Un `AUDIT_RECEIPT` almacenado **no demuestra** que el evaluador fuera independiente ni que su criterio sea correcto. Las firmas, sellos de tiempo externos, identidad del actor, gestión de permisos y verificación de verdad científica permanecen abiertos.
- SQLite no proporciona control de acceso adicional al sistema operativo. El propietario debe proteger backups, volumen y equipo. No prometer confidencialidad criptográfica.
- `verify` es O(n) en eventos y bytes almacenados, y `append` verifica el historial existente antes de agregar. Correcto para esta escala de prototipo; índices, checkpoint periódicos y benchmark quedan pospuestos con mediciones.

## Criterios de aceptación

Reinicio recupera bytes idénticos; se rechazan cambio de payload/evento/versión, huecos, disparadores ausentes o reemplazados por otros inertes con el mismo nombre, definiciones divergentes de tablas, checkpoint divergente, archivo simbólico, nombre inválido y contenido vacío/grande; reusar un hash conserva objeto único pero produce eventos distintos; una escritura abortada no deja bytes huérfanos; escrituras concurrentes generan una secuencia continua. Matriz Linux/Windows Python 3.12/3.13 y prueba en el equipo del usuario, sin datos privados en el repositorio.

## Límites de integración

Este prototipo hace persistentes evidencias genéricas, pero **aún no conecta automáticamente los recibos** del motor `revision_audit` o `knowledge_integrity` con el almacén. Por tanto no puede elevar sus estados declarativos a una certificación de autenticidad. Esa conexión exigirá referencias tipadas a pruebas realmente observadas, reglas de autorización y tests de recuperación del flujo completo.
