# ADR-0022 — Barridos críticos e iteraciones externas recuperables

- Estado: aceptada para prototipo local Sprint 2; sin certificación académica.
- Fecha: 2026-10-20 (UTC).
- Base: `develop` `96fd77f` después de PR #28; ADR-0010/0014/0015/0018/0021.

## Problema

El dominio podía registrar `CleanSweep` e iteraciones externas en memoria, pero
`SQLiteRevisionJournal` solo coordinaba `START`, `AUDIT`, `EDIT`, `FINDING_OPEN`
y `FINDING_RESOLVE`. Un reinicio después de evaluar a un crítico perdía el
conteo de barridos y los límites de iteración o invitaba a inventar el estado
desde narrativas externas. La mera existencia de un digest de observación no
identifica su clase, ejecución, revisión ni oportunidad causal.

## Decisión

1. Incorporar `CLEAN_SWEEP` y `EXTERNAL_ITERATION` como tipos de intención del
   esquema 2 existente, sin migrar ni reinterpretar snapshots previos. Cada
   operación usa `BEGIN IMMEDIATE`, auditoría íntegra del ledger, versión
   esperada, ID idempotente, evento de intención, nuevo estado inmutable y
   evento de commit en **una transacción**.
2. Exigir eventos de observación explícitos en el mismo ledger: tipos
   `CRITIC_OBSERVATION`, `CRITIC_CONTEXT` y
   `EXTERNAL_ITERATION_OBSERVATION`. Su `run_id` y `subject_id` deben coincidir
   con los de la revisión. Sus secuencias deben ser posteriores al commit de
   la versión anterior y anteriores a la nueva intención; se rechaza el
   intercambio de referencias entre clases, ejecuciones, revisiones y ciclos.
3. Congelar `policy`, documento SHA-256, huella de DocumentIR y fingerprints
   de cada scope dentro de la intención del barrido. En escritura, ejecutar
   `add_clean_sweep` con el **documento real**. En recuperación, reproducir
   el gate a partir de los scopes guardados y los recibos inmutables del
   estado anterior, sin necesitar texto confidencial. Comprobar igualdad
   completa del estado reconstruido y del snapshot.
4. Mantener critic ID distinto, referencia de contexto distinta, ausencia de
   diagnóstico heredado, inventario no vacío, auditorías actuales completas,
   ausencia de hallazgo material abierto y presupuesto disponible. La
   iteración externa solo incrementa su contador si el presupuesto lo permite.
5. Mantener la distinción entre `CONVERGED` **local** y aceptación científica.
   Estas referencias verifican procedencia local de eventos, no autoría,
   independencia real, veracidad del contenido ni autoridad de un revisor.
   Una política de firmas y verificación externa sigue siendo necesaria.

## Compatibilidad y recuperación

Los estados anteriores (`START/AUDIT` esquema 1 y los tipos previos del esquema
2) siguen siendo legibles. No se añade una columna ni se modifica el DDL del
journal. Una respuesta perdida se reproduce por `operation_id` y huella de
solicitud aun si el cliente usa una versión antigua; una clave reutilizada con
otro payload provoca conflicto. Si ocurre una excepción antes de `COMMIT`, no
quedan intención ni snapshot huérfanos. La auditoría de evidencias y el replay
causal completo son obligatorios incluso cuando el cliente solo consulta.

## Alternativas no escogidas

| Alternativa | Motivo |
|---|---|
| Conservar contadores fuera de SQLite | Riesgo de divergencia/crash entre evidencia y estado |
| Declarar evidencias como cadenas arbitrarias | No permite validar run, tipo, revisión ni secuencia |
| Considerar IDs de críticos prueba de independencia | La identidad textual se puede autodeclarar |
| Persistir texto completo del manuscrito para el replay | Exposición innecesaria; bastan hashes vinculados al estado previo |
| Saltarse replay bajo snapshots «firmados» | No demuestra transición de dominio válida |

## Pruebas y límites

`tests/integration/test_durable_critic_transitions.py` cubre reinicios,
reintentos, CAS concurrente, pérdida de respuesta, rollback por error, contexto
reutilizado, evidencia antigua o de run/revisión/tipo distinto, documento
modificado, hallazgo material, inventario sucio y agotamiento de presupuesto.
Las condiciones de corrupción de DDL, ledger y snapshots ya se cubren en los
tests anteriores del journal y las copias verificadas. No se han realizado
ensayos de pérdida física de energía ni atestaciones de críticos externos.

Trazabilidad: AWF-R031. Sprint 2 **permanece abierto**; 0/168 `MUST` históricos
adjudicados, 16 `DEFERRED_LAB` limitados a `EVAL_ONLY`.
