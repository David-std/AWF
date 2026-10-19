# S2 — Contrato de autorización de evaluadores

Esta función **autentica una firma frente a una clave permitida por una
política explícita** y verifica que la atestación corresponde a un evento local
exacto. **No demuestra** que una persona sea quien declara ser, que sea
independiente, que una fuente sea correcta o que el sistema haya comprendido
la lectura. Sprint 2 y las 168 reglas `MUST` permanecen abiertos.

## Autoridad y custodia

El operador distribuye por un canal confiable un hash SHA-256 de una política
JSON canónica, independiente tanto de `--policy-file` como de SQLite. Una
política contiene como máximo 128 grants y esta forma (identificadores y claves
de ejemplo; `public_key_hex` debe ser una clave Ed25519 real de 32 bytes):

```json
{"grants":[{"actor_id":"critic-a","key_id":"key-a","public_key_hex":"<64 lowercase hexadecimal characters>","revoked":false,"roles":["AUDITOR"],"runs":["run-1"],"subjects":["p1:claims"],"valid_from":1790000000,"valid_until":1900000000}],"schema":1}
```

El JSON efectivo no acepta espacios de formato, campos extra ni claves
duplicadas. Debe terminar con una nueva línea LF. El digest externo nunca
debe obtenerse simplemente leyendo la misma política que se va a verificar:
eso no establece una raíz de confianza. Las claves privadas pertenecen al
firmante y **no** deben copiarse a este repositorio ni almacenarse en SQLite.

## Flujo para una auditoría

1. Registrar el recibo ordinario `AUDIT_RECEIPT` en el ledger o journal.
   Recuperar su `EvidenceRecord` y digest `event:<64hex>`.
2. Construir `ReviewerClaim(actor_id, key_id, role=ReviewerRole.AUDITOR,
   run_id, subject_id, target_event_ref, issued_at)` para **ese evento**.
   El evaluador firma `claim.signing_bytes` con su clave privada fuera de AWF.
   Entregar solamente `SignedReviewerClaim(claim, signature_hex).to_bytes()`.
3. Admitir ese archivo en local si la política externa permite exactamente
   actor, clave, rol, run, sujeto y momento:

```shell
awf evidence attest signed_review.json --database .awf/evidence/ledger.sqlite \
  --policy-file /ruta/privada/trusted_reviewers.json \
  --expected-policy-sha256 <hash-confiable-desde-otro-canal>
```

4. Conservar el `attestation_ref` producido, distinto del evento objetivo.
   Recuperar y verificar de nuevo, idealmente con `--expected-head` guardado
   fuera de SQLite:

```shell
awf evidence attest-verify --database .awf/evidence/ledger.sqlite \
  --policy-file /ruta/privada/trusted_reviewers.json \
  --expected-policy-sha256 <hash-confiable-desde-otro-canal> \
  --attestation-ref event:<digest-firmado> --target-ref event:<digest-audit> \
  --role AUDITOR --run-id run-1 --subject-id p1:claims
```

5. Para todas las auditorías de un `RevisionState`, invocar el gate
   `verify_authorized_audit_receipts` con un inventario completo
   `dict[receipt.evidence_ref, attestation_ref]`. Para progreso de conocimiento,
   usar `verify_authorized_knowledge_progress`; las etapas `UNDERSTOOD` y
   `APPLICABLE` exigen roles `CALIBRATOR` y `APPLICABILITY_REVIEWER`, además de
   la verificación previa del registro y cobertura READ.

## Semántica de fallos

- Permiso revocado/vencido o clave desconocida: **no autorizado**.
- Firma, tipo, run, sujeto, bytes o referencia incorrectos: **no autorizado**.
- Política sin anclaje correcto, JSON ambiguo, fuente ausente: **error**.
- Evidencia local correcta pero sin firma: **integridad local sí, autorización no**.
- Firma y permiso correctos: `authorization_verified=true` **sin** juicio
  científico. `independent_adjudication_proven=false` siempre.
- Reloj de sistema manipulado, clave robada, dos claves de la misma persona,
  operador de confianza comprometido: fuera de la garantía del prototipo.

Las atestaciones no convierten a `REVIEW_ATTESTED` ninguna entrada histórica
del corpus AWS 3.19.1; la identidad/independencia real y un checkpoint externo
firmado siguen pendientes. Consultar [ADR-0016](adr/0016-signed-reviewer-authorization.md).
