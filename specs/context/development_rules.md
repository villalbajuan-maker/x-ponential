# Development Rules

Este archivo define las reglas vivas del proyecto Business Bridge.
Su objetivo es que el agente y el equipo trabajen con una sola referencia clara,
sin mezclar nombres viejos, flujos viejos o decisiones sueltas.

## 1. Identidad del proyecto

- El nombre vigente del proyecto es `Business Bridge`.
- Cualquier referencia vieja a `SEASIM` o a otros nombres anteriores debe migrarse a `Business Bridge` cuando toque el codigo, los docs o las rutas.
- Los archivos, carpetas y textos deben mantener la nomenclatura actual del proyecto.
- El codigo nuevo debe usar nombres claros, cortos y coherentes con el dominio del negocio.

## 2. Fuente de verdad

- El codigo canonico vive en `src/business_bridge/`.
- Las especificaciones viven en `specs/`.
- Los README deben permanecer en espanol y describir el estado real del repo.
- Si un documento dice algo distinto al codigo, el documento debe actualizarse o marcarse como obsoleto.

## 3. Estructura tecnica

- La logica debe ir dividida por responsabilidad.
- `core/` contiene reglas de dominio y helpers compartidos.
- `services/` contiene orquestacion de casos de uso.
- `adapters/` contiene integraciones, parseadores y compatibilidad temporal.
- `api/` contiene rutas, schemas, runtime y middleware.
- `tests/` debe reflejar la estructura funcional del codigo.
- Si una funcion crece demasiado, se debe partir en funciones pequenas y testeables.

## 4. Regla de modularidad

- No dejar funciones gigantes en archivos canonicos.
- Desmenuzar cualquier flujo complejo en piezas pequenas y auditables.
- Cada pieza debe poder ser testeada de forma independiente.
- Si aparece una funcion duplicada, se busca un unico lugar canonico para la implementacion.
- Las fachadas de compatibilidad solo deben existir mientras haya imports viejos o transicion real.

## 5. Reglas de pruebas

- Cada funcion pura debe tener su test unitario.
- Cada paso del flujo debe tener al menos un caso feliz.
- Cada bug importante debe dejar una regresion minima.
- Los fixtures deben ser pequenos y reutilizables.
- No depender solo de un test gigante de extremo a extremo.
- Si cambia una funcion, su test debe actualizarse en la misma PR.
- Si aparece un flujo nuevo, se debe recomendar y crear el test minimo que lo cubra.
- Si un cambio toca varios modulos, debe haber al menos un test de integracion.
- Si una prueba no falla al mutar un dato importante, esa prueba es debil.

## 6. Cobertura y calidad

- La cobertura canonicamente visible vive en `coverage.json`.
- El archivo se regenera en cada corrida y no se versionan historicos viejos.
- La misma suite debe correr localmente y en CI.
- La cobertura no es solo un numero: debe proteger comportamientos reales.
- El umbral minimo actual debe mantenerse en linea con el estado real del repo y subir por etapas.
- Si la cobertura baja o un flujo nuevo queda sin proteccion, primero se agregan pruebas y luego se sube el umbral.

## 7. Logging y trazabilidad

- No usar `print` para depuracion permanente.
- El logging debe ser estructurado cuando se trate de flujos de negocio.
- Cada request importante debe tener `request_id` y `operation_id`.
- Los eventos deben incluir contexto util para auditoria.
- Los errores no deben ocultarse con `except: pass`.
- Si un error se captura, debe quedar registro suficiente para reconstruir lo ocurrido.

## 8. API y contratos

- Las rutas FastAPI deben mantener contratos claros.
- Los codigos de error deben ser explicitamente esperados por los tests.
- Los headers de correlacion deben mantenerse consistentes.
- La serializacion debe ser estable y predecible.
- Si cambia un endpoint, se actualiza su test de API y cualquier fixture asociado.

## 9. Datos y archivos

- Los fixtures deben ser pequenos, representativos y faciles de leer.
- Los archivos de ejemplo no deben crecer sin necesidad.
- Las rutas de archivo deben mantenerse seguras.
- Los nombres de archivos subidos deben normalizarse.
- El proyecto no debe depender de archivos temporales ni caches para funcionar.

## 10. Dependencias y entorno

- Las dependencias deben ir fijadas o bloqueadas cuando sea posible.
- `requirements.lock.txt` debe estar alineado con `pyproject.toml`.
- La CI debe usar las mismas herramientas que el entorno local.
- No introducir dependencias nuevas sin una razon tecnica clara.
- Si una dependencia cambia, validar antes la suite y la compatibilidad.

## 11. Documentacion

- Todo cambio importante debe dejar rastros en documentacion.
- Los README deben seguir en espanol.
- Si aparece un flujo nuevo, debe actualizarse la documentacion que lo explica.
- Si se corrige una confusion recurrente, debe quedar documentada en el lugar mas visible.
- Los documentos vivos deben reflejar el estado actual, no solo el historico.

## 12. Flujo de trabajo

- Antes de cambiar codigo, entender el archivo y su responsabilidad.
- Antes de cerrar una PR, revisar si el cambio necesita pruebas nuevas o pruebas actualizadas.
- Si el cambio altera un flujo, ejecutar la suite completa.
- Si el cambio toca multiples modulos, revisar cobertura por modulo.
- Si el cambio es grande, preferir entregas pequenas y verificables.

## 13. Reglas para el agente

- No asumir que algo esta bien si el codigo o la documentacion lo contradicen.
- No borrar cambios del usuario sin permiso.
- No crear soluciones paralelas cuando ya existe una estructura canonica.
- No dejar codigo duplicado cuando se pueda centralizar.
- No dejar una tarea a medias si se puede validar en la misma sesion.
- Si un cambio necesita nuevos tests, proponerlos y, si es posible, crearlos.

## 14. Nuevos flujos

Cuando aparezca un flujo nuevo en el proyecto:

- crear el fixture minimo
- agregar el test del caso feliz
- agregar el borde mas probable
- agregar regresion si hubo bug
- actualizar este archivo si la regla general cambia
- actualizar `tests/README.md` para que el equipo vea el nuevo alcance

## 15. Checklist de cambio

Antes de dar por terminado un cambio:

- [ ] el codigo compila o pasa lint
- [ ] la suite relevante corre sin fallos
- [ ] los tests nuevos o existentes cubren el cambio
- [ ] la cobertura sigue siendo util y actual
- [ ] la documentacion fue actualizada si el flujo cambio
- [ ] no quedaron nombres viejos visibles en el area tocada
- [ ] no quedaron caches o artefactos temporales nuevos

## 16. Criterio de evolucion

Este archivo debe crecer con el proyecto.
Si una nueva decision se repite varias veces, debe quedar escrita aqui.
Si una regla deja de servir, debe actualizarse.
Si una practica se vuelve canonica, debe moverse de la conversacion al documento.
