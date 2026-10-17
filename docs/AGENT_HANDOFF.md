# AWF — estado de transferencia

Actualizado: 2026-10-17. Este registro debe actualizarse en **cada** PR de implementación o cambio de arquitectura. Ver plantilla `docs/templates/AGENT_HANDOFF_TEMPLATE.md`.

## Estado

- **Sprint actual:** S0 — documentación de preparación; trabajo de software pendiente.
- **Repositorio:** https://github.com/David-std/AWF
- **Rama documental:** `docs/architecture-baseline-v0.1`; no confundir PR abierto con cambios fusionados a `main`.
- **Último commit verificado en main al preparar el baseline:** `a902135b80e96eea17ebb9c229eed065077e809d`.
- **Baseline de especificación:** `docs/architecture/ARCHITECTURE_SPEC_0_1.md` (679 líneas).
- **Producto:** no hay todavía CLI, runtime AWF, modelo ajustado, endpoints, pruebas automatizadas ni benchmark implementados. Los scripts de la especificación son interfaces **previstas**.
- **Fuente histórica AWS:** ZIP 3.19.1 externo, sha256 `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`, no versionado como código del repositorio.
- **Equipo:** usuario confirmó GPU RTX 4050 con inferencia Qwen local exitosa; menciona Google AI Pro/Notebook. VRAM, acceso efectivo GPU, cuota y políticas siguen por comprobar.

## Qué se entregó en este cambio

Documentación completa de arquitectura propuesta, decisiones iniciales, fuente histórica, requerimientos, sprints, laboratorio de ML, bibliografía/evidencia y guía de agentes. Se evitó crear un andamiaje de software fingiendo funcionalidades.

## Qué verificar antes del siguiente cambio

1. Consultar el último commit de main y el estado del PR documental.
2. Revisar `AGENTS.md`, `docs/architecture/ARCHITECTURE_SPEC_0_1.md`, `docs/architecture/DECISIONS_LOCK.yaml` y `docs/REQUIREMENT_TRACEABILITY.md`.
3. Confirmar autorización de código/límites de licencia antes de importar fuentes antiguas.
4. Iniciar S0 con el menor corte demostrable: `pyproject.toml` + paquete `src/awf` + `awf --version` + pruebas + CI, siguiendo el blueprint.
5. Después ejecutar pruebas reales y registrar comandos/salidas exactos. Sin hardware de pago ni modelo entrenado todavía.

## Cambio de estado obligatorio al finalizar un sprint

Rellenar: `current_sprint`, `head_commit`, `changed_files`, `features_verified`, `commands_and_results`, `open_failures`, `new_ADRs`, `risk_and_licensing`, `next_smallest_testable_step`. Si una prueba no se ha ejecutado, registrar `NOT_RUN`.

**Siguiente paso mínimo:** issue S0, empaquetado Python/uv y CLI real con versión; ningún uso de Qwen implica que ya se haya entrenado AWF.
