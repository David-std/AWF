# AWF — handoff integral de recuperación, PR #45 (LoRA real)

**Fecha:** 2026-10-21, Lima. **Repositorio:** https://github.com/David-std/AWF. **Cuenta:** GitHub David-std. **Propósito:** permitir que el siguiente agente continúe sin reconstruir código, repetir entrenamientos o confundir PR paralelas. Este documento recoge evidencia ya contrastada con GitHub y el ordenador autorizado.

**Punto de partida verificado:** PR #45 (https://github.com/David-std/AWF/pull/45), OPEN y DRAFT; branch feat/s3-peft-training-foundation, base feat/s3-synthetic-scope-benchmark (#43). HEAD antes de publicar este handoff: a0d7a27356f77e5dd7de8d869e8cae343c2eed6b. El commit documental que añade esta nota será posterior y necesitará **su propia CI**. No atribuirle CI de un commit anterior.

## 1. Estado técnico comprobado

| Elemento | Resultado sustentado |
| --- | --- |
| CI del HEAD original de PR #45 | Rama: https://github.com/David-std/AWF/actions/runs/39692394224, 4/4 SUCCESS. PR: https://github.com/David-std/AWF/actions/runs/39692400122, 4/4 SUCCESS. Ubuntu/Windows × Python 3.12/3.13. |
| Commit funcional | 6d31a353d58bc48139ef78b2f199237c73821f30; rama https://github.com/David-std/AWF/actions/runs/39691797573 y PR https://github.com/David-std/AWF/actions/runs/39691803895, ambos 4/4 SUCCESS. |
| Pruebas CI | 555 pytest PASS en Ubuntu/Python 3.12, Ruff lint/format PASS, Pyright cero errores/advertencias, wheel/sdist PASS. La CI no ejecuta un training CUDA nuevo en cada SO. |
| Modelo base | Qwen/Qwen2.5-0.5B-Instruct, Hugging Face revisión exacta 7ae557604adf67be50417f59c2c2f167def9a775, Apache-2.0. NO confundir con el Qwen2.5 7B usado en PR #42 mediante Ollama. |
| Máquina | ASUS_ROG_STRIX, RTX 4050 Laptop 6 GB, Windows, entorno Python neural aislado. PyTorch 2.9.1+cu130, Transformers 5.0.0, PEFT 0.20.0, TRL 0.29.1. |
| Segundo entrenamiento REAL | Run f4e66e7e8e3b420d8dd74dfab79536fc, 8/8 pasos de optimizador, training loss 0.9806072264909744, duración entrenador ~15,09 segundos, proceso exit 0. |
| Datos | Solo material ficticio original: 8 ejemplos train, 2 validation, descriptor ficticio holdout sellado/no abierto. Manifest SHA 73c1c93971dcdfecd783bd16c747f70a77b04158e05e54af00a9716958770fda. |
| Adaptador | adapter_model.safetensors de 2.175.168 bytes, SHA 8261a513e3a2fa517f13814bf422669d4763f62b5ff1f3fcacbf94a3dd26f319. |
| Recibo | receipt.json SHA 2b37cc7f8376be93ade5da3429f1445a8298fb33cf28c9de849e45a80b7c28e1; siete de siete archivos contrastados contra el recibo. |
| PEFT revision | adapter_config.json fija ahora exactamente revisión 7ae557604adf67be50417f59c2c2f167def9a775; verificador stdlib con exit 0. |
| Reload | Recarga PEFT offline correcta, 96/96 tensores LoRA no nulos, generación sintética de ocho tokens, parámetros congelados en inferencia. |
| Colab | El notebook QLoRA y perfil NF4 existen, pero NO hay evidencia de ejecución real en Google Colab. |
| Validación académica | NO realizada; no hay gold independiente, validación de conservación de claims/citas ni prueba de mejora respecto al modelo base. |

La evidencia ya está comentada en https://github.com/David-std/AWF/pull/45#issuecomment-6328737585 y descrita en docs/handoffs/2026-10-21-S3-PR45-LORA-TRAINING.md. En esta recuperación se verificó de nuevo directamente por terminal local que el segundo run existe, que coinciden el SHA del recibo y pesos, los pasos/loss y la revisión guardada en adapter_config.

### Primer entrenamiento histórico, NO sobrescribir

Run a39d4d23782d4cd79ee94325b0566696: 8 pasos, loss ~0,9749333, peso verificado, recarga offline. Su adapter_config.json tenía revision:null, aunque el recibo contenía el pin de revisión. El bug de reproducibilidad fue corregido después; mantener ambos runs **sin corregir retrospectivamente** los archivos históricos.

## 2. PRs: pila principal y rama paralela

    ... → PR #39 → PR #40 → PR #41 → PR #42 → PR #43
                                                      ├── PR #44, EXPERIMENTAL PARALELA
                                                      └── PR #45, LoRA PEFT verificado (ACTUAL)

- PR #43: https://github.com/David-std/AWF/pull/43; HEAD 446c129cad2def835e1c8c712c9ec3d981878ed8; base feat/s2-local-agent-execution; OPEN DRAFT.
- PR #44: https://github.com/David-std/AWF/pull/44; branch feat/s4-lora-smoke-pipeline, HEAD cea2057ad7d22ebafc76fe07f7fd44805a2921a9; base **#43**. No es padre de #45. No incorporar automáticamente sus archivos, resultados ni reglas.
- PR #45: https://github.com/David-std/AWF/pull/45; branch feat/s3-peft-training-foundation; base **#43**; OPEN DRAFT; HEAD pre-handoff a0d7a27356f77e5dd7de8d869e8cae343c2eed6b.
- Main a fecha de corte: a902135b80e96eea17ebb9c229eed065077e809d.
- Develop a fecha de corte: 6888a8f44a3342c61e0d31dc93374ef44a21c174.

**PROHIBIDO por defecto:** merge, retarget, force-push, rebase, eliminación de ramas, publicación de artefactos o cherry-pick de #44. Si alguna funcionalidad de #44 parece útil, comparar explícitamente ambos diffs, contratos y casos de prueba, proponer ADR si cambia arquitectura y obtener una integración trazable en rama separada.

## 3. Dónde están los archivos privados reales

El dispositivo ASUS_ROG_STRIX estaba ONLINE al efectuar esta recuperación. Checkout con entrenamiento ejecutado:

    C:\Users\david\AppData\Local\Temp\awf_pr45_execution_20261021\
      .git\                         [HEAD local: 6d31a353d58b...]
      .awf\
        neural-smoke\
          manifest.json
          train.jsonl
          validation.jsonl
        model-runs\
          a39d4d23782d4cd79ee94325b0566696\   [primera corrida histórica]
            receipt.json
            adapter\
          f4e66e7e8e3b420d8dd74dfab79536fc\   [run post-fix CANÓNICO]
            receipt.json
            adapter\
              adapter_config.json
              adapter_model.safetensors
              [cinco archivos de configuración/tokenizer adicionales]

Entorno virtual neural observado:

    C:\Users\david\AppData\Local\Temp\awf_neural_venv_20261021\

Otro checkout C:\Users\david\AppData\Local\Temp\awf_pr45_neural_20261021 tiene código anterior y NO es la prueba final. La carpeta C:\Users\david\AppData\Local\Temp\awf_s4_train_20261021 corresponde a la rama **#44 paralela**. Existe además zona C:\Users\david\Downloads\AWF, cuya existencia no certifica un run actual.

**Acción urgente de conservación:** Temp puede limpiarse automáticamente. Copiar los dos runs, la manifest y los splits a un almacenamiento privado duradero y excluido de Git, de forma **no destructiva**; recalcular los hashes tras copiar. Nunca confundir una reconstrucción posterior con el run original ni borrar Temp antes de verificar copia. No subir pesos/datos/checkpoints a GitHub, Drive, Colab ni HF como atajo.

### Verificación no destructiva en PowerShell (NO reentrena ni abre holdout)

    $repo = Join-Path $env:TEMP 'awf_pr45_execution_20261021'
    $python = Join-Path $env:TEMP 'awf_neural_venv_20261021\Scripts\python.exe'
    $run = Join-Path $repo '.awf\model-runs\f4e66e7e8e3b420d8dd74dfab79536fc'
    Set-Location $repo
    $env:PYTHONPATH = Join-Path $repo 'src'
    git rev-parse HEAD
    Get-FileHash (Join-Path $run 'receipt.json') -Algorithm SHA256
    Get-FileHash (Join-Path $run 'adapter\adapter_model.safetensors') -Algorithm SHA256
    & $python -m awf.training.verify_adapter $run --expected-receipt-sha256 2b37cc7f8376be93ade5da3429f1445a8298fb33cf28c9de849e45a80b7c28e1

Verificar contra hashes anteriores. El módulo verify_adapter compara archivos/revisión declarada y coherencia estructural, NO demuestra calidad científica, derechos, procedencia humana ni que se hayan seguido todas las decisiones de entrenamiento.

## 4. Arquitectura y archivos que el siguiente agente DEBE leer

Lectura en orden ANTES de tocar código:

1. AGENTS.md: contrato operativo, estilo, pruebas, restricciones de seguridad y trabajo sobre PR drafts.
2. README.md, docs/AGENT_HANDOFF.md, este documento, docs/handoffs/2026-10-21-S3-PR45-LORA-TRAINING.md y discusión de PR #45.
3. docs/architecture/ARCHITECTURE_SPEC_0_1.md, docs/architecture/DECISIONS_LOCK.yaml, docs/REQUIREMENT_TRACEABILITY.md, docs/SOURCE_REGISTRY.md.
4. docs/adr/0033-exact-invariant-probe.md, 0034-local-agent-execution.md, 0035-synthetic-evaluation-boundary.md, 0036-peft-adapter-training.md, docs/SOURCE_RIGHTS_GATE_S2.md.
5. docs/NEURAL_TRAINING_S3.md, docs/COMPUTE_AND_TRAINING.md, comentarios de PR #44 si se necesita analizar un conflicto.

Mapa concreto:

| Archivo/ruta | Función |
| --- | --- |
| src/awf/training/manifest.py | SHA de manifest y JSONL, derechos DECLARADOS, roles SYNTHETIC_SMOKE y OWNER_AUTHORED, separación train/validation/holdout por grupo. No abre holdout. Pin del modelo y revisión. |
| src/awf/training/synthetic_smoke.py | 12 pares completamente ficticios ES/EN de los que salen 8 train, 2 validation y descriptor sellado. Creación local en .awf, no corpus real. |
| src/awf/training/runner.py | Preflight sin GPU, --execute explícito, SFTTrainer de TRL, PEFT LoraConfig con revisión y parámetros, guardado en .awf/model-runs y recibo. |
| src/awf/training/verify_adapter.py | Hash de recibo, inventario/byte-hash de archivos y revisión PEFT. Stdlib, sin ML/GPU. |
| config/training/local_lora_0_5b.json | r 8; alpha 16; dropout 0,05; 8 pasos; seq 256; LR 0,0002; acumulación 2; seed 42. |
| config/training/colab_qlora_0_5b.json | QLoRA NF4, 80 pasos, seq 512, acumulación 4; no ejecutado en Colab. |
| requirements-neural.txt y requirements-neural-colab.txt | Dependencias ML separadas del runtime normal; bitsandbytes para QLoRA. Torch CUDA compatible con GPU. |
| notebooks/awf_s3_qlora_colab.ipynb | Opción Colab: por defecto EXECUTE_TRAINING=False; clona la rama #45 (NO un commit inmutable de AWF). Si algún día se ejecuta, fijar SHA del checkout y registrar el entorno real. |
| tests/unit/test_neural_training.py y test_verify_adapter.py | Contratos, negativos y pruebas aisladas; CI no demuestra una nueva corrida CUDA. |
| src/awf/application/ports.py, commands/run_agent.py, adapters/models/ollama_local.py | Inferencia local observada de Qwen 7B en Ollama (PR #42), independiente del LoRA entrenado Qwen 0.5B. |
| src/awf/evaluation/synthetic_scope.py | Diagnóstico de fallos/abstenciones deterministas, NO gold ni verificador semántico científicamente evaluado. |
| docs/handoffs/2026-10-21-S3-PR43-SYNTHETIC-SCOPE.md | Historia del diagnóstico sintáctico sobre pares ficticios que motivó la evaluación. |

La arquitectura AWF es **monolito modular Python 3.12, hexagonal con puertos/adaptadores**, dominio tipado y sin dependencias Torch en el runtime ordinario, con hashes sobre bytes, data lineage, originales inmutables, tests negativos y CI Ubuntu/Windows/Python 3.12/3.13. No rediseñar para introducir microservicios, una base vectorial o infraestructura de agentes adicional sin necesidad medida.

## 5. Qué está probado y qué queda SIN demostrar

Lo que sí quedó demostrado: entrenamiento supervisado **real** del delta LoRA con ocho pasos, archivo safetensors guardado, integridad de siete artefactos, revisión de base guardada, recarga offline y generación de prueba. AWF ya dispone de un primer adaptador neuronal propio, pero en etapa de **smoke test de infraestructura**.

Lo que NO se demostró: mejores reescrituras, preservación semántica, fidelidad de citas, precisión/rechazo en cambios críticos, generalización a textos académicos, detector Pangram/Turnitin/GPTZero, validación sobre fuentes reales, satisfacción de todos los requisitos AWS o calidad autoral humana.

Punto importante del código: el runner usa SFTConfig con eval_strategy="no" (sin evaluación durante SFT) y save_strategy="no". Hay 2 pares de validación que son leídos/validados estructuralmente, pero NO se reportó val_loss. Holdout ficticio sellado no fue abierto. **0,9806 es pérdida de entrenamiento**, NO validación ni benchmark independiente. No “abrir” el descriptor ficticio para fabricar una evaluación gold y no comparar el adaptador con su mismo train set.

## 6. Próximas tareas, por prioridad (incrementos medibles)

1. **Preservar evidencia privada**: copiar no destructivamente ambos runs históricos + manifest/splits a destino durable local y verificar hashes; mantener el original. No reentrenar para recuperar trazabilidad.
2. **Construir protocolo gold independiente**: pares fuente/candidato derechos claros, soporte de claims y citas, registro de annotators, anotaciones discrepantes, procedencia y QA, y split/holdout agrupado por documento/autor/fuente para impedir leakage. Un campo JSON que diga INDEPENDENT_REVIEWED no certifica la revisión. Mantener la aceptación académica en UNKNOWN/NEEDS_REVIEW ante dudas.
3. **Comparación pareada base vs base+LoRA**: usar **la misma base Qwen2.5 0.5B pinned**, misma tarea, prompt, parámetros/seed/tokenizer y documento por cada par, salidas y tiempos medidos, SHA/recibos separados, controles de preservación de negación, cantidad, cita, causalidad, población y límites. Reportar falsos positivos/negativos, abstenciones, estratos ES/EN y casos críticos; gold externo separado de selección de hiperparámetros.
4. **Solo luego** considerar nuevos datos autorizados, entrenamiento con más pasos/rank o Colab QLoRA NF4. No asumir que Google AI Pro garantice GPU/tiempo; confirmar recursos y privacidad del runtime. Si aún no existe corpus independiente autorizado, implementar primero **solo el harness con fixtures marcadas sintéticas**, sin afirmar calidad real.
5. A cada corte: commit inmutable, CI exacta (ambos eventos) y herramientas, ADR si cambia contrato, docs/handoff y comentario técnico PR; reportar lo no completado.

No priorizar UI/branding, nueva cadena de firmas o microservicios: el principal cuello de botella ahora es **la calidad de datos y evaluación**, no volver a demostrar SGD/LoRA.

## 7. Restricciones no negociables y deuda histórica

- ZIP AWS 3.19.1 privado, SHA ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c; NO subirlo. Sus 184 requisitos: 168 MUST **sin adjudicación formal**, 16 DEFERRED_LAB **EVAL_ONLY**. El legacy source es origen de hipótesis, no verdad automáticamente aceptada de AWF.
- El dueño puede autorizar pruebas locales; eso no significa que terceros hayan licenciado sus textos para entrenamiento ni que haya independencia de revisores. Controles de derechos y rechazos siguen vigentes.
- NO publicar a GitHub, Hugging Face o Colab: ZIP histórico, PDFs/textos de terceros sin derecho, dataset privado, pesos safetensors, credenciales, logs sensibles, cachés y .awf local. No usar API externa con manuscritos confidenciales de manera implícita.
- Modelos generan propuestas, NO jueces incuestionables. PASS de comprobación literal no equivale a fidelidad; FAIL crítico bloquea y UNKNOWN necesita revisión. No optimizar scores de detectores como sustituto de calidad y atribución correcta.
- Mantener failures y PRs históricas, no falsificar el recibo original revision:null, ni cambiar flags model_quality_certified=false / semantic_equivalence_verified=false / independent_gold_verified=false para hacer pasar el experimento.
- No remezclar los artefactos de #44 y #45 sin auditar sus fuentes y ramas.

## 8. Protocolo del agente entrante

Antes de escribir código: verificar en GitHub **#43, #44 y #45** (head SHA, base, draft, CI); leer documentos del §4 y comentario de PR #45 https://github.com/David-std/AWF/pull/45#issuecomment-6328737585; verificar que esta nota fue publicada y su **nuevo SHA/CI**. Identificar exactamente el checkout del run f4e...; si Temp se limpió, NO fabricar el mismo experimento, indicar la pérdida y buscar respaldo.

Si requiere una nueva funcionalidad que dependa de #45, crear una nueva rama y PR draft apilada sobre #45; mantener main y develop. NO mergear #44 por tener un nombre similar. Realizar tests, lint, format, Pyright, builds, CI Ubuntu/Windows 3.12/3.13 y una prueba funcional con recibos; reportar fallos sin atribuir resultados inexistentes.

**Mensaje reutilizable para el próximo chat:**

> Continúa Academic Writing Forge desde la PR #45. Usa el conector GitHub David-std y lee íntegro https://github.com/David-std/AWF/blob/feat/s3-peft-training-foundation/docs/handoffs/2026-10-21-S3-PR45-CONTINUATION-COMPLETE.md, el handoff antiguo de PR45, AGENTS.md, ADR-0033 a ADR-0036, arquitectura y trazabilidad. Verifica el HEAD/CI actual de #43, #44 y #45 antes de cambiar nada. La PR #44 es PARALELA y no pertenece al historial de #45. El LoRA de Qwen 0.5B fue entrenado realmente: run privado f4e66e7e8e3b420d8dd74dfab79536fc, 8/8 pasos, recibo/7 hashes verificados y recarga offline. No rehagas ese training ni publiques los datos. Preserva los runs desde Temp y desarrolla el siguiente incremento medible: protocolo de evaluación independiente con derechos y gold, luego base-vs-adapter pareado con control de afirmaciones/citas/negación y holdout no contaminado. Mantén todas las PR en draft, deja CI, docs y comentarios de trazabilidad verificables. Si falta gold, implementa infraestructura y fixtures sin fingir resultados científicos.

---

**Verificación final:** consulta GitHub PR #45/PR #44/CI y lectura de fuente a SHA a0d7a273... + lectura de metadatos SHA/loss/pasos/revisión de archivos locales originales en ASUS_ROG_STRIX. Ningún entrenamiento adicional ni auditoría científica fue realizado durante este handoff.
