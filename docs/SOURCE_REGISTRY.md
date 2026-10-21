# Registro inicial de fuentes y límites de evidencia

Cada entrada indica qué justifica, qué **no** demuestra y en qué etapa debe revalidarse. No se presenta una página comercial como validación independiente de rendimiento. La fuente histórica AWS se gestiona en `docs/PROVENANCE.md`.

| ID | Fuente | Tipo | Uso arquitectónico | Límite |
|---|---|---|---|---|
| SR-01 | [CoEdIT — EMNLP 2023](https://aclanthology.org/2023.findings-emnlp.350/) / [repo](https://github.com/vipulraheja/coedit) | Artículo + código | Baseline de edición instruccional, pares de datos | No implica disponibilidad de todos los textos ni eficiencia ES |
| SR-02 | [mEdIT — NAACL 2024](https://aclanthology.org/2024.naacl-long.56/) / [repo](https://github.com/vipulraheja/medit) | Artículo + código | Transferencia y baseline multilingüe | Medir ámbito académico ES por separado |
| SR-03 | [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | Model card | Modelo neuronal preentrenado candidato | No garantiza mejora al ajustar ni consumo de VRAM |
| SR-04 | [TRL PEFT](https://huggingface.co/docs/trl/en/peft_integration) | Documentación primaria | Implementar SFT/DPO con adaptadores | La librería no valida la calidad del dataset |
| SR-05 | [PEFT/LoRA](https://huggingface.co/docs/peft/index) | Documentación primaria | Ajuste eficiente | Cuantización/QLoRA no hacen determinista al LLM |
| SR-06 | [uv](https://docs.astral.sh/uv/) | Documentación técnica | Gestión de paquetes/lock reproducible | Lock no garantiza reproducibilidad de GPU por sí solo |
| SR-07 | [Ruff](https://docs.astral.sh/ruff/) / [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) | Estándares y guías | Código legible, lint, formato | Usar un formateador canónico, no reglas cosméticas rivales |
| SR-08 | [CQRS pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs) | Documentación de arquitectura | Entender tradeoffs de comando/consulta | No justifica doble BD ni eventual consistency en AWF |
| SR-09 | [MLflow](https://mlflow.org/docs/latest/tracking/) | Documentación técnica | Tracking y model registry posterior | No sustituye model/dataset cards ni control legal |
| SR-10 | [HF Dataset Cards](https://huggingface.co/docs/hub/datasets-cards) | Documentación técnica | Metadatos, usos, limitaciones, licencia | Dataset card no constituye permiso si la licencia falta |
| SR-11 | [StealthHumanizer](https://github.com/rudra496/StealthHumanizer) | Ingeniería abierta del tercero | Interfaces de modelos y pipelines | Scores proxies no validan Turnitin/GPTZero/Pangram |
| SR-12 | [Phrasly Technology](https://phrasly.ai/technology) | Declaración del proveedor | Hipótesis SFT + feedback/RL | No divulga pesos/recompensa/datos; claims no replicación independiente |
| SR-13 | [Docling](https://github.com/docling-project/docling) / [GROBID](https://github.com/kermitt2/grobid) | Código/documentación | Ingesta de documentos/bibliografía | No obligatorio para S0; probar casos reales |
| SR-14 | [Kaggle GPU](https://www.kaggle.com/docs/efficient-gpu-usage) / [Colab](https://research.google.com/colaboratory/faq.html) | Políticas proveedores | Opciones experimentales | Cuotas y GPUs no garantizadas |
| SR-15 | [Runpod GPU](https://www.runpod.io/gpu-models/rtx-4090) / [Modal](https://modal.com/pricing) | Proveedores comerciales | Alquiler eventual | Precio/stock cambian; no gasto comprometido |
| SR-16 | [IteraTeR](https://github.com/vipulraheja/iterater) | Corpus de revisiones | Candidato dataset humano | Revisar licencia/splits/uso para entrenamiento |

## Clasificación obligatoria de una nueva fuente

`INDEPENDENT_STUDY`, `OPEN_DATA`, `VENDOR_DOCUMENTATION`, `VENDOR_BENCHMARK`, `IMPLEMENTATION_SOURCE`, `INTERNAL_EXPERIMENT`, `HYPOTHESIS`. Guardar publicación, experimento y snapshot por separado cuando sea relevante.

**Pendiente:** fichas de literatura con resultados cuantitativos, datasets usados, amenazas de validez, contradicciones y versión exacta. Este registro es un índice inicial, no una revisión sistemática concluida.

## Rights-related source-of-truth research for PR #35

- [SPDX License List](https://spdx.org/licenses/) and
  [SPDX expressions](https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/):
  names and expressions help describe licences but do not prove a particular file's
  owner, applicable licence instrument or the authority of a grantor.
- [Creative Commons licence considerations](https://wiki.creativecommons.org/wiki/Considerations_for_licensors_and_licensees/Licensees):
  read the legal code, not only the human-readable deed; adaptation/commercial
  and version/jurisdiction conditions differ.
- [Hugging Face dataset cards](https://huggingface.co/docs/hub/main/datasets-cards):
  descriptive metadata supports discovery and responsible context, but a card is not
  independently verified chain-of-title evidence or ML training permission.

These references justify **not inferring rights** in AWF; they are not an external
legal opinion or certification of the old AWS ZIP.

## Scientific disagreement methodology (S2 PR #36)

- [JBI Manual for Evidence Synthesis, Critical appraisal (2024)](https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355828247/4.2.7%2BCritical%2Bappraisal).
  Supports independent critical appraisal and consensus/third-reviewer procedures;
  does not certify AWF reviewer credentials or adjudicated scientific claims.
- [JBI Manual, methodological-quality assessment](https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355598976/7.3.6.3%2BAssessment%2Bof%2Bmethodological%2Bquality).
  Requires pre-specified appraisal criteria and documenting reviewer disagreement.
- [PRISMA 2020 expanded checklist](https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf),
  items 8–9. Supports reporting the number and independence of reviewers and how
  disagreement was handled; not evidence for any particular AWF review outcome.

These recommendations inform a **governance analogy**, not validation that two
signing keys represent two independently qualified people. AWF must not
equate a signature with a correct decision or rights grant.

## Methodological basis for third-party arbitration (PR #37)

- [JBI Manual for Evidence Synthesis, section 7.3.6.3](https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355598976/7.3.6.3%2BAssessment%2Bof%2Bmethodological%2Bquality):
  independent appraisal, explicit quality criteria, consensus discussion
  and escalation to a third reviewer if needed.
- [PRISMA 2020 explanation and elaboration (BMJ)](https://www.bmj.com/content/372/bmj.n160):
  reporting how many reviewers worked independently and how differences
  were resolved; automation should be reported and validated.

These guidelines concern transparent research-review methods; they do **not**
certify individual reviewer competence, endorse AWF software, give legal
rights to research sources, or adjudicate a scientific truth claim.

## Source basis for governance in PR #38 (AWF-R040)

- [PRISMA 2020 expanded checklist, items 8–9](https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf):
  document reviewer independence, selection methods and disagreement-resolution
  process; does NOT prescribe an AWF quorum of two or certify individuals.
- [COPE — Ethical guidelines for peer reviewers](https://doi.org/10.24318/2019.1.4):
  competence, confidentiality, transparency and competing-interest duties;
  does NOT verify a particular AWF app user.
- [NIST AI RMF GOVERN 1.4–1.5, 2.1](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/):
  documented policies, monitoring, accountability, roles and responsibilities;
  this is a governance framework, not a scientific arbitration warrant.

These are **design rationale**, not evidence of a real independent custodian
or experimental proof that a specific historical AWS rule is correct.
