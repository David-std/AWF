# AWF — auditoría de integración de PR #10–#20

- **Fecha de corte:** 2026-10-19 (UTC).
- **Destino exclusivo:** `develop`, creado desde `main` en `a902135b80e96eea17ebb9c229eed065077e809d`.
- **HEAD auditado:** `26a937ebf647fd438ed703ac0e3a9c94aabc09c7`.
- **Resultado:** once PR revisadas y fusionadas **en orden**, con merge commits; `main` no se modificó.
- **Alcance de la afirmación:** pruebas técnicas e integridad local, **no** revisión científica independiente, completitud de S2 ni certificación de las reglas históricas.

## Puertas aplicadas

Para cada PR se cotejó su diseño con `AGENTS.md`, la especificación de arquitectura v0.1, los ADR y la dependencia anterior; se inspeccionaron contratos de dominio/adaptadores, rutas negativas, persistencia y cambios de documentación. Los defectos detectados se corrigieron en la **rama original de la PR** (o en un commit de integración de dos padres cuando aparecieron conflictos). Se validó el árbol real resultante, lint, formato, tipos y CI Linux/Windows antes de la fusión; ningún cambio se introdujo directamente en `develop` para disimular una rama incompleta.

| PR | Merge commit en `develop` | Hallazgo relevante y resolución |
|---|---|---|
| [#10](https://github.com/David-std/AWF/pull/10) | `4a8fff0` | Arquitectura, contratos y decisiones fijadas como marco de la integración. |
| [#11](https://github.com/David-std/AWF/pull/11) | `0f0773b` | Se extendió la CI para cubrir push a `develop`; CLI, packaging y calidad básica. |
| [#12](https://github.com/David-std/AWF/pull/12) | `7c57c90` | Publicación de blobs atómica, rechazo de rutas simbólicas/alias de fuente y escritura segura de JSON; negativos y concurrencia. |
| [#13](https://github.com/David-std/AWF/pull/13) | `35dc9af` | `REVIEW_PROPOSED` no equivale a `REVIEW_ATTESTED`; rechazo de promociones falsificadas y ZIP validado sobre descriptor estable. |
| [#14](https://github.com/David-std/AWF/pull/14) | `5d94e63` | Workbench no sobrescribe anotaciones humanas y recupera generación incompleta; conflicto fusionado preservando código y pruebas previas. |
| [#15](https://github.com/David-std/AWF/pull/15) | `70a9782` | Presupuestos y `CONVERGED` sin falso PASS; huellas locales de estructura y vecindad, tipos estrictos y casos negativos. |
| [#16](https://github.com/David-std/AWF/pull/16) | `40b0975` | Fuentes vacías no justifican READ; preservación de metadatos/dependencias, calibración y validación de fragments. |
| [#17](https://github.com/David-std/AWF/pull/17) | `ec006a7` | SQLite ya no confía en *nombres* de triggers reemplazados: verifica DDL efectivo; resolución de imports de CLI sin perder módulos previos. |
| [#18](https://github.com/David-std/AWF/pull/18) | `e13913c` | Rechaza recibos duplicados, claves dirty ajenas y secuencias de conocimiento mezcladas entre ejecuciones. |
| [#19](https://github.com/David-std/AWF/pull/19) | `83ab095` | Atomicidad de estado/evento, idempotencia y recuperación; verificación de triggers de snapshots y reconstrucción del delta `AUDIT`. |
| [#20](https://github.com/David-std/AWF/pull/20) | `26a937e` | Replay tipado de `EDIT`/hallazgos; resolución de conflicto preservando replay `AUDIT` anterior; rechazo de eventos válidos reutilizados fuera del orden causal. |

La columna de resolución identifica controles técnicos probados, **no** garantiza exhaustividad lógica de todos los escenarios futuros.

## Evidencia de validación del estado acumulado

| Superficie | Resultado | Evidencia |
|---|---|---|
| Árbol combinado Linux Python 3.12 | **196 pytest PASS**, Ruff check/format y Pyright sin errores | Worktree de integración con árbol idéntico al publicado para PR #20. |
| GitHub Actions sobre la resolución exacta de PR #20 | **4/4 SUCCESS**: Ubuntu y Windows en Python 3.12/3.13 | [Workflow 39186482215](https://github.com/David-std/AWF/actions/runs/39186482215). |
| Equipo ASUS ROG STRIX autorizado, Windows Python 3.12 | **194 PASS, 2 SKIP** | Worktree aislado de `develop` al SHA `26a937e`; `hypothesis==6.142.4` en directorio local de dependencias de auditoría. |
| Protecciones de rama | 11 PR `closed/merged`, todas con base final `develop`; `main` inalterada | Historia `--first-parent` de `develop` y metadata de PR #10–#20. |

Las dos omisiones Windows están motivadas: una prueba de permisos POSIX y una limitación de bloqueo de ZIP abiertos en Windows. Las pruebas adversariales correspondientes se conservaron y ejecutan donde aplica. El ensayo inicial del worktree Windows sin paquete instalado falló en *importación*, no en lógica; se reprodujo con `PYTHONPATH` de proceso y terminó verde sin alterar la rama original del dispositivo.

## Riesgos que siguen abiertos

1. **Identidad/roles del evaluador:** un recibo vinculado a bytes y eventos sigue siendo una declaración local; no existe comprobación independiente de autoridad, aislamiento o calidad de quien juzga. No inferir `independent_adjudication_proven`.
2. **Anclaje y recuperación fuera del dispositivo:** un atacante con control total puede reescribir el ledger y el head. Faltan firma/custodia externa, prueba de truncación, backup/restore y un protocolo de recuperación versionado.
3. **Convergencia durable incompleta:** `START`, `AUDIT`, `EDIT`, `FINDING_OPEN` y `FINDING_RESOLVE` están coordinados; barridos críticos e iteraciones externas no tienen todavía el mismo contrato durable. No automatizar aceptación final.
4. **Escalabilidad:** verificar toda la cadena repetidamente por fragmento puede ser O(n²) en el flujo de conocimiento. Requiere perfiles, vistas transaccionales por lote y límites explícitos antes de corpus voluminosos.
5. **Corpus histórico y licencias:** 184 entradas, de ellas 168 `MUST`; **cero adjudicaciones formales**. Solo 32 poseen análisis/prototipos técnicos preliminares y 136 aún requieren ese examen. Las 16 `DEFERRED_LAB` se mantienen `EVAL_ONLY`. El ZIP, el corpus, los holdouts y los manuscritos reales no se publicaron.

## Siguiente incremento recomendado

Abrir una PR S2 **después de la integración**, desde `develop`, con contratos de identidad/roles y anclaje externo verificable: especificar quién firma, cómo se revocan claves, dónde se custodian checkpoints y cómo fallan los verificadores ante suplantación, rollback o ausencia de la prueba. Antes de certificar barridos, añadir su transacción de estado y una recuperación que reproduzca el cambio de dominio. Mantener ADR y pruebas adversariales por módulo; medir latencia con fragmentos numerosos. No pasar a entrenamiento o adjudicación formal por el solo hecho de tener la infraestructura integrada.
