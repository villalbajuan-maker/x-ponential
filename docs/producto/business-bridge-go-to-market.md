# Business Bridge - Producto, mercado y go-to-market

## Proposito del documento

Este documento ordena el frente de producto, mercado y go-to-market para el piloto de Business Bridge.

Su objetivo es convertir la oportunidad en una propuesta evaluable: clara en problema, cliente, alcance, valor, monetizacion preliminar y criterios de decision.

Este trabajo complementa la revision tecnica del MVP, la estimacion de esfuerzo y la definicion operativa del equipo. No reemplaza arquitectura, desarrollo, IA, OCR, datos ni metodologia specs.

## Punto de partida

Business Bridge representa una oportunidad concreta porque existe un cliente identificado, un dolor operativo real, material documental disponible y una primera exploracion tecnica alrededor de automatizacion de licitaciones.

El objetivo no debe ser construir desde el inicio una plataforma completa de gestion licitatoria. El primer paso debe ser validar si podemos convertir un dolor documental especifico en un piloto acotado, medible, vendible y potencialmente repetible.

## Problema

Las empresas y consultoras que participan en licitaciones publicas en Colombia pierden una cantidad desproporcionada de tiempo y esfuerzo re-digitando y reformateando informacion que ya poseen, para adaptarla a los formularios y anexos que cada entidad estatal define de manera distinta.

No es principalmente un problema de falta de informacion. Es un problema de baja estandarizacion entre entidades, carga documental variable, procesos manuales de transcripcion y alta exigencia de verificacion.

El problema tampoco parece estar en encontrar la licitacion. Ese frente ya esta mejor cubierto por otras herramientas. El dolor principal esta en preparar el expediente: convertir datos corporativos dispersos o recurrentes en el formato exacto que exige cada pliego, sin errores y dentro del tiempo disponible.

### Dolor observado

- Lectura de pliegos extensos, heterogeneos y, en ocasiones, disponibles como PDF escaneado sin capa de texto.
- Identificacion manual de requisitos habilitantes, anexos obligatorios, formatos y condiciones particulares de cada proceso.
- Re-transcripcion de informacion corporativa recurrente en formularios distintos: NIT, datos legales, indicadores financieros, experiencia, personal, certificaciones y soportes.
- Diligenciamiento repetitivo, de bajo valor agregado y propenso a errores por fatiga, presion de tiempo o diferencias de formato.
- Validacion de datos duros, como cifras, fechas y vigencias, donde una inconsistencia puede poner en riesgo la propuesta.
- Armado final del expediente en el orden y formato exigido.
- Revision humana indispensable sobre documentos que hoy se construyen casi desde cero, no sobre un borrador previamente organizado.
- Dependencia de criterio experto para revisar cumplimiento y evitar omisiones.
- Dificultad para escalar el numero de procesos atendidos sin aumentar proporcionalmente la carga operativa.

### Impacto del problema

- Tiempo: el reporte de validacion cita entre 8 y 30 horas por propuesta en re-digitacion y hasta 40 a 200 horas para expedientes complejos.
- Costo operativo: preparar propuestas consume tiempo cualificado y genera costos indirectos relevantes, especialmente cuando hay varios procesos simultaneos.
- Riesgo de error: informacion inexacta o incompleta puede ser causal de rechazo o inhabilitacion.
- Riesgo de rechazo: referencias internacionales citadas en el reporte muestran porcentajes relevantes de propuestas rechazadas por errores de cumplimiento documental.
- Perdida de oportunidades: algunas empresas pueden descartar procesos por falta de tiempo para prepararlos, no necesariamente por falta de capacidad para ejecutarlos.
- Dependencia de conocimiento experto: el saber operativo vive en personas y consultores, no en un sistema replicable.
- Dificultad para escalar: una empresa o consultora no puede atender mas procesos simultaneos sin sumar personas o sin aceptar mayor riesgo operativo.

### Evidencia del problema

#### Evidencia fuerte

- Informacion inexacta o incompleta como causal de rechazo o inhabilitacion, segun doctrina de Colombia Compra Eficiente citada en el reporte.
- Estudios academicos que identifican la carga documental como barrera estructural para MiPymes.
- Existencia de consultoras colombianas que cobran por resolver manualmente este problema, lo que sugiere que el mercado ya paga por una solucion artesanal.
- Volumen relevante de contratacion publica en Colombia y presencia de miles de proponentes activos, lo que confirma que el problema ocurre a escala.

#### Evidencia estimada

- El tamano del mercado direccionable en Colombia es una estimacion bottom-up, no una cifra publicada como estudio especifico del nicho.
- Las horas perdidas por duplicidad de informacion provienen de benchmarks, fuentes comparables y lectura del ecosistema, no de una encuesta formal al segmento colombiano.

#### Hipotesis por validar

- Que las horas reales perdidas por Business Bridge coincidan con los rangos observados en la investigacion.
- Que Business Bridge y clientes similares tengan disposicion real a pagar por reducir este dolor.
- Que exista tolerancia a documentos pre-generados o asistidos por IA en un proceso legalmente sensible, siempre con revision humana.
- Que el dolor sea suficientemente recurrente para convertirse en producto o servicio repetible, y no solo en consultoria a medida.

### Hipotesis de problema

Si Business Bridge pudiera estructurar informacion base del proponente, identificar requisitos recurrentes, cruzar esa informacion contra los documentos del proceso, senalar faltantes y asistir el diligenciamiento de formatos con revision humana obligatoria, podria reducir tiempo, friccion y riesgo en la preparacion documental de licitaciones.

La hipotesis no es reemplazar el criterio experto ni automatizar la radicacion completa. Es convertir el trabajo mecanico y repetitivo en un flujo asistido, trazable y revisable, para que el esfuerzo humano se concentre en validar calidad, cumplimiento y decisiones sensibles.

### Preguntas pendientes para Business Bridge

Para validar la magnitud real del problema en la operacion del cliente, necesitamos responder:

1. Cuantas licitaciones revisan, presentan y descartan al mes?
2. Cuantas licitaciones descartan por falta de tiempo para prepararlas?
3. Cuantas horas toma hoy preparar un expediente documental promedio?
4. Que proporcion del tiempo se va en lectura del pliego, transcripcion, diligenciamiento, validacion y armado final?
5. Que informacion corporativa se repite en casi todos los procesos?
6. Quien mantiene actualizada esa informacion y donde vive actualmente?
7. Han perdido o han sido descalificados por errores documentales en el ultimo ano?
8. Que errores generan mayor riesgo: fechas, cifras, documentos vencidos, requisitos omitidos, anexos incompletos u otros?
9. Cual es el maximo de procesos simultaneos que pueden atender con el equipo actual?
10. Que herramienta o metodo usan hoy: Excel, Word, plantillas, checklists, ChatGPT, consultores u otros?
11. Que parte del proceso confiarian en probar primero con asistencia de IA?
12. Que resultado tendria que ocurrir para que consideren que el piloto resolvio un dolor real?

## Cliente objetivo

El cliente inicial es Business Bridge como empresa que ya participa o acompana procesos licitatorios y experimenta friccion documental dentro de su operacion.

Para evaluar repetibilidad, el cliente objetivo ampliado podria incluir organizaciones que participan recurrentemente en contratacion publica o privada y que enfrentan carga documental similar.

### Segmentos potenciales

- Consultores de contratacion publica.
- Empresas proveedoras recurrentes del Estado.
- Firmas que acompanen a terceros en procesos licitatorios.
- Empresas de servicios profesionales con participacion frecuente en licitaciones.
- Empresas de tecnologia, salud, educacion, infraestructura o consultoria con alta carga documental.

## Buyer persona inicial

### Comprador probable

Persona responsable de aumentar capacidad operativa, mejorar eficiencia documental o reducir riesgo en procesos licitatorios.

Puede ser gerente, socio, director de operaciones, lider comercial, lider de licitaciones o responsable de desarrollo de negocio.

### Usuario probable

Persona que prepara, revisa, diligencia o consolida los documentos del proceso licitatorio.

Puede ser analista de licitaciones, asistente juridico, asistente comercial, consultor documental, coordinador de propuestas o profesional encargado de preparar anexos y soportes.

### Diferencia clave

El comprador busca capacidad, velocidad, reduccion de riesgo y retorno. El usuario busca menos carga manual, menos reproceso, claridad sobre pendientes y facilidad para armar el paquete documental.

## ICP inicial

El perfil de cliente ideal inicial no deberia ser cualquier empresa que licita. Debe ser una organizacion con dolor recurrente, volumen suficiente y disposicion a pagar por reducir friccion documental.

### Criterios iniciales de ICP

- Participa o acompana licitaciones de forma recurrente.
- Maneja varios procesos al mes o tiene aspiracion de aumentar volumen.
- Tiene carga documental repetitiva.
- Usa informacion base del proponente de forma recurrente.
- Sufre errores, reprocesos, demoras o dependencia de expertos.
- Tiene capacidad de pago para piloto o servicio acotado.
- Puede entregar documentos reales para validar.
- Acepta un flujo con revision humana y no espera automatizacion total inmediata.

## Propuesta de valor inicial

Ayudar a Business Bridge a reducir friccion documental en procesos licitatorios mediante un piloto asistido que permita identificar requisitos, organizar informacion del proponente, apoyar el diligenciamiento de formatos y mantener control humano sobre la calidad del paquete documental.

### Promesa responsable

No prometer automatizacion total del proceso licitatorio en la primera version.

La promesa inicial debe enfocarse en:

- ordenar el flujo documental,
- reducir tiempo de revision y diligenciamiento,
- disminuir riesgo de omisiones,
- reutilizar informacion recurrente,
- generar trazabilidad sobre hallazgos y pendientes,
- validar si el proceso puede convertirse en activo repetible.

## Alcance preliminar del piloto

El piloto debe ser acotado para evitar construir un producto completo antes de validar valor.

### Alcance recomendado

Trabajar sobre una muestra limitada de procesos reales de Business Bridge para construir una primera version asistida del flujo documental.

El piloto podria incluir:

- Carga de documentos de licitacion.
- Extraccion inicial de requisitos y anexos.
- Identificacion de campos recurrentes.
- Registro estructurado de informacion base del proponente.
- Apoyo al diligenciamiento de formatos priorizados.
- Checklist de cumplimiento documental.
- Revision humana obligatoria antes de cualquier entrega.
- Reporte simple de hallazgos, pendientes y riesgos.

### Fuera de alcance inicial

- Automatizacion total de licitaciones.
- Presentacion automatica ante plataformas externas.
- Sustitucion completa del criterio experto.
- Multitenancy avanzado.
- Producto SaaS completo.
- Integraciones extensas no necesarias para validar valor.

## Empaquetamiento comercial preliminar

La primera oferta no deberia venderse como plataforma completa. Deberia venderse como piloto asistido de automatizacion documental para licitaciones.

### Nombre de trabajo

Piloto asistido de automatizacion documental para licitaciones.

### Que se vende

Un experimento acotado para reducir friccion documental en una muestra real de procesos licitatorios, con entregables verificables y criterios claros para decidir si avanzar a una siguiente fase.

### Que recibe el cliente

- Diagnostico documental inicial.
- Mapa de requisitos y anexos recurrentes.
- Primer flujo asistido de carga, extraccion y revision.
- Checklist documental.
- Priorizacion de formatos automatizables.
- Recomendacion de siguiente fase.

## Pricing preliminar

El precio no deberia definirse solo por horas de desarrollo. Debe considerar valor para el cliente, esfuerzo tecnico, riesgo, aprendizaje, posibilidad de caja y potencial de reutilizacion.

### Opciones iniciales

1. Piloto pago acotado.
   - Precio fijo por alcance limitado.
   - Adecuado si el cliente acepta validar valor con entregables concretos.

2. Servicio de diagnostico + prototipo.
   - Primera fase mas consultiva.
   - Adecuado si todavia falta claridad sobre alcance y datos.

3. Piloto con descuento estrategico.
   - Menor caja inicial, pero con derecho a caso de uso, aprendizaje y posible continuidad.
   - Solo tendria sentido si el equipo obtiene valor claro de validacion.

### Pendiente

Definir rango de precio despues de validar:

- alcance exacto,
- cantidad de documentos,
- numero de formatos priorizados,
- esfuerzo tecnico estimado,
- nivel de acompanamiento requerido,
- disponibilidad del cliente para interactuar,
- valor economico del dolor para Business Bridge.

## Supuestos

- Business Bridge tiene dolor documental suficiente para pagar por una solucion acotada.
- La muestra documental disponible representa bien el problema real.
- El equipo puede entregar una primera version util sin construir un producto completo.
- El flujo con revision humana sera aceptable para el cliente.
- Parte de lo construido podra reutilizarse en otros clientes o segmentos.
- El piloto puede generar aprendizaje comercial, tecnico y operativo.

## Riesgos

- Prometer automatizacion total antes de tener capacidad suficiente.
- Subestimar la variabilidad documental entre procesos.
- Confundir prototipo funcional con producto listo para produccion.
- Construir demasiado para un solo cliente sin validar repetibilidad.
- No definir responsables, alcance, entregables y criterios de aceptacion.
- No obtener disponibilidad suficiente del cliente para validar el flujo.
- Que el dolor sea real pero no suficientemente monetizable.

## Criterios de decision

Para avanzar con una propuesta de piloto, deberiamos poder responder positivamente la mayoria de estas preguntas:

- Hay un problema claro y urgente para Business Bridge?
- Existe una muestra documental suficiente para validar?
- El alcance puede acotarse sin perder valor?
- El cliente entiende que el piloto incluye revision humana?
- Podemos definir entregables verificables?
- Hay responsable tecnico, responsable de producto/mercado y responsable de relacion con cliente?
- El esfuerzo estimado es compatible con la disponibilidad real del equipo?
- Existe una logica de cobro razonable?
- Lo aprendido puede convertirse en activo reutilizable?

## Siguiente trabajo de Juan

1. Sintetizar el problema desde la perspectiva del cliente.
2. Afinar buyer persona e ICP inicial.
3. Traducir el MVP en una oferta entendible para Business Bridge.
4. Proponer alcance comercial del piloto.
5. Construir primera logica de pricing.
6. Definir preguntas pendientes para validar con Business Bridge.
7. Preparar una recomendacion de avance, pausa o reformulacion.

## Relacion con otros insumos

- Issue principal: #11
- Reporte ejecutivo de investigacion de mercado: `docs/materiales/business-bridge/Reporte_Ejecutivo_Automatizacion_Licitaciones_Colombia.pdf`
- Analisis de esfuerzo: `docs/materiales/business-bridge/analisis_esfuerzos.pdf`
- MVP inicial: `mvp/`
