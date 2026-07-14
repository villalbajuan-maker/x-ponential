# Pruebas

Esta carpeta está dividida por flujo funcional, no por nombres aleatorios.

Estructura actual:

- `unit/`
- `integration/`
- `api/`
- `fixtures/`

Las primeras muestras de prueba deben ser fragmentos pequeños y representativos de licitaciones, junto con payloads JSON mínimos.

## Regla de oro

- Cada función pura recibe su propio test unitario.
- Cada paso del flujo feliz recibe al menos una prueba enfocada.
- Cada bug importante agrega la regresión más pequeña y útil posible.
- Las muestras de prueba deben seguir siendo pequeñas y reutilizables.
- Evita depender solo de un test gigante de extremo a extremo.
- Si un paso se rompe, los tests de ese paso deben fallar de forma clara y aislada.

## Cobertura visible actual

- `unit/test_company_profile.py`: normalización y persistencia del perfil
- `unit/test_workspace.py`: rutas seguras y helpers del espacio de trabajo
- `unit/test_ocr_helpers.py`: limpieza de texto y helpers de tipo de archivo
- `unit/test_audit.py`: payloads estructurados de eventos de auditoría
- `unit/test_document_service.py`: registro de extracción, revisión y flujo de respuesta faltante
- `unit/test_secop.py`: clasificación del parser de SECOP
- `integration/test_ocr_regex_fixture.py`: extracción con regex desde una muestra tipo licitación
- `api/test_pilot_flow.py`: rutas de raíz, salud, lectura/actualización/importación de perfil, carga, proceso, revisión y respuesta faltante

## Informe canonico de cobertura

- `python -m pytest` regenera `coverage.json` en la raiz del repo.
- El archivo se sobrescribe en cada corrida, asi que no quedan versiones viejas.
- El umbral minimo actual es del `90%`; si baja de ahi, la prueba falla.

## Como deben crecer los tests

- Si cambia una funcion, el test que la cubre debe actualizarse en la misma PR.
- Si aparece un flujo nuevo, primero se agrega el test mas pequeno posible.
- Si el flujo cruza modulos, se suma un test de integracion o de API.
- Si el cambio corrige un bug, se deja una regresion minima.
- Si una parte del repo ya no esta bien protegida por la suite actual, aqui se debe recomendar el siguiente test.

## Recomendacion rapida por modulo

- `core/company_profile.py`: normalizacion, carga, guardado e importacion.
- `core/workspace.py`: nombres seguros, layout, archivo faltante y JSON subido.
- `services/document_service.py`: revision humana, respuestas faltantes y promociones.
- `adapters/ocr_*`: OCR, preprocesado, deteccion regex y despacho por formato.
- `adapters/secop_*`: parsing, cliente, flujo, render y agrupacion.
- `api/routes/*`: contratos HTTP y respuestas de error.
- `api/middleware.py`: request ID, operation ID y trazabilidad estructurada.

## Checklist rapida de cambio

Antes de cerrar una PR, revisa esto:

- Si cambias `core`, actualiza el test unitario correspondiente.
- Si cambias `services`, confirma que haya un test del caso feliz y uno de error.
- Si cambias `adapters`, agrega o ajusta pruebas con fixtures minimos.
- Si cambias `api`, actualiza contrato, headers, errores y serializacion.
- Si cambias un flujo nuevo, crea primero el test minimo y luego amplialo por bordes.
- Si corriges un bug, deja una regresion pequena que falle sin la correccion.
- Si alteras datos compartidos, revisa los tests que leen esos fixtures.
- Si el cambio toca varios modulos, agrega al menos un test de integracion.

## Primeros flujos por cubrir

- perfil de la empresa
- importación JSON
- carga y nomenclatura de archivos
- extracción de texto
- detección de campos con regex
- punto de control de revisión
- verificación de salud
- un flujo liviano de extremo a extremo

Cada bug importante debe agregar el test más pequeño y útil posible.
