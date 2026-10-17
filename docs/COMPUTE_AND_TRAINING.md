# Estrategia de cómputo y entrenamiento

## Información aportada por el usuario (2026-10-17)

- GPU local: **NVIDIA GeForce RTX 4050**; VRAM exacta y demás especificaciones aún no confirmadas.
- El usuario ya ejecutó **Qwen** localmente sin problemas de inferencia. No equivale a haber probado QLoRA, lotes grandes, contextos largos ni fine-tuning.
- Cuenta con **Google AI Pro** y manifiesta acceso a cómputo de notebooks de Google. La elegibilidad, duración de sesión, tipo GPU, cuota de Colab y políticas de uso deben comprobarse en cada entorno; no asumir garantía ilimitada ni que la suscripción equivalga automáticamente a GPU dedicada.

## Política por sprint

S0–S3: CPU suficiente; sin compra, API comercial ni cuota de GPU obligatoria. S4: probar inferencia local con checkpoint, tokenizer, versión CUDA/PyTorch, dtype, cuantización y perfil real. S5: realizar piloto LoRA/QLoRA de pocos pasos, registrar VRAM pico, tiempo/paso, OOM, secuencia, batch, precisión, semilla y costo si hubo alquiler. Solo entonces elegir Colab/Notebook o alquiler.

## Experimentos y trazabilidad

Cada run ML almacena: `run_id`, commit, dataset_manifest_sha256, split grupo, licencias, checkpoint/revisión, tokenizer, PEFT config, seed, framework/CUDA, GPU, parámetros de decoding y tiempos. Nunca subir pesos, tokens, ejemplos privados o checkpoints a Git; el manifest apunta a almacenamiento controlado.

## Criterios de selección

- Qwen3-4B es **candidato**, no vencedor predesignado.
- CoEdIT/mEdIT son baselines de edición; revisar licencias antes de descargar/entrenar/redistribuir.
- Si un modelo pequeño es suficiente por calidad/memoria/latencia medida, preferirlo al grande.
- SFT antes que DPO; DPO solo si preferencias independientes aportan mejora medible; RL completo no es requisito.
- Pruebas de rendimiento y calidad separadas: un modelo más rápido puede ser peor editor.

## Riesgos no resueltos

Capacidad de VRAM, cuotas gratuitas reales, confidencialidad de documentos, licencia de outputs de APIs externas y costos variables de almacenamiento/red. Resolver antes de activar rutas externas o entrenamiento masivo.
