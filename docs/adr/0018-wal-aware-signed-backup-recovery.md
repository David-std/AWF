# ADR-0018 — Backups online SQLite y restauración a ruta nueva ligada a checkpoint

- **Estado:** incremento S2 verificable, con custodia externa operada manualmente.
- **Fecha:** 2026-10-19 (UTC).
- **Base:** ADR-0012, ADR-0014, ADR-0015, ADR-0017; `develop` tras PR #23.

## Necesidad y fallo adversarial

El almacén de evidencia usa SQLite en modo WAL y contiene **dos contratos
inseparables**: eventos/bytes de evidencia y estados del journal de revisiones.
Una copia directa del fichero `.sqlite` puede omitir transacciones confirmadas
que siguen en el `.sqlite-wal`. Otro error sería aceptar un backup cuyo ledger
conserva hashes correctos pero al que se ha alterado o borrado un snapshot
persistente de revisión. Restaurar sobre una base existente también puede
destruir resultados válidos posteriores o interrumpir lectores.

## Decisiones

1. `SQLiteSnapshotWriter.create_new` usa exclusivamente la API online
   `sqlite3.Connection.backup()` para obtener una vista coherente que incluye
   las transacciones WAL confirmadas; **no** usa `shutil.copyfile` del fichero
   vivo ni altera la base origen. Trabaja primero en fichero temporal privado
   del mismo directorio que el destino.
2. El caso de uso `create_verified_snapshot` exige antes la firma Ed25519,
   grant, política SHA-pinned, último checkpoint SHA-pinned, historia completa
   y que el checkpoint sea el **head actual**, no solo un prefijo. El escritor
   vuelve a comprobar el head exacto y número de eventos en la copia temporal.
   Esto bloquea una append concurrente entre autorización y backup.
3. `SQLiteRevisionJournal.verify_all_revisions` audita la cadena y todos los
   objetos una sola vez y recupera cada historial de revisión dentro de **la
   misma transacción de lectura**. Valida la definición del journal y sus
   triggers, detecta IDs de transición huérfanos, snapshots faltantes, hashes,
   secuencias y replays alterados. Una base solo de evidencias, sin la tabla de
   revisiones, sigue siendo legítima **si no existen eventos de transición**.
4. La copia queda publicada únicamente después de pasar la verificación,
   finalizar en journal SQLite de un solo fichero, fsync y enlace duro
   create-only (`os.link`) en el directorio destino. No se usa `os.replace`:
   la carrera entre `exists()` y `replace()` podría sobrescribir un destino
   aparecido durante la operación. `os.link` falla si el destino ya existe.
   En plataformas sin hardlinks se falla cerrado y no se simula atomicidad.
   La transferencia tiene deadline monotónico configurable, por defecto
   120 segundos, para no esperar indefinidamente bajo escritura intensa.
5. `snapshot-create` y `snapshot-restore` invocan la **misma garantía**.
   Restaurar solo crea una ubicación inexistente; nunca reemplaza la base
   activa automáticamente. Cualquier corte operativo para cambiar la base en
   uso debe ser un procedimiento adicional de operador con rollback propio.
6. `SnapshotReceipt` en `application.dto` y `SnapshotWriterPort` en
   `application.ports` conservan los límites hexagonales. El adaptador no
   importa casos de uso ni posee claves. El SHA-256 del fichero resultante es
   una medición local en la publicación, no una firma ni una retención externa.

## Pruebas negativas obligatorias

- Origen activo en WAL con lector antiguo abierto: el snapshot contiene todos
  los eventos confirmados pese al checkpoint SQLite pendiente.
- Append entre prueba de firma y backup: el `expected_head` ya no coincide;
  no se publica destino.
- Historial local reconstruido o trigger SQLite alterado: falla antes de
  escribir un destino.
- Trigger de snapshot anulado y bytes de estado cambiados **sin modificar
  ninguno de los hashes del ledger**: falla el replay del journal.
- Snapshot modificado antes de restaurar, destino ya existente, path de origen
  igual a destino, enlace simbólico y error inyectado al publicar: fallo cerrado;
  el origen se conserva y no quedan ficheros temporales en fallos normales.
- Doble operación backup→restore verifica bytes, número de eventos, último
  digest y ausencia de reescrituras del origen.

## Límites, alternativas y migración

| Opción | Consideración |
|---|---|
| Copia OS de `.db` aislada con WAL activo | Rechazada: puede omitir commits confirmados |
| `VACUUM INTO` | Posible API de snapshot, pero la interfaz `backup` está disponible en Python y admite control incremental |
| Restaurar con overwrite de la base activa | Rechazada: borrado potencial e interrupción de transacciones/lectores |
| Backups con restauración create-only y head firmado | Elegida: riesgo destructivo acotado y prueba falsable de consistencia |

- El último hash firmado **debe estar realmente custodiado por un actor externo**.
  Sin ese hecho, el software por sí solo no demuestra recuperación de historia
  completa ni un punto de recuperación aceptable. Tampoco proporciona
  almacenamiento remoto, distribución de claves, retención, ACL institucional,
  replicación, scheduler, RPO/RTO prometido, ni consola de cutover.
- Se obliga a que el head coincida exactamente con el firmado. No se intenta
  recuperar un backup cuyos eventos posteriores no tienen checkpoint nuevo.
  Para respaldo de un ledger activo con anexos, primero detener/escalar la
  ventana de firma y capturar el head más reciente; el contrato falla cerrado
  si aparece otra append antes de capturar la copia.
- Un hardlink create-only puede no funcionar en algunos volúmenes. No se
  degrada a `replace`; el operador elige un volumen compatible y vuelve a
  intentar. Un crash puede dejar un fichero temporal oculto **no publicado**;
  se requiere limpieza supervisada, no se borran nombres ambiguos.
- La comprobación de revisiones exige un recorrido de la evidencia más
  verificación por cada revisión; medir p95/crecimiento en S2 antes de
  garantizar objetivos de latencia. No se demuestran permisos científicos,
  evaluación académica, identidad civil ni 168 MUST adjudicadas.

Ver [guía de respaldos/recuperación S2](../VERIFIED_SNAPSHOTS_S2.md).
