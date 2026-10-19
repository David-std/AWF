# ADR-0017 — Anclaje externo firmado de prefijos del ledger S2

- **Estado:** prototipo S2, sin operador externo integrado ni sellado temporal confiable.
- **Fecha:** 2026-10-19 (UTC).
- **Base:** ADR-0012, ADR-0014, ADR-0016, `develop` después de PR #22.

## Contexto y amenaza

Un adversario que reemplace toda la base SQLite puede dejar una cadena de
SHA-256 internamente válida después de truncar los últimos eventos o generar
un historial alternativo. `evidence verify` no detecta este ataque sin un hash
auténtico previamente custodiado. Los recibos firmados de PR #22 autorizan
declaraciones de evaluador **dentro** de un ledger, no garantizan que el ledger
contenga el historial anterior completo.

## Decisión

1. `CheckpointClaim` declara `schema=1`, `ledger_id` asignado por operador,
   `key_id`, SHA-256 del evento final, cantidad exacta de eventos, instante
   de emisión y SHA-256 del **checkpoint firmado** previo. Su firma Ed25519
   cubre los bytes canónicos del payload y el prefijo específico
   `AWF/ledger-checkpoint/v1\x00`. No se reutiliza el dominio de firmas de
   revisores.
2. El permiso para custodiar un ledger es distinto de los roles académicos:
   `CheckpointTrustPolicy` admite hasta 32 claves independientes con listas
   exactas de `ledger_ids`, vigencia y revocación. El SHA-256 de la política
   llega por un canal ajeno a SQLite y al propio fichero de política.
3. El verificador recibe también el SHA-256 **del fichero firmado** de
   checkpoint procedente de un testigo independiente. Compara hash, firma,
   permisos actuales, identidad del ledger, orden, continuidad y todos los
   checkpoints intermedios **desde la primera emisión**. No interpreta un
   hash calculado del fichero a validar como certificación externa.
4. `EvidenceStorePort.verify_anchors` y `SQLiteEvidenceLedger.verify_anchors`
   recorren hashes, bytes, objetos, triggers y esquema; luego contrastan
   todos los pares `(sequence, digest)` **en una misma transacción de lectura**.
   Evita mezclar la vista de un prefijo y el head si otro proceso anexa eventos.
   La política permite anexos honestos posteriores; opcionalmente se exige
   `require_current_head` si el flujo necesita un head actual exacto.
5. `awf evidence checkpoint-propose` **solo propone** un claim desde eventos
   comprobados y no firma ni publica. Para enlazar una propuesta exige fichero
   anterior, su digest independiente, política, su digest independiente y
   todos los ficheros anteriores. `checkpoint-verify` vuelve a revisar esos
   datos y emite `external_custody_proven=false`: el programa no puede
   observar si el operador protegió realmente los hashes o claves externos.
6. Reutilizar `Ed25519Verifier` y JSON canónico estrictamente validado es
   apropiado; crear una segunda implementación de Ed25519/canonicalización
   aumentaría superficie de error. Se conservan los nombres publicados de
   PR #22 como aliases compatibles. No se añade esquema ni evento nuevo.

## Alternativas y consecuencias

| Alternativa | Motivo |
|---|---|
| Hash del head registrado únicamente en la misma SQLite | Atacante puede reemplazar ambos |
| Hash local exportado sin custodia verificable | Solo evidencia un valor editable por el mismo actor |
| Guardar clave privada o firma automática en la base | El atacante también puede falsificar nuevos checkpoints |
| Servicio central de transparencia, RFC3161 o PKI institucional | No existe operador ni SLA/credenciales S2, se difiere la integración |
| Claims firmados externamente con lista SHA-pinned | Elegida; contrato comprobable y sin proveedor obligatorio |

## Pruebas de aceptación

- SQLite histórico sustituido por copia truncada mediante `Connection.backup`
  sigue verificando internamente, pero **falla** frente al checkpoint posterior.
- Historial reconstruido con el mismo número de eventos y otros bytes falla.
- Firma, hash externo, clave, ledger, rol de custodia, validez, revocación,
  bytes JSON, versión, sujeto de cadena y enlaces maliciosos fallan.
- Cadena de tres checkpoints y propuesta del cuarto con historia obligatoria;
  falta de ancestría, secuencia igual/regresiva, tiempo regresivo fallan.
- Auditoría de head y prefijos en una sola instantánea SQLite; reabrir la
  base y continuar anexando preserva la validez de un prefijo histórico.

## Riesgos excluidos y migración

- Identificador de ledger es una etiqueta de confianza de la política, no una
  identidad física del dispositivo. Copias idénticas de un ledger representan
  el mismo prefijo histórico.
- La firma no prueba dónde se almacenó el fichero, frescura real de un
  testigo ni hora certificada. Sin **último** hash custodiado externamente, un
  atacante puede presentar un checkpoint anterior auténtico y su copia vieja.
- Un custodio comprometido puede firmar una cadena falsa. El modelo de
  revocación es conservador: revocar una clave invalida la verificación actual
  de checkpoints anteriores firmados por ella; rotación con historia histórica
  institucional necesita protocolo de confianza versionado y validado.
- Se exige historia completa desde el primer checkpoint, máximo 1024 por
  operación; superar ese límite requiere protocolo de agregación/anclaje de
  época en un ADR posterior. No introducir un reinicio silencioso de linaje.
- No se automatiza sincronización con S3 externo, TSP, backups/restores,
  barridos críticos, valoración científica, derechos de corpus ni revisión
  humana. Ninguna de las 168 reglas `MUST` queda adjudicada por este ADR.

Ver [guía de uso S2](../SIGNED_CHECKPOINTS_S2.md).
