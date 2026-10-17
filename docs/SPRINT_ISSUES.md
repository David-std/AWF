# Issues por sprint y estado de entrega

Registro remoto creado en el repositorio `David-std/AWF`. Es la lista autorizada de tareas de desarrollo; **crear un issue no demuestra implementación**.

| Sprint | Issue | Estado inicial |
|---|---|---|
| S0 — Paquete, CLI, quality gates, CI | [#1](https://github.com/David-std/AWF/issues/1) | OPEN |
| S1 — DocumentIR, ingesta y originales inmutables | [#2](https://github.com/David-std/AWF/issues/2) | OPEN |
| S2 — Knowledge compiler de AWS 3.19.1 | [#3](https://github.com/David-std/AWF/issues/3) | OPEN |
| S3 — Verificación independiente y errores críticos | [#4](https://github.com/David-std/AWF/issues/4) | OPEN |
| S4 — Baselines Qwen/modelos de edición en ES/EN | [#5](https://github.com/David-std/AWF/issues/5) | OPEN |
| S5 — Entrenamiento de adaptador SFT/QLoRA | [#6](https://github.com/David-std/AWF/issues/6) | OPEN |
| S6 — Ablaciones y DPO condicional | [#7](https://github.com/David-std/AWF/issues/7) | OPEN |
| S7 — API y despliegue | [#8](https://github.com/David-std/AWF/issues/8) | OPEN |
| S8 — Investigación de detectores opcional | [#9](https://github.com/David-std/AWF/issues/9) | OPEN |

## PR de arquitectura

[PR #10](https://github.com/David-std/AWF/pull/10): diseño y trazabilidad v0.1, en revisión (draft al crearse). Su merge no cierra S0: S0 exige código real, tests y CI.

## Criterios antes de cerrar un issue

Actualizar archivos y pruebas, realizar demostración del comportamiento indicado, registrar hash de commit y enlazar la evidencia en el issue/PR. Los tests que no se ejecutaron deben decir `NOT_RUN`. Si un benchmark no mejora, el issue puede concluir con resultado negativo documentado sin falsificar la métrica.

Priorizar secuencia y dependencias antes que velocidad. No imponer un plazo ficticio a entrenamiento ni comprar GPU mientras falte benchmark.
