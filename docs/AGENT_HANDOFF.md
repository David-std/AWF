# AWF — handoff de la implementación Sprint 2 (corte inicial)

Fecha: 2026-10-17. Rama `feat/s2-knowledge-compiler`, apilada sobre PR #12, #11 y #10. **Las PR continúan abiertas; no confundir rama con `main`.**

- **Sprint activo:** S2, fase de importación y clasificación conservadora. Issue [#3](https://github.com/David-std/AWF/issues/3); PR [#13](https://github.com/David-std/AWF/pull/13).
- **S0–S1:** la CLI, `DocumentIR`, ingesta Markdown y tests previos están en PR #11 y #12; las últimas pruebas de S1 pasaron en Linux/Windows y Python 3.12/3.13.
- **S2 código:** `domain/knowledge.py`, compilador, clasificador conservador, aplicabilidad, duplicados textuales, grafo explícito de dependencias, adaptador ZIP, importador, auditor, guardado JSON atómico local y comandos CLI.
- **Fuente real:** `academic_writing_suite_v3_19_1_product(1).zip` NO SUBIDO; SHA-256 `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c` y 184 requisitos (168 MUST + 16 DEFERRED_LAB) verificados al inspeccionar los bytes locales. La ejecución del importador sobre este ZIP se debe comprobar en entorno local autorizado; CI usa ZIP sintéticos para no publicar el corpus.
- **Salida:** registro en `.awf/knowledge/`, sin enunciados originales. Inicialmente 168 `UNRESOLVED` y 16 `EVAL_ONLY`, 184 entradas sin silencios.
- **Tests:** consultar el último job de PR #13. No declarar PASS si no concluyó satisfactoriamente; anotar SHA exacto del run. Los ensayos de permisos de ZIP, negativos y CI son por código sintético, no dataset real.
- **No implementado:** revisión cualitativa de 168 requisitos, autoría/licencias por dataset, contradicciones semánticas verificadas, persistencia transaccional SQLite/ORM, evaluación de redacción, modelos, SFT/DPO o API.
- **ADR:** `docs/adr/0008-local-knowledge-import.md`; difiere SQLite/ORM hasta tener una razón empírica. Imprescindible revisar ADR antes de incorporarlo.
- **Siguiente tarea:** cerrar CI, probar `knowledge import` con el archivo privado sin subirlo, y diseñar lotes de revisión de reglas con criterios objetivos y estados conservadores; mantener S2 abierto hasta adjudicación completa.

**Regla de continuidad:** no considerar un registro importado como corpus listo para fine-tuning; registrar evidencia, permisos y validación antes de promoción.
