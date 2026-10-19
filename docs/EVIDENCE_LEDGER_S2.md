# S2 — almacenamiento transaccional privado de evidencias

**Etapa:** infraestructura local de integridad, no verificador de comprensión, verdad académica o autoría.

El módulo `awf.domain.evidence` define los tipos de evento y el hash canónico. El adaptador `awf.adapters.persistence.sqlite_evidence` proporciona operaciones de inicialización, agregación, lectura verificada y auditoría. Su interfaz aparece en `EvidenceStorePort` de `application/ports.py`; la CLI es la raíz de composición.

## Prueba reproducible, con contenido sintético

```powershell
# Dentro de la raíz del repositorio; Python 3.12+ y el código fuente local
$env:PYTHONPATH = (Resolve-Path ./src).Path
# La carpeta .awf se ignora en Git
New-Item -ItemType Directory -Force .awf/evidence | Out-Null
"evidence for a synthetic audit" | Set-Content -Encoding utf8 .awf/evidence/example.txt

python -m awf.cli.main evidence append .awf/evidence/example.txt `
  --kind AUDIT_RECEIPT --run-id run-001 --subject-id DSR-019 `
  --database .awf/evidence/ledger.sqlite

python -m awf.cli.main evidence verify --database .awf/evidence/ledger.sqlite `
  --expected-head "SHA256_HEAD_64_CARACTERES_GUARDADO_APARTE"
```

La salida `append` muestra `evidence_sha256` y `head_digest`. Para detectar restauraciones a un estado anterior, guarda `head_digest` fuera del propio archivo SQLite (por ejemplo en un registro de auditoría autorizado con acceso independiente). Si se pasa un hash incorrecto, `verify` devuelve error y código de salida 2.

Los registros incluyen el contenido de evidencia dentro de SQLite; **no uses documentos reales de terceros ni claves** para la prueba inicial. El directorio `.awf/` no está versionado. Si el equipo comparte el almacenamiento, aplica permisos apropiados y copia de seguridad cifrada por separado.

## Qué se verifica realmente

- Atomicidad evento/bytes y recuperación posterior al reinicio.
- Existencia de cada payload, coincidencia del SHA-256, integridad de cada evento y de sus vínculos, secuencia completa, integridad referencial y contrato de esquema.
- Estado explícito de `external_authenticity_proven: false`, porque un checksum autocontenido no valida firmas, aislamiento ni honestidad de un evaluador.
- Alteraciones y fallos de escritura producen error en vez de un `PASS` silencioso.
- Dos eventos pueden señalar el mismo hash de contenido sin duplicar el objeto.

## Pendientes

El motor de revisión debe almacenar y recuperar sus propios recibos en este puerto, con identidad de sesión/actor confiable y validación de evidencia más allá del hash. Se requiere probar reinicio a mitad de un flujo de generación, rescate de WAL/backup y límites de escalamiento antes de publicar un runtime de producción. El ledger local no sustituye los derechos de uso de fuentes ni el aislamiento de respuestas de holdout.
