# S2 — Copias SQLite coherentes y restauración verificada

Este contrato protege el historial de evidencias **y** los snapshots del
journal de revisiones. Exige el checkpoint del **head actual** firmado bajo la
política de custodios separada de SQLite. No automatiza la custodia ni restaura
encima de una base existente.

## Preparación obligatoria

1. Asegurar un snapshot de checkpoint firmado auténtico conforme a la
   [guía de checkpoints](SIGNED_CHECKPOINTS_S2.md), con todos sus ancestros.
   El testigo independiente debe conservar el SHA-256 del último JSON firmado
   y de la política. No derivar los valores esperados del propio fichero.
2. Usar un destino nuevo y vacío en un volumen de archivos que soporte
   hardlinks (publicación atómica create-only).
3. Para una base con escrituras, coordinar el instante de checkpoint. Si se
   anexa un evento después de la firma pero antes/durante el backup, se
   rechazará el nuevo fichero y deberá obtenerse un checkpoint actualizado.

## Crear backup

```shell
awf evidence snapshot-create .awf/evidence/ledger.sqlite \
  /ruta/segura/backup-2026-10-19.sqlite \
  --checkpoint-file /ruta/privada/checkpoint_mas_reciente.json \
  --expected-checkpoint-sha256 HASH_ULTIMO_DEL_TESTIGO \
  --policy-file /ruta/privada/custodios.json \
  --expected-policy-sha256 HASH_POLITICA_DEL_TESTIGO
```

La transferencia online tiene un tiempo máximo por defecto de 120 segundos;
se puede ajustar mediante `--timeout-seconds N` (entre 1 y 3600). Si vence
el límite se aborta la copia temporal y no se publica un destino incompleto.
El tiempo máximo cubre la transferencia, **no** garantiza una duración total
del replay de revisiones en bases grandes.

Para una cadena con varios checkpoints, añadir tantos
`--history-file /ruta/checkpoint_antiguo.json` como sea necesario,
**desde el más antiguo hasta el inmediatamente anterior**.

El comando publica `SNAPSHOT_BACKUP_CREATED` con ruta, cantidad de eventos,
head y `snapshot_file_sha256`. Este hash del fichero físico se puede guardar
para controlar traslado de bytes, pero **no** sustituye el hash del checkpoint
firmado. No se imprime el contenido del manuscrito ni se genera una clave.

## Restaurar sin sobrescribir la base activa

```shell
awf evidence snapshot-restore \
  /ruta/segura/backup-2026-10-19.sqlite \
  /ruta/nueva/ledger-restaurado.sqlite \
  --checkpoint-file /ruta/privada/checkpoint_mas_reciente.json \
  --expected-checkpoint-sha256 HASH_ULTIMO_DEL_TESTIGO \
  --policy-file /ruta/privada/custodios.json \
  --expected-policy-sha256 HASH_POLITICA_DEL_TESTIGO
```

Agregue `--history-file` para todos los ancestros, si los hay. El backup
fuente también se vuelve a comprobar contra los permisos y el checkpoint
externo. Se crea un **nuevo fichero** y se verifica su journal antes de
publicarlo; si el destino ya existe, el comando devuelve error y no lo toca.

Antes de emplear el fichero restaurado en producción, el operador debe
comprobar permisos, control de acceso, espacio y el procedimiento de cambio
de ruta de la aplicación. AWF no efectúa el cutover automáticamente. Conserve
el backup previo y la base anterior hasta confirmar las pruebas de servicio.

## Qué fallará expresamente

| Escenario | Resultado |
|---|---|
| Hay transacciones WAL confirmadas | Copia online coherente las incluye |
| Último checkpoint no corresponde al head | Falla; requiere nueva firma |
| Backup íntegro en SHA de eventos pero corrupto en `revision_snapshots` | Falla tras reproducir las revisiones |
| Clave revocada, firma falsa o política sin hash confiable | Falla antes de crear destino |
| Destino ocupado o coincide con fuente | Falla sin sobrescribir |
| Fallo antes del enlace de publicación | No se crea archivo final; se limpia el staging normal |
| Crash del proceso o disco, custodia externa no mantenida | No hay promesa de RPO/RTO ni recuperación automática |

Las salidas mantienen `external_custody_proven=false`, porque esa custodia no
es observable por el programa. Tampoco autorizan decisiones académicas ni
promocionan las 168 reglas históricas obligatorias.

Decisión: [ADR-0018](adr/0018-wal-aware-signed-backup-recovery.md).
