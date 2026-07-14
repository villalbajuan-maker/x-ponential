# Especificaciones

Este repositorio usa trabajo guiado por especificaciones.

Cada cambio importante debe comenzar en su propia carpeta de funcionalidad dentro de `specs/`.

## Archivos estándar

- `spec.md`
- `plan.md`
- `tasks.md`
- `checklist.md`

Archivos opcionales:

- `open-questions.md`
- `risks.md`
- `migration.md`

## Reglas

- Una funcionalidad por carpeta.
- No escribir código antes de tener una especificación aprobada.
- Mantén las especificaciones cerca del código que describen.
- Si una funcionalidad afecta al piloto, indica exactamente qué archivos y qué paso del flujo cambian.
- Si una funcionalidad introduce pruebas, la especificación debe describir las muestras esperadas y la ruta de validación.

## Primeras áreas sugeridas

- perfil de la empresa
- carga de archivos
- extracción de texto
- detección de campos
- revisión humana
- migración desde `mvp/` hacia `src/business_bridge/`
