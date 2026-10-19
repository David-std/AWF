# Matriz de trazabilidad de AWF — planificación v0.1

**Alcance:** esta tabla captura los requisitos expresados por el usuario y las decisiones del diseño AWF. NO afirma la migración individual de los 184 requisitos históricos de AWS: ese mapeo debe realizarse en S2 contra el ZIP original por ID, estado y evidencia. No confundir compromiso documental con código verificado.

Estados: `DESIGNED` (especificado), `OPEN` (requiere decisión), `IMPLEMENTED` (solo tras test automatizado + demostración), `RESEARCH` (hipótesis). Todos los elementos de ejecución están **DESIGNED** o **OPEN**.

| ID | Requerimiento/decisión | Fuente del proyecto | Evidencia de aceptación prevista | Sprint | Estado |
|---|---|---|---|---|---|
| AWF-R001 | Conservar AWS 3.19.1 exacto con SHA/licencia/provenance, sin importar a ciegas | TDP/AWS y conversación | SHA del ZIP + manifest + inventario de derechos | S0/S2 | DESIGNED |
| AWF-R002 | Mantener arquitectura para migración entre chats/agentes sin pérdida | Solicitud explícita del usuario | Spec completa, ADR, README, handoff, estado verificable | S0 | DESIGNED |
| AWF-R003 | Tipar reglas deterministas/probabilísticas/contextuales, evitar if masivos | Pregunta sobre skills ineficientes | Registry con aplicabilidad y prueba por regla; 184 IDs auditados | S2 | DESIGNED |
| AWF-R004 | Evaluar redundancia, obsolescencia y contradicción de fuentes | Pregunta sobre investigación acumulada | Disposition + duplicado + fuente/snapshot + contradicción | S2/S6 | DESIGNED |
| AWF-R005 | Evitar que LLM se otorgue un PASS sin evidencia | Auditoría AWS | Inyección de falso recibo falla; verificación real sobre bytes | S3 | DESIGNED |
| AWF-R006 | Preservar causalidad, certeza, alcance, tiempo, cifras, citas y atribución | GDText/Meaning Audit | Mutaciones adversariales + gold + medición de falsos negativos | S3 | DESIGNED |
| AWF-R007 | Mantener originales inmutables con hash y rollback | Blueprint | Round-trip original bytes y diff reversible | S1 | DESIGNED |
| AWF-R008 | Editor neuronal especializado y baselines abiertos | Comparación Stealth/Phrasly/CoEdIT | Mismo benchmark sobre modelo base y modelo de edición | S4 | DESIGNED |
| AWF-R009 | Entrenar adaptador propio SFT/LoRA/QLoRA, no de cero | Interés ML del usuario | Adapter versionado, dataset card y métricas vs baseline | S5 | DESIGNED |
| AWF-R010 | DPO únicamente con preferencias verificadas y no contaminadas | Literatura sobre rewards | Auditoría de preferencias + ablation; decisión go/no-go | S6 | DESIGNED |
| AWF-R011 | Holdout sellado por grupos y permisos de datasets | Riesgo de contaminación | Tests de no filtración a train/evaluador/embeddings | S3–S6 | DESIGNED |
| AWF-R012 | Editores/modelos intercambiables; sin vendor lock-in | Diseño hexagonal | Pruebas contractuales Dummy/Transformers/API | S1/S4 | DESIGNED |
| AWF-R013 | CQRS ligero, monolito modular, dominio puro | Preferencia de arquitectura estándar | Test de imports/capas + ADR sobre cambio | S0–S2 | DESIGNED |
| AWF-R014 | Calidad académica primero, detectores independientes de aceptación | Objetivos del proyecto | Ningún score de detector revierte falla crítica | S3/S8 | DESIGNED |
| AWF-R015 | Evidencia externa calificada por fecha/snapshot/autoría | Deep Research y fuentes | Source registry y model card con límites | S2/S4 | DESIGNED |
| AWF-R016 | ES/EN medidos por separado y sin trasferencia automática | Proyecto TDP | Reportes separados por idioma/género | S4–S6 | DESIGNED |
| AWF-R017 | Sprint demostrable, testado, sin archivos decorativos | Solicitud del usuario | Demo, tests, changelog, evidencia de CI por sprint | S0–S7 | DESIGNED |
| AWF-R018 | Escalable sin elegir stack web genérico por inercia | Solicitud del usuario | ADR con alternativas/trigger de migración | Continuo | DESIGNED |
| AWF-R019 | Ejecutable local con RTX 4050 y opción de Notebook/Google | Hardware comunicado por usuario | Perfil real de VRAM, OOM, throughput, quotas | S4–S5 | OPEN |
| AWF-R020 | Sin necesidad de compras ni suscripciones en S0–S3 | Restricción de viabilidad | Core/CI/offline ejecutables sin API keys/GPU | S0–S3 | DESIGNED |
| AWF-R021 | Investigación científica y benchmark reproducible, resultados negativos | Comparación de técnicas | Protocolos ablation + CI + reportes con CIs | S4–S8 | DESIGNED |
| AWF-R022 | Licencias, derechos de datasets y privacidad de manuscritos | Riesgo legal | Dataset Cards, permiso por fuente, local_only default | S0–S5 | OPEN |
| AWF-R023 | Código higiénico, tipado y test con principios SOLID aplicados | Solicitud de estándares | Ruff, pyright, pytest, hypothesis, quality gate CI | S0 | DESIGNED |
| AWF-R024 | No exigir una GUI antes de validar núcleo y benchmark | Riesgo de scope | CLI inicial, API posterior, sin React por defecto | S0–S7 | DESIGNED |

## Procedimiento para implementar cada fila

Cada cambio crea relación verificable: `AWF-Rxxx → ADR → código/archivo → tests → commit → demo`. El PR registra evidencias ejecutadas, fallos y exclusiones. Nunca convertir DESIGNED en IMPLEMENTED solo porque existe un módulo vacío.

## Migración heredada AWS

La suite AWS 3.19.1 documenta 184 requisitos normativos (168 MUST, 16 lab/deferred), 22 comprobaciones semánticas atómicas y 54 casos JSON según la auditoría previa. **Estas cifras son inventario inicial, no cobertura ejecutada en AWF**. La migración exige rastrear IDs/fuentes y escoger `POLICY`, `MODEL_TRAINING`, `RETRIEVAL`, `EVAL_ONLY`, `DEPRECATED_WITH_EVIDENCE` o `UNRESOLVED` sin borrar originales. Para elementos de alto impacto, exigir prueba negativa que demuestre si la regla funciona de verdad.
