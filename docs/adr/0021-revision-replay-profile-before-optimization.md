# ADR-0021 — Perfilar replay completo antes de optimizarlo

- Estado: aceptada como medición diagnóstica de Sprint 2, sin cambio de contrato de recuperación.
- Fecha: 2026-10-20 (UTC).
- Base: `develop` en `f55ae6c`, después de PR #27; ADR-0014/0015/0018/0019/0020.

## Problema y evidencia

`SQLiteRevisionJournal.load`, `_write` y `verify_all_revisions` comprueban la
cadena íntegra de evidencia y reconstruyen las transiciones tipadas. La latencia
depende de **dos ejes diferentes**: tamaño total del ledger y número de estados
de cada revisión. Optimizar una consulta sin aislar esos costes podría introducir
una caché de integridad insegura o aceptar snapshots sin replay.

El [ensayo reproducible](../REVISION_REPLAY_PROFILE_S2.md) separa los tres
costes: replay interno, carga pública íntegra y verificación de todas las
revisiones. En Linux Python 3.12/SQLite 3.53.1 con bytes sintéticos, 128
auditorías de una revisión generaron 257 eventos y `load` tuvo 36,434 ms de
mediana (tres repeticiones). Dieciséis revisiones × dieciséis auditorías
generaron 528 eventos y `verify_all_revisions` tuvo 52,481 ms de mediana,
con amplia dispersión. El perfil de 129 snapshots registra 530 llamadas
SQL para `load`; el codec/replay ocupa más tiempo acumulado que la auditoría
del ledger de ese caso. Son mediciones de laboratorio, no un objetivo operativo.

## Decisión

1. Mantener sin cambios las rutas públicas actuales y el replay completo.
   No introducir un `trusted_head` cacheado, saltos de validación, estado
   materializado no comprobado o migración destructiva por motivos de velocidad.
2. Conservar el benchmark aislado, parametrizado y probado para comparar
   diferentes cantidades de revisiones y versiones sobre SQLite temporal.
   Registrar mediana, rango, pico de memoria trazada, consultas del perfil,
   plataforma, Python y SQLite. El coste de población queda fuera del tiempo.
3. Antes de introducir una optimización, exigir escenario de uso esperado,
   presupuesto explícito de latencia/memoria y repetición bajo Windows/WAL,
   y demostrar equivalencia en corrupción, reordenación, truncamiento, schema,
   concurrencia, idempotencia y reinicio.
4. La siguiente unidad de trabajo tendrá **otro PR**: durable `CleanSweep`
   e iteración externa con replay tipado. No mezclar esa semántica con la
   optimización de lectura en esta PR.

## Alternativas y límites

| Alternativa | Disposición |
|---|---|
| Saltarse auditoría completa al cargar | Rechazada: perdería detección de daño/truncamiento |
| Snapshot de estado confiable sin replay | Rechazada: podría legitimar una transición alterada |
| Prefetch/consulta agrupada manteniendo todas las verificaciones | Candidata posterior; necesita ganancia medida y prueba de equivalencia |
| Medir primero y mantener ruta íntegra | Elegida; no altera la superficie de fallo actual |

No se compararon discos, máquinas o usuarios reales; `tracemalloc` no mide RSS.
La variación, los efectos de caché OS y el coste de `BEGIN IMMEDIATE` bajo
contención sostenida permanecen fuera de este experimento. Los resultados no
demuestran corrección científica, identidad del crítico ni adjudicación de DSR.
