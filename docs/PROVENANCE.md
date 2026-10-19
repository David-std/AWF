# Procedencia y preservación de los artefactos AWS → AWF

## Fuente histórica congelada y comprobada

- Fuente: `academic_writing_suite_v3_19_1_product(1).zip`, suministrada por el usuario.
- Versión interna: `3.19.1`.
- SHA-256 ZIP comprobado: `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`.
- Entradas ZIP: `1364`.
- Manifiesto histórico suministrado: `academic_writing_suite_v3_19_1_product.manifest(1).json`; hash ZIP coincide con el anterior.
- Nota de derechos: no se ha verificado una licencia de redistribución para todo el corpus, referencias e historiales del ZIP. **No publicar el ZIP ni trasladar su contenido a un repositorio público automáticamente.**

## Fuentes de arquitectura v0.1

- Blueprint ZIP `AWF_Neural_Engine_architecture_blueprint_v0_1.zip`, SHA-256 `32592f7ef8de1b3f39c82d7a8765435ec50817f292ec7b910d8cbf9a68524ce2`.
- Especificación Markdown original: SHA-256 `4011f2b31ff729890245ad2cbd807d51ad7eb4abd7516bb0333ba64b3a522401`.
- Plantilla de handoff original: SHA-256 `25a917eed434921ea75837d6a4c90a17f8077a6ec29310b5dacfe23d5ee315f6`.
- Decision lock original: SHA-256 `cfe9f1fe89eed7b79402eb36eb6f4d3fe53d0ed6d5dff76f68080275f5be9879`.
- `docs/architecture/DECISIONS_LOCK.yaml` es un **overlay actualizado** de la versión original para reflejar repositorio real y hardware comunicado, no la copia byte a byte de la fuente.

## Regla de migración

El corpus no es una verdad incuestionable. S2 debe inspeccionar cada requisito heredado, clasificarlo según verificabilidad, actualidad, contradicciones y evidencia y mantener su procedencia. Un `knowledge item` se relaciona con el source_id histórico, sha, segmento, decisión y test. Los casos adversariales heredados se reservan prioritariamente para evaluación salvo permisos/decisión explícita.

No atribuir a AWF ningún rendimiento detector, entrenamiento o calidad demostrada por la suite histórica hasta repetir experimentos con el motor nuevo.
