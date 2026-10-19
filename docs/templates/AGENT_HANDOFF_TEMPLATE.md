# AWF — Plantilla de transferencia a otro agente / conversación

**Estado de partida:** Documento de arquitectura 0.1, NO es un repositorio implementado. No afirmar que existen archivos o comandos hasta que se hayan creado y probado.

## Leer antes de modificar

1. `ARCHITECTURE_SPEC_0_1.md` completo.
2. `DECISIONS_LOCK.yaml` para decisiones iniciales y temas abiertos.
3. Cuando exista repo: `AGENTS.md`, `docs/AGENT_HANDOFF.md`, ADR afectados y `docs/REQUIREMENT_TRACEABILITY.md`.
4. Solo cuando sea necesario, el AWS 3.19.1 original. Nunca usarlo como autoridad de ejecución del nuevo motor sin clasificación de reglas.

## Estado de implementación

```yaml
current_sprint: S0_NOT_STARTED
last_good_commit: null
feature_completed: []
changed_files: []
test_commands_executed: []
test_results: []
new_adrs: []
missing_licenses: []
blocking_issues: []
next_smallest_testable_step: initialize repository with Python packaging, CI, CLI version and immutable baseline manifest
```

## Reglas de colaboración

- Ninguna modificación arquitectónica sin ADR que registre problema, alternativas, evidencia, consecuencias y reversión.
- No convertir reglas textuales en regular expressions sin test de positivos, falsos positivos y contraejemplos.
- Los nuevos modelos proponen; código y evaluación externa verifican. UNKNOWN crítico nunca autoaceptado.
- Detectors son un laboratorio separado. Resultados anteriores no demuestran transferibilidad a otro snapshot/idioma.
- Si se acaba la ventana de contexto, continuar desde el último commit y el handoff, no desde una reconstrucción de memoria.