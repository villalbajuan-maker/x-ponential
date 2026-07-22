# Reunion: Automatización de licitaciones y formatos

## Fecha

2026-07-17

## Participantes

- Juan Carlos Villalba
- David Gallego
- Hector Alejandro Montes Lobaton
- Alexis Rodriguez

## Proposito de la reunion

Revision tecnica y comercial para automatizar procesos de licitacion y reconstruccion de formatos, definir prioridades de desarrollo para Business Bridge y alinear el modelo de negocio.

## Temas tratados

**Identificacion de pliegos amañados**
Se discutio como detectar pliegos cerrados o amañados, identificando especificaciones que referencian marcas concretas como señal de riesgo contractual y practica anticompetitiva. Se ejemplifico con una especificacion tecnica que obliga a comprar un equipo de marca especifica.

**Experiencia y volumen de licitaciones**
Alexis detalló su trayectoria reciente en licitaciones en Colombia, cuantificando la participacion total en cientos de procesos y diferenciando entre su rol personal y el aporte de empresas asociadas.

**Business Bridge: equipo y propuesta de valor**
Se presento Business Bridge como un servicio que acompaña a pymes en procesos licitatorios para romper practicas monopolicas, describiendo la combinacion de estructuracion financiera, tecnica y soporte juridico. La eficiencia de adjudicacion subio de 10% a 30% en seis meses. El equipo maneja actualmente 33 formatos distintos.

**Gobernanza de IA y ecosistema cloud**
Se expuso la necesidad de gobernanza para integrar multiples herramientas de IA en un ecosistema cloud mediante conectores, plugins y skills, convirtiendo las operaciones en una fabrica digital supervisada por expertos.

**Procesos clave y brechas tecnologicas**
Se identificaron los procesos clave de la cadena de licitacion (busqueda, perfilamiento, match de idoneidad, llenado de formatos, calculo de precio y analisis de pliegos). El llenado de la oferta economica fue identificado como la brecha no resuelta por terceros y la prioridad para desarrollo propio.

**Biblioteca de capacidades y prioridades de desarrollo**
Se acordo construir una biblioteca modular de capacidades priorizando el modulo documental (lectura y llenado de PDFs) como primer entregable.

**KPIs y aprendizaje de IA**
Alexis propuso KPIs de masificacion y tasa de adjudicacion. Se discutio que la IA debe aprender, razonar e interactuar para reducir la carga cognitiva mediante interfaces conversacionales y semantica etiquetada.

**Modelo de negocio y oportunidad de consolidacion**
Se discutio la fragmentacion del mercado y la oportunidad de consolidar las piezas en una "fabrica" operativa que permita monetizar. La validacion con indicadores elevaria el valor del negocio para inversion o venta. Alexis confirmo que la estrategia contempla tanto uso interno como comercializacion a terceros.

**Progreso tecnico del modulo de llenado de formatos**
Se reviso el estado del modulo que convierte PDFs en plantillas editables y compara datos de empresa con la plantilla para auto-llenar campos. Requiere integracion con herramientas de contexto y pruebas en vivo. Tecnicamente se necesita un JSON con coordenadas y etiquetas para mapear campos del PDF.

**Reconstruccion automatica del formato**
Alexis describio el flujo manual actual (copiar encabezados como imagen, pegar y modificar) y la necesidad de automatizarlo. Se acordo priorizar recrear el documento visualmente en vez de hacerlo editable por plantilla, cubriendo asi el 80% de los problemas de traspaso de informacion.

**Arquitectura tecnica: skill en Python para documentos Word**
Se acordo que un skill en Python que convierta y construya documentos Word es el componente tecnico requerido, mientras el modelo de lenguaje actua como soporte periferico para evitar alucinaciones.

## Acuerdos

- Priorizar el lector y llenador de PDFs como primer modulo de desarrollo.
- Construir una biblioteca modular de capacidades comenzando por el modulo documental.
- Business Bridge es el vehiculo comercial del know-how tecnico desarrollado.
- La solucion tecnica preferida es recrear el documento visualmente (no editar el PDF original).
- El skill en Python para construir documentos Word sera el componente central del modulo documental.

## Decisiones

- El primer frente de trabajo es el lector y llenador de PDFs.
- Se usara un JSON con coordenadas y etiquetas como requisito tecnico para mapeo de campos.
- Se comercializara tanto internamente como a terceros.
- Los casos de exito internos seran la base para vender a clientes externos.

## Preguntas abiertas

- ¿Como se estructura el frente de deteccion de pliegos amañados como oportunidad de IP?
- ¿Cual es el modelo de pricing para comercializar la solucion a terceros?
- ¿Como se integran las herramientas actuales (Gemini, Notebook, Google Workspace) con la biblioteca de capacidades?

## Proximas acciones

| Accion | Responsable | Fecha objetivo | Estado |
| --- | --- | --- | --- |
| Realizar pruebas del modulo de llenado usando archivos de contexto (JSON) y un PDF de prueba para validar coordenadas y mapeo de campos | Hector Alejandro Montes Lobaton | Pendiente | Pendiente |
| Enviar el documento "Anexo 8" u otro PDF de ejemplo al equipo para realizar la prueba de llenado y transcripcion | Alexis Rodriguez | Pendiente | Pendiente |
| Investigar y reportar el costo actual de las licencias recurrentes usadas por el equipo (Workspace y otras herramientas) | Juan Carlos Villalba | Pendiente | Pendiente |
| Priorizar el esfuerzo del equipo para enfocar el desarrollo en la lectura y llenado de PDFs como primer frente de trabajo | David Gallego | Pendiente | Pendiente |
| Crear un skill en Python que convierta y construya documentos Word con parametros definidos para integrar la extraccion de texto y la reconstruccion del formato | Juan Carlos Villalba | Pendiente | Pendiente |
