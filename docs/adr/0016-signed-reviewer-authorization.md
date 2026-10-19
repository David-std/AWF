# ADR-0016 — Autorización de revisores con firma separada del juicio académico

- **Estado:** prototipo S2 verificable; no demuestra independencia real ni certifica una revisión.
- **Fecha:** 2026-10-19 (UTC).
- **Contexto:** ADR-0010–0015, rama `develop` tras PR #21.

## Problema

Los recibos de `AUDIT_RECEIPT`, `CALIBRATION_JUDGMENT` y `REVIEW_DECISION`
acreditan únicamente el registro local. El `run_id`, `subject_id` y el campo
`observation_ref` proceden de declaraciones del llamante: alguien con acceso
al almacén puede presentarse como evaluador o reutilizar el mismo recibo en
otro contexto. Incluso la atomicidad de las revisiones no autentica una
decisión humana.

## Decisión

1. Introducir un contrato de dominio puro `ReviewerClaim` con versión,
   `actor_id`, `key_id`, rol, `run_id`, `subject_id`, `target_event_ref` e instante
   UTC numérico. La firma Ed25519 cubre los **bytes JSON canónicos** de ese
   contrato, con prefijo de separación de dominio `AWF/reviewer-authorization/v1`.
   No se firman hashes de contenido sin contexto ni mensajes transformables.
2. El adaptador criptográfico es `Ed25519ReviewerVerifier` sobre la biblioteca
   mantenida `cryptography` (dependencia normal fijada en `uv.lock`), detrás de
   `ReviewerSignatureVerifierPort`. AWF no genera ni almacena claves privadas
   de evaluadores en esta función. La validez de firma se comprueba al anexar
   **y** en cada lectura autorizada; no se confía en un booleano persistido.
3. Se exige `ReviewerTrustPolicy` con grants explícitos de actor/clave, roles,
   ejecuciones, sujetos exactos, intervalo de vigencia y revocación. El texto
   canónico de esa política se compara con un SHA-256 aportado **por un canal
   independiente** del fichero y de la base SQLite. No calcular el digest del
   propio fichero al invocar la aplicación y llamarlo «anclaje externo».
4. Los roles admitidos son `AUDITOR → AUDIT_RECEIPT`,
   `CALIBRATOR → CALIBRATION_JUDGMENT` y
   `APPLICABILITY_REVIEWER → REVIEW_DECISION`. Una misma clave **no** hereda
   roles diferentes. La firma se ata al evento concreto `event:<digest>`;
   además se verifica su tipo, run, sujeto y orden anterior a la atestación.
5. `REVIEW_ATTESTATION` es un evento nuevo, aditivo, en el mismo ledger; no
   altera los esquemas ni reescribe los eventos anteriores. `awf evidence
   attest` solo acepta una atestación previamente validada y el comando de
   verificación vuelve a cargar las fuentes y firma actuales. El comando
   genérico `evidence append` no expone este tipo como opción de usuario.
6. Se ofrecen gates de aplicación sobre recibos de auditoría y sobre las etapas
   de conocimiento adjudicadas. Ambos ejecutan antes los **gates de integridad
   existentes**; solo devuelven `authorization_verified` cuando hay una
   atestación correcta para cada evento requerido. La salida
   `independent_adjudication_proven` **siempre permanece `False`**.

## Alternativas

| Opción | Razón para no elegirla |
|---|---|
| `actor_id` suministrado por el cliente | Una cadena editable no autentica al evaluador |
| HMAC con secreto compartido | Todos los poseedores del secreto pueden hacerse pasar por los demás; no hay firma asimétrica |
| Claves privadas en SQLite/configuración AWF | El dispositivo podría falsificar atestados de todas las identidades |
| Certificado X.509/PKI y servicio externo ahora | No existe aún operador/PKI ni necesidad de complejidad remota S2 |
| Ed25519 + allowlist externa fijada | Elegida: prueba de posesión de clave y permiso explícito, sin pretensión de identidad civil o independencia científica |

## Amenazas comprobadas y residuales

- Se rechazan firma alterada, claves desconocidas, revocadas o vencidas,
  rol equivocado, ejecución/sujeto/evento sustituido, firma para otro evento,
  inventario incompleto, política reemplazada, JSON no canónico/campos duplicados,
  atestado previo al evento y bytes persistidos inconsistentes.
- **La política y su digest deben custodiarse fuera de SQLite**; si un atacante
  controla además el digest esperado o las claves privadas, esta garantía se
  pierde. Los nombres de actor identifican una clave en la política, no una
  persona civil o una institución verificada.
- La hora es la proporcionada por el llamante (reloj local en CLI): no hay
  autoridad de sellado temporal. La revocación vigente invalida verificaciones
  retrospectivas por diseño conservador. Falta un protocolo de versionado
  histórico de grants y de gestión de claves (alta/rotación/compromiso).
- No se comprueba que dos claves pertenezcan a personas distintas, que la
  revisión haya sido ciega, o que el criterio académico sea verdadero. Tampoco
  se autentica por defecto el journal anterior: debe solicitarse **este gate**
  por separado. Los barridos críticos y la aceptación final siguen pendientes.
- El coste de verificación aún incluye recorrido completo del ledger por cada
  referencia; optimización por lote y checkpoint firmado quedan para otro ADR.

## Compatibilidad y aceptación

Se preserva lectura de evidencia y snapshots S2 anteriores. El nuevo tipo de
evento se admite por enum sin migración destructiva. Los recibos históricos sin
firma **no** reciben autorización implícita. Pruebas sintéticas de roundtrip
con reinicio, firma falseada, roles/tiempos, adulteración de estado, swapping,
revocación y CLI multiplataforma; ninguna clave privada o corpus histórico se
publica. Ver [guía de autorización](../REVIEWER_AUTH_S2.md).

Implementación Ed25519 según la [documentación del proyecto
cryptography](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ed25519/).
