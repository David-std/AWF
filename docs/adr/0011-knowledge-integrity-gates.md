# ADR-0011 — Integridad del conocimiento basada en cobertura esperada

- **Estado:** Aceptado como prototipo del Sprint 2; pendiente de pruebas reales y revisión independiente.
- **Fecha:** 2026-10-17.
- **Contexto:** En la suite histórica AWS 3.19.1 el recibo de `knowledge_coverage.make_receipt` copia las referencias del manifiesto a `covered_references` sin observar su lectura y declara `canonical_corpus_unchanged` y `source_pointer_integrity` verdaderos. Esto puede generar un falso PASS de cobertura aunque el lector no consulte los fragmentos.
- **Decisión:** crear una capa pura que genera inventario por bytes originales, hash de cada fragmento, coordenadas contiguas a EOF, dependencias explícitas, excepciones críticas y negativos. Validar recibos observados por separado; exposición de faltantes y duplicados en `CoverageAssessment`.
- **Separación epistémica:** `AVAILABLE != READ != UNDERSTOOD != APPLICABLE != APPLIED != VERIFIED`. Cada transición requiere una referencia a evidencia; lectura demanda cobertura completa, comprensión exige adjudicación explícita y aplicabilidad revisión contextual. Estos recibos **no son criptográficamente firmados ni evidencia de competencia cognitiva**.
- **Calibración:** registrar al menos un positivo, near-miss, contraejemplo y holdout por operación; fabricar un paquete activo con ID y referencia de pregunta, nunca con referencias a claves privadas; discrepancias y resultados no resueltos bloquean avance.
- **Recuperación:** usar cierre transitivo en un grafo revisado y añadir fuentes críticas aunque no se encuentren por relevancia. Un ejemplo humano/negativo no autoriza generar plantillas de estilo, ni un registro de metadatos autoriza entrenamiento.
- **Métricas separadas:** reportar costo/tokens y cobertura de invariantes como dos magnitudes diferentes; estos cálculos no avalan la fidelidad real del texto editado.
- **Tradeoffs:** la inclusión conservadora de excepciones puede gastar más tokens y generar ruido, pero evita invisibilizar obligaciones críticas por frecuencia. Una política de pertinencia por contexto requerirá validación propia.
- **Alternativas descartadas:** copiar los hashes en una lista etiquetada `covered`; promover `UNDERSTOOD` con un resumen; usar ejemplos como moldes textuales; excluir excepciones infrecuentes por costo; inferir conformidad a partir de ahorro de tokens.
- **Seguridad:** corpus y respuestas de holdout continúan solo en local; el Git público contiene contratos, tests con datos sintéticos y análisis sin reproducir textos originales.
- **Pendiente:** autenticidad/firmas, persistencia, verificadores de comprensión/fidelidad, cumplimiento de licencias, integración con datos reales y evaluación de fuentes.

## Segunda pasada de arquitectura

Se trasladó el cierre de dependencias a `awf.domain.dependencies` y se dejó un reexport compatible en `awf.knowledge.dependency_graph`; la capa de dominio ya no importa conocimiento de aplicación ni adaptadores. La transición `READ` exige ahora un `CoverageAssessment` tipado y completo, no un booleano declarado por el llamante; un cambio de `context_ref` invalida la continuidad de las etapas ya registradas. Estas mejoras eliminan dos vías de falso cumplimiento estructural, pero siguen sin autenticar criptográficamente los recibos.

## Revisión previa a fusión (2026-10-19)

- Los archivos fuente vacíos se pueden inventariar mediante un fragmento de cero bytes por compatibilidad documental, pero **nunca** satisfacen `CoverageAssessment.complete` ni autorizan `READ`.
- La verificación de manifiestos exige IDs y SHA-256 bien formados, e impide fragmentos de longitud cero dentro de fuentes no vacías. Los cambios de dependencias, criticidad, rutas de evidencia y otros metadatos dejan deuda de preservación aunque el SHA del contenido se mantenga.
- La calibración rechaza familias de casos representadas como strings en vez de enums tipados; un resultado mecánicamente `PASSED` no certifica comprensión o veracidad académica.
- Estas garantías estructurales no prueban que un tercero realmente haya leído, comprendido o validado las fuentes; permanecen pendientes identidad, derechos y verificación independiente.
