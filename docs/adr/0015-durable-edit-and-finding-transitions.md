# ADR-0015 — Ediciones y hallazgos durables con replay tipado

- Estado: aceptada para prototipo S2, sin autoridad de certificación académica.
- Fecha: 2026-10-18.
- Base: ADR-0010–0014; PR #19 `feat/s2-atomic-revision-journal`.

## Problema

ADR-0014 permite confirmar `START` y `AUDIT` con el registro de evidencias,
pero las operaciones puras `accept_edit`, `open_finding` y `resolve_finding`
seguían en memoria. Una interrupción podía recuperar un estado anterior sin
la invalidación de auditorías o sin un hallazgo material y su resolución.

## Decisión

1. Añadir al mismo `SQLiteRevisionJournal` comandos tipados de edición,
   apertura y resolución de hallazgos. Se reutilizan el fichero SQLite, el
   `BEGIN IMMEDIATE`, las claves idempotentes y la versión esperada.
2. Registrar un evento de intención (`REVISION_TRANSITION`,
   `type=revision_intent`), otro de commit (`type=revision_commit`) y el
   snapshot inmutable **en una sola transacción**. Los estados enlazan la
   intención mediante su evento `event:<digest>` y no solo por hash de bytes.
   La referencia observacional original es una declaración local: no es firma
   ni identidad/autorización comprobada.
3. Conservar exactamente el `revision_commit` esquema 1 para `START/AUDIT`.
   Los nuevos commits usan esquema 2, con tipo de operación y vínculo a
   intención. No cambiar `user_version=1` ni reescribir eventos históricos.
4. En ediciones registrar hashes de ambos documentos, huellas de sus IR y
   fingerprints de todos los scopes del inventario original, sin incorporar
   manuscritos completos al snapshot. El dominio comparte una única rutina
   pura para ejecutar y reproducir la invalidación. `DOCUMENT` queda sucio
   al cambiar bytes; `LOCAL_NEIGHBORS` solo se arrastra si sus dependencias
   conservan el mismo fingerprint. El hallazgo abierto sobrevive a editar;
   los barridos críticos no sobreviven.
5. Resolver un hallazgo requiere ID existente en estado `OPEN`; preservar el
   recibo de apertura y registrar por separado el de resolución. Rechazar
   IDs repetidos, tipos incorrectos, versiones obsoletas y observación vacía.
6. En la recuperación verificar todos los eventos, su correspondencia con
   cada snapshot, run/operación, hash de solicitud y reproducción del dominio
   contra el estado anterior. Comprobar también el **orden temporal** dentro
   del ledger: recibo de auditoría o intención posterior al commit previo y
   anterior a su propio commit. No aceptar un recibo preexistente, aunque
   todos los hashes y metadatos coincidan. Intención sin commit/snapshot
   bloquea el acceso.

## Alternativas y consecuencias

| Alternativa | Evaluación |
|---|---|
| Estado JSON separado | Requiere reconciliar dos recursos tras crash |
| Evento escrito antes del estado | Deja evidencia huérfana al fallar |
| Texto completo en cada snapshot | Repite contenido sensible, costo innecesario |
| Solo snapshot y tipo nuevo | No permite contrastar la causa y su semántica |
| Intención, commit y snapshot transaccionales | Elegida: replay tipado compatible |

## Límites

- Las huellas se computan desde un `DocumentIR` de entrada. El journal **no**
  verifica por sí solo los bytes reales que originaron el IR ni custodia los
  manuscritos. Se necesita el flujo independiente de ingesta y almacenamiento.
- La cadena de hashes acredita integridad local relativa a un checkpoint,
  no verdad científica, autorización editorial ni identidad del observador.
  Faltan firmas/checkpoints externos y gestión de roles.
- `add_clean_sweep`, `record_external_iteration` y la aceptación final
  no tienen comando durable. Ningún resultado nuevo certifica `CONVERGED`
  ni adjudica las 168 reglas `MUST` de AWS 3.19.1.
- Se conserva lectura de toda la cadena O(historial); faltan benchmark y
  pruebas de backup/restore del dispositivo del usuario.
- El ZIP histórico, sus reglas y los manuscritos reales continúan solo localmente.

## Evidencia de aceptación

Pruebas sintéticas de invalidación global/local y vecinos, persistencia de
hallazgos durante edición, resolución explícita y auditoría nueva; reinicio,
replay, claves reutilizadas, presupuesto, carrera de dos escritores, caída
abrupta posterior a la intención, rollback por trigger e intención huérfana.
Se prueba además el rechazo de un recibo válido generado antes de crear la
revisión, indebidamente reutilizado en un commit posterior.
CI multiplataforma y revisión independiente permanecen como condiciones de
cierre técnico, no de certificación académica.
