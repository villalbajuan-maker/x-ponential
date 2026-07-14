# Paquete `business_bridge`

Este será el paquete de código canónico para Business Bridge.

## Capas

- `core/`: reglas de dominio y estructuras compartidas
- `services/`: flujos de aplicación y casos de uso
- `adapters/`: sistema de archivos, OCR, SECOP y otras integraciones externas
- `api/`: puntos de entrada HTTP, módulos de rutas y entrega de la interfaz
- `cli/`: puntos de entrada de línea de comandos

## Regla de migración

El runtime ahora vive en `src/business_bridge/api/`, y la lógica reutilizable debe moverse a este paquete paso a paso.

## Descomposición actual

- `adapters/ocr.py` y `adapters/secop.py` son fachadas de compatibilidad.
- La implementación de OCR vive en `adapters/ocr_text.py`, `adapters/ocr_extractors.py` y `adapters/ocr_detection.py`.
- La implementación de SECOP vive en `adapters/secop_constants.py`, `adapters/secop_utils.py`, `adapters/secop_models.py`, `adapters/secop_client.py`, `adapters/secop_parsing.py`, `adapters/secop_flow.py` y `adapters/secop_render.py`.
- Los manejadores de FastAPI viven en `api/routes/`.
