# S2 — Guía del checkpoint externo firmado

Este flujo detecta **truncamiento o sustitución del historial SQLite** si un
testigo ajeno a la máquina conserva de forma segura el hash **más reciente** de
un checkpoint firmado, las claves autorizadas y el hash de su política. No
afirma que un servicio externo ya exista ni que un manuscrito sea correcto.

## Qué deben conservar fuera de SQLite

1. Cada fichero de checkpoint firmado (`.json`, canonical UTF-8 con LF), en
   orden cronológico, desde la primera emisión. No subirlo con contenidos
   privados al repositorio.
2. SHA-256 del **último** fichero firmado, transmitido por un canal de
   custodia independiente de la carpeta donde están los JSON y SQLite.
3. Política de claves de custodia, con su SHA-256 distribuido por ese canal
   independiente; gestión de revocación y custodia privada de la clave Ed25519.
4. Identificador estable del ledger que figure en los grants. El custodio debe
   comprobar la legitimidad del primer snapshot antes de firmarlo: una firma
   nueva sobre un historial ya truncado **no restaura** eventos perdidos.

Política canónica, ilustrativa (hex de ejemplo, **no es una clave válida de
producción**; usar una clave real Ed25519 de 32 bytes):

```json
{"grants":[{"key_id":"witness-a","ledger_ids":["research-ledger-a"],"public_key_hex":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","revoked":false,"valid_from":1790000000,"valid_until":1900000000}],"schema":1}
```

JSON sin espacios de formato y con LF final para bytes idénticos. No colocar
jamás la clave privada en `docs/`, Git, SQLite, argumentos CLI o impresiones de
log. AWF únicamente consume claves públicas, firmas y metadatos sintéticos.

## Emitir el primer checkpoint

```shell
awf evidence verify --database .awf/evidence/ledger.sqlite
awf evidence checkpoint-propose \
  --database .awf/evidence/ledger.sqlite \
  --ledger-id research-ledger-a --key-id witness-a
```

La respuesta `CHECKPOINT_UNSIGNED_PROPOSAL` contiene `claim` y
`signing_message_hex`. Un **firmante externo** valida su contexto y firma los
bytes exactos decodificados de `signing_message_hex` con Ed25519; después
construye `SignedLedgerCheckpoint(claim, signature_hex).to_bytes()` con la API
del paquete. El prefijo `AWF/ledger-checkpoint/v1\x00` es parte obligatoria
del mensaje; firmar solo el JSON o su hash sin el prefijo falla. AWF **no**
almacena la clave de custodia ni firma la propuesta.

Tras custodiar de verdad el fichero, el testigo publica el SHA-256 del fichero
firmado por un canal diferente de donde reside el fichero. El operador obtiene
también el SHA-256 de la política por ese canal; no los sustituye con un hash
recién calculado de los mismos ficheros no confiables.

## Comprobarlo antes de recuperar o usar resultados

```shell
awf evidence checkpoint-verify /ruta/privada/checkpoint_001.json \
  --database .awf/evidence/ledger.sqlite \
  --expected-checkpoint-sha256 HASH_CONFIABLE_001 \
  --policy-file /ruta/privada/custodios.json \
  --expected-policy-sha256 HASH_POLITICA_CONFIABLE \
  --require-current-head
```

`--require-current-head` exige que no existan anexos posteriores. Sin ese flag,
un checkpoint de prefijo histórico **puede seguir siendo válido** después de
que crezca el ledger; la salida indica `checkpoint_is_current_head=false`.
En ambos modos el resultado conserva `external_custody_proven=false`, ya que
el programa no ve al testigo. Si faltan el hash o la política externos, el
comando falla cerrado.

## Checkpoints sucesivos y rotación

Para una segunda emisión con al menos un evento nuevo:

```shell
awf evidence checkpoint-propose \
  --database .awf/evidence/ledger.sqlite \
  --ledger-id research-ledger-a --key-id witness-a \
  --previous-file /ruta/privada/checkpoint_001.json \
  --expected-previous-sha256 HASH_CONFIABLE_001 \
  --policy-file /ruta/privada/custodios.json \
  --expected-policy-sha256 HASH_POLITICA_CONFIABLE
```

Para un tercero, añadir `--history-file checkpoint_001.json` (y poner
`checkpoint_002.json` en `--previous-file`). Para verificar el tercero,
especificar los ancestros **en orden**:

```shell
awf evidence checkpoint-verify /ruta/privada/checkpoint_003.json \
  --history-file /ruta/privada/checkpoint_001.json \
  --history-file /ruta/privada/checkpoint_002.json \
  --database .awf/evidence/ledger.sqlite \
  --expected-checkpoint-sha256 HASH_CONFIABLE_003 \
  --policy-file /ruta/privada/custodios.json \
  --expected-policy-sha256 HASH_POLITICA_CONFIABLE
```

No se permite omitir eslabones, repetir secuencias ni retroceder en tiempo de
emisión. En la política actual la revocación invalida retrospectivamente las
verificaciones de toda la cadena que use esa clave; una política de rotación
institucional versionada aún no está diseñada. La cadena admite hasta 1024
eslabones; para más se necesita un nuevo ADR de anclajes de época.

## Semántica de aceptación y límites

| Situación | Resultado esperado |
|---|---|
| Registro acortado, hash local coherente | `CHECKPOINT_FAILED` contra el checkpoint más reciente |
| Mismo número de eventos con bytes alterados | `CHECKPOINT_FAILED` por prefijo incorrecto |
| Clave revocada/ajena, firma falsa, política sustituta | `CHECKPOINT_FAILED` |
| Pérdida del último hash externo, pero fichero antiguo válido | **No es detectable el rollback a esa versión antigua** |
| Nueva append después de la firma | Prefijo válido; no se afirma head actual |
| Firma válida de operador autorizado | Integridad de prefijo; **no** identidad civil ni validez académica |

Ninguna salida promueve automáticamente los 168 `MUST` a `REVIEW_ATTESTED` ni
habilita entrenamiento. Para copiar SQLite con escrituras concurrentes se
usará el respaldo transaccional oficial de SQLite en un incremento distinto;
copiar el `.db` aislado de los archivos WAL **no** es un protocolo de backup.

Implementación: `domain/checkpoints.py`, `application/commands/checkpoints.py`,
`EvidenceStorePort.verify_anchors`, `SQLiteEvidenceLedger.verify_anchors` y
`tests/integration/test_signed_checkpoints.py`. Decisión: [ADR-0017](adr/0017-externally-signed-ledger-checkpoints.md).
