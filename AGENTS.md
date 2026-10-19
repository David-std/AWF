# AWF — instrucciones para agentes y colaboradores

Este archivo controla la **forma de trabajar** en David-std/AWF. No sustituye la especificación. Estado actual: prototipos S0–S2 en PR apiladas; hay CLI, ingesta, registros y puertas de auditoría, pero no editor neuronal ni verificador independiente completo. Comprobar el estado exacto en `docs/AGENT_HANDOFF.md`.

## Lectura obligatoria y precedencia

1. Revisar `README.md` y `docs/AGENT_HANDOFF.md` para reconocer sprint/commit.
2. Leer **completa** `docs/architecture/ARCHITECTURE_SPEC_0_1.md` antes de decisiones arquitectónicas o de estructura. Sus ADR son *propuestas basales*, no pruebas de software existente.
3. Leer `docs/architecture/DECISIONS_LOCK.yaml`, `docs/REQUIREMENT_TRACEABILITY.md` y los ADR específicos cuando se modifique su ámbito.
4. Consultar `docs/SOURCE_REGISTRY.md` para separar fuentes primarias, artículos, afirmaciones comerciales e hipótesis.
5. Comprobar el repositorio y ejecutar las pruebas que realmente existan. Documentar resultados reales, no comandos planeados.
6. Si un contrato nuevo contradice la especificación, crear ADR justificando evidencia, alternativas, consecuencias y migración antes de desplazar el contrato.

La suite AWS 3.19.1 es **origen histórico de conocimientos**, no autoridad de runtime de AWF. Ver `docs/PROVENANCE.md`.

## Arquitectura y límites

- Monolito modular Python 3.12; puertos/adaptadores hexagonales y comandos/consultas ligeros; evitar microservicios y doble base de datos sin métricas que lo justifiquen.
- `domain` no importa FastAPI, torch, Transformers, SQLAlchemy, Docling ni implementaciones concretas; puertos y casos de uso separan efectos secundarios.
- Modelos generan **candidatos**, no atestados que se acepten por sí solos. Un `FAIL` crítico rechaza; `UNKNOWN` crítico requiere revisión y bloquea aceptación automática.
- Documentos originales son inmutables; hashes medidos sobre bytes reales; salida derivada con versionado y linaje.
- Una regla puede ser determinista, probabilística, contextual, contradictoria o inaplicable. No convertir las 184 reglas heredadas a `if` ni a prompts sin clasificación y test.
- Desconocer el veredicto es un estado explícito; jamás convertir excepción de NLI/API/parseo en `PASS`.
- Preservar originales, casos adversariales, observaciones negativas, autoría/licencias y experimentos fallidos; prohibida la limpieza destructiva.
- Idiomas español/inglés, snapshot de modelo/detector, scope y grupo documental siempre identificados en evaluaciones.

## Higiene de implementación

- Crear únicamente archivos del sprint activo con responsabilidad comprobable; no generar módulos vacíos como decoración.
- Convenciones: `snake_case` en módulos/funciones, `PascalCase` en clases, `UPPER_SNAKE_CASE` en constantes, tipado, UTF-8/LF, línea final, longitud 100 formateada por Ruff.
- En Sprint 0 introducir `uv`, `ruff`, `pyright`, `pytest`, `hypothesis` y CI; no proclamar PASS antes de ejecutarlos.
- Tests con negativos de seguridad y mutaciones; cada operación que muta estado deja evidencia verificable y rollback.
- Aislar credenciales y documentos sensibles: jamás añadir `.env`, textos privados, pesos, datasets grandes, tokens ni artefactos de entrenamiento a Git.
- Preferir composición y funciones puras; interfaces mediante `Protocol`; explicaciones para reglas ambiguas, sin `except Exception: pass` ni hashes de ejemplo como hashes reales.
- Entrenamiento offline separado de inferencia, con datasets licenciados, splits por documento/autor/fuente y holdout sellado.

## Cierre de trabajo y continuidad

Actualizar `docs/AGENT_HANDOFF.md` al terminar un cambio: sprint, commit/hash válido, archivos, comandos ejecutados, pruebas con resultado, bloqueos, ADR/decisiones y siguiente paso mínimo. Si un cambio queda a medias, escribirlo **incompleto**. Un PR documental no prueba que el código esté implementado.

No ejecutar SFT, DPO, benchmark de detectores o pago por GPU como paso implícito. En S0–S3 no hace falta GPU. El usuario informa que Qwen ejecuta localmente en su RTX 4050 y cuenta con Google AI Pro/Notebooks; capacidad exacta de VRAM y cuotas GPU aún por medir, no inferirlas.

Prioridad del producto: fidelidad académica, citas, semántica, privacidad y utilidad editorial. Las puntuaciones de detectores son observaciones separadas, nunca garantía de autoría ni principal criterio de aceptación.
