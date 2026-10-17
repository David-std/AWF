# Roadmap AWF — hitos S0–S8

El roadmap contiene criterios de salida, no fechas irreales. Un sprint se considera completo únicamente con pruebas ejecutadas, demostración y handoff actualizado. Un resultado negativo/INCONCLUSIVE de ML no requiere rehacer la arquitectura.

| Sprint | Demostración funcional | Aceptación y exclusiones |
|---|---|---|
| S0 — Fundación | `awf --version` desde instalación `uv` y ejecución CI | Ruff, pyright, pytest, build, README/AGENTS/ADR; sin secretos. La documentación inicial **no equivale a S0 completo** |
| S1 — DocumentIR | `awf ingest draft.md` produce documento estructurado y SHA | Ingesta idempotente, original byte-identical, parser probado con casos adversariales |
| S2 — Knowledge Compiler | Importar un snapshot legado y consultar reglas clasificadas | Inventario completo de 184 IDs, autoridad, duplicados, excepciones y decisión de aplicabilidad; no pérdida silenciosa |
| S3 — Verification-first | Proponer candidato dummy y verificar bytes reales/citas/cifras | Falla crítica → REJECTED, incertidumbre crítica → NEEDS_REVIEW; falsos PASS detectados |
| S4 — Baselines neuronales | Evaluar Qwen local, modelo de edición existente y baseline con prompts | Runs etiquetados ES/EN, splits por documento, hardware/performance/costos y model cards |
| S5 — Primer adaptador propio | SFT/LoRA/QLoRA con dataset autorizado y verificador | Comparación pareada vs mejor baseline; artefactos/versiones reproducibles o resultado INCONCLUSIVE |
| S6 — Preferencias y ablaciones | Comparar con/sin reglas, retrieval, SFT, y DPO condicional | Ganancia marginal con incertidumbre, negativos documentados, sin tuning contra holdout |
| S7 — Producto API | HTTP y CLI comparten casos de uso y resultados | Contratos, límites, timeouts y privacidad; documentación deployment |
| S8 — Lab detector específico opcional | Registro de observaciones en productos externos | Snapshot, idioma, scope, procedencia, sesgos y reportes separados; sin claims de evasión garantizada |

## Orden obligatorio de implementación

S0–S3 no necesitan GPU ni proveedor externo. La RTX 4050 reportada sirve como posible baseline local cuando se programe S4. No asumir que inferencia exitosa significa entrenamiento exitoso. Notebook/Google Pro puede emplearse para pilotos bajo cuotas y términos efectivos de la sesión.

## Condición para pasar a entrenamiento

Exigir: (1) datos con permiso explícito, (2) gold/holdout sellado, (3) baseline sin fine-tuning medido, (4) verificadores calibrados, (5) registro de reproducibilidad, (6) hipótesis falsable con go/no-go. No empezar DPO hasta tener pares de preferencias fiables.

## Calidad del software

En cada PR: tests positivos y negativos, revisión de licencias, diff legible, controles de regresión, salida del linter/formato/tipado, documentación del límite conocido y `docs/AGENT_HANDOFF.md` actualizado. No sobrecargar CI estándar con entrenamiento GPU.

## Alcance futuro

Aplicar ADR antes de añadir React, Supabase, microservicios, event sourcing, vector DB o motor distribuido. Cada tecnología nueva debe responder a una necesidad cuantificada y conservar contratos hexagonales.
