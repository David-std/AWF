# Revisión de transferencia: integridad del conocimiento DSR-016..DSR-032

**Estatus:** 17 reglas inspeccionadas contra el ZIP local AWS 3.19.1; **ninguna adjudicada definitivamente**. Este documento registra propuestas técnicas y los límites que impiden afirmar cumplimiento completo. Las fuentes originales, su texto y las respuestas de evaluación permanecen en el equipo autorizado y no se publican en GitHub.

## Fuentes y distinciones

Se inspeccionaron las entradas DSR-016..032 del registro `runtime/deep_spec_requirement_ledger.json` y los mecanismos históricos `runtime/knowledge_coverage.py`, `runtime/reference_manifest.py`, con referencias a `runtime/runtime_policy.json`, `AGENTS.md` y `knowledge/README.md`. ZIP original SHA-256: `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`.

El `make_receipt()` histórico construye `covered_references` enumerando todo el manifiesto y establece `canonical_corpus_unchanged=True` y `source_pointer_integrity=True`. Es una declaración estructural por defecto, **no una comprobación de lectura real, integridad del corpus o comprensión**. El manifiesto histórico sí obtiene hashes reales por archivo/fragmento y registra límites de líneas; esto permite identidad, pero no autentica al lector. AWF sustituye esas afirmaciones por un inventario esperado basado en los bytes originales, recibos contrastados y deuda explícita.

## Matriz de 17 decisiones candidatas

| ID | Estrategia propuesta | Evidencia implementada en el corte | Brecha para adjudicación final |
|---|---|---|---|
| DSR-016 | `KEEP_AS_CODE` candidata | Manifest canónico, prueba de preservación entre versiones | No hay copia/persistencia integral del corpus ni política de derechos |
| DSR-017 | `KEEP_AS_CODE` condicionada | Fragmentos byte-contiguos hasta EOF y recibos por hash | Ningún checksum demuestra lectura/comprensión cognitiva |
| DSR-018 | `KEEP_AS_CODE` candidata | `CoverageAssessment` explícito para fragmentos y ejes | Inventario real de ejes y tareas de cada operación todavía parcial |
| DSR-019 | `KEEP_AS_CODE` candidata | Estados independientes `AVAILABLE/READ/UNDERSTOOD/APPLICABLE/APPLIED/VERIFIED` | Evidencia externa para cada transición, aún no integrada |
| DSR-020 | `KEEP_AS_CODE` condicionada | La transición a comprensión no deriva de resúmenes | Diseño/ejecución de examen independiente y validación pedagógica |
| DSR-021 | `KEEP_AS_CODE` condicionada | Operaciones bloqueadas si falta calibración | Motor de casos independiente y adjudicación auténtica pendiente |
| DSR-022 | `KEEP_AS_CODE` candidata | Inventario obligatorio de caso positivo, casi acierto, contraejemplo, holdout | Calidad y representatividad de los casos no evaluadas |
| DSR-023 | `KEEP_AS_CODE` condicionada | Paquetes de preguntas sin claves de respuesta | Aislamiento externo del almacén de claves y fugas por otros canales |
| DSR-024 | `KEEP_AS_CODE` candidata | `FAILED/UNRESOLVED` mantienen deuda y bloquean puerta | Auditoría de quién adjudica y de la evidencia registrada |
| DSR-025 | `KEEP_AS_CODE` condicionada | Error de calibración impide continuar con alta criticidad | Planificador explícito de reentrenamiento/recalibración |
| DSR-026 | `KEEP_AS_CODE` condicionada | Política rechaza convertir controles humanos en plantillas de estilo | Prohibición en puertos/modelo de generación y evaluaciones adversariales |
| DSR-027 | `KEEP_AS_CODE` condicionada | Las tarjetas admiten principios y límites, no copiar ejemplos como plantillas | Instrucciones/pipelines de edición y exámenes del comportamiento del modelo |
| DSR-028 | `KEEP_AS_CODE` candidata | Tarjeta conserva punteros a fuentes y dependencias transitivas | Resolver punteros contra archivos reales, credenciales y licencias |
| DSR-029 | `KEEP_AS_CODE` candidata | Conservación de referencias/negativos entre versiones con deuda por eliminación | Registro de versiones, pruebas de migración y explicación de retiradas |
| DSR-030 | `KEEP_AS_CODE` candidata | Fuentes críticas se incluyen en cierre de dependencias aun si son raras | Establecer aplicabilidad auténtica y evitar sobreinclusión innecesaria |
| DSR-031 | `KEEP_AS_CODE` candidata | Recuperación exige dependencias declaradas, no solo ranking textual | Extracción/adjudicación de dependencias faltantes en todo el corpus |
| DSR-032 | `KEEP_AS_CODE` condicionada | Métricas diferenciadas de ahorro de tokens y cobertura de invariantes | Evaluación independiente de fidelidad semántica y calidad de escritura |

De los 17, **12 son reclamos mecánicos históricos y 5 garantías estructurales acotadas**. En AWF estas entradas siguen `UNRESOLVED` y el código de este corte es un **prototipo verificable**, no una migración homologada.

## Criterios falsables y garantías reales

- Hash original, fragmentos y contigüidad: pruebas mecánicas contra cambios, duplicados, huecos, ciclos o fragmentos faltantes.
- Recibos de lectura: documentan fragmentos observados; un agente puede copiar sus hashes sin leer, por lo que **no equivalen a comprensión**. El contrato exige evidencia adicional de evaluación para avanzar.
- Calibración: los casos positivos, near-miss, contraejemplos y holdouts están inventariados. Las referencias de respuestas privadas jamás se colocan en el paquete activo. Si falta una familia o la adjudicación es irresuelta, el uso de alto impacto queda bloqueado.
- Recuperación: cierre transitivo por dependencias tipadas e inclusión conservadora de excepciones críticas. Ninguna recuperación se interpreta como permiso de aplicar la regla.
- Controles humanos: solo sirven para investigar variación legítima y falsos positivos, no para imitar sus elecciones superficiales o entrenar sin licencia.
- Versiones: una fuente eliminada o alterada genera deuda; esta versión no permite borrar historia negativa silenciosamente.
- Eficiencia: una reducción del 90 % en tokens con solo 33 % de invariantes respaldados **no es** mejora de fidelidad. Los indicadores se publican por separado y no constituyen un certificado de calidad científica.

## Riesgos residuales (no resueltos)

1. **Autenticidad de recibos:** `reader_ref` y `evidence_ref` son referencias declarativas; necesitan un verificador independiente y almacenamiento inalterable.
2. **Lectura real:** el software observa bytes, no estados cognitivos de un LLM. Comprensión requiere casos adjudicados y controles de transferencia.
3. **Conocimiento verdadero:** hash y cierre de dependencias no resuelven contradicciones o veracidad científica de afirmaciones; deben existir verificadores de fuente y juicio experto.
4. **Fuga del holdout:** el paquete de desafío excluye claves pero carece de separación de procesos/credenciales; no se debe presumir aislamiento completo.
5. **Derechos y entrenamiento:** la clasificación `TRAIN` del registro S2 no constituye permiso para usar materiales históricos como dataset.
6. **Aplicabilidad:** incluir excepciones críticas por defecto es conservador, pero no sustituye una revisión de pertinencia contextual.
7. **Integración:** no hay CLI estable para estas primitivas, ni entrenamiento neuronal, ni recuperación de documentos reales, ni aceptación en el registry de 184 decisiones.

**Siguiente paso:** conectar estas puertas a un registro durable con identidad verificada y corpus privado autorizado, y revisar las relaciones de las 17 reglas con los casos reales; mantener `REVIEW_ATTESTED` vacío hasta resolver límites de evidencia.
