# Gestión de Delivery por MVP
### Propuesta metodológica desde el rol de Project Manager / Delivery Manager

**Autor:** Iván — Delivery Manager / Project Manager
**Fecha:** 2026-07-21

---

## 1. Propósito de este documento

Este documento define **cómo se gestiona la ejecución de cada MVP** dentro del método Lean descrito en `/docs/methodology.md` (Captura → Evaluación → Descubrimiento → Diseño → Desarrollo → Validación → Aprendizaje). No reemplaza esa metodología ni la arquitectura técnica de David: la complementa, aportando el sistema de gestión, control y seguimiento que garantiza que el método se cumpla en la práctica y no solo en el papel.


La posición del Delivery/Project Manager en este sistema es la de **guardián del proceso**: no decide qué se construye (eso es de Juan Carlos y del cliente) ni cómo se construye técnicamente (eso es de David y Alejandro), pero sí es responsable de que **nada avance de fase sin cumplir los criterios definidos**, de que **los riesgos y bloqueos se vean a tiempo**, y de que **exista evidencia y trazabilidad** de cada decisión y cada entregable.

Este documento se apoya en un segundo archivo, `checklist-mvp-xxxx.xlsx`, que es la herramienta operativa de control (el "cómo" del día a día). Este documento es el "por qué" y el "cuándo".

---

## 2. Rol del Delivery/Project Manager en el ciclo de vida del MVP

El ciclo de vida definido tiene 7 etapas. La tabla siguiente aterriza qué controla el PM/DM en cada una — no ejecuta el trabajo de cada rol, pero sí valida que el gate de salida de cada etapa esté cumplido antes de dejar avanzar la iniciativa.

| Etapa | Dueño del contenido | Rol del Delivery Manager |
|---|---|---|
| 1. Captura de oportunidades | Juan Carlos (registra), cualquier miembro (propone) | Asegurar que **toda** idea quede en el Backlog de Oportunidades antes de discutirse en reunión. Ninguna idea "de pasillo" entra al Sprint. |
| 2. Evaluación | Juan Carlos + equipo | Facilitar la sesión de evaluación, documentar el resultado (descartada / semilla / experimento / aprobada) y con qué evidencia se decidió. |
| 3. Descubrimiento | Olav (cliente/proceso) + Juan Carlos (negocio) | Verificar que exista evidencia de entrevista/validación antes de autorizar el paso a Diseño. Es el primer gate duro. |
| 4. Diseño | David (arquitectura) + Olav (alcance/historias) | Confirmar que el MVP cumple **Definition of Ready** antes de asignarlo a un Sprint. |
| 5. Desarrollo | Alejandro (+ David, Olav, todo el equipo según el caso) | Dar seguimiento al flujo Issue → Spec → Código → Review → Demo → Done; visibilizar avance y destrabar bloqueos. |
| 6. Validación | Olav + Juan Carlos (cliente real) | Asegurar que la validación con usuario real quede documentada (feedback, problemas, resultados) antes de declarar el MVP "Done". |
| 7. Aprendizaje | Todo el equipo, decide Juan Carlos con el equipo | Facilitar la sesión de cierre/retro y garantizar que la decisión (continuar/iterar/pivotar/cerrar) y el aprendizaje queden documentados y no se pierdan. |

**Principio de gestión:** un MVP no debería llegar a Desarrollo si no cumple Definition of Ready, y no debería marcarse como terminado si no cumple Definition of Done. El Delivery Manager es quien aplica ese "no" cuando corresponde, con datos, no con autoridad jerárquica.

---

## 3. Cadencia de gestión

### 3.1 Reunión semanal (dueño: Delivery Manager)

- **Cuándo:** jueves 10:00 am –1:00 pm.
- **Objetivo:** revisar avance, riesgos, métricas, priorizar el siguiente Sprint y tomar decisiones.
- **Formato de gestión (responsabilidad del DM):**
  1. Agenda enviada con **mínimo 24 h de anticipación**, basada en el estado real del checklist (no en memoria).
  2. Revisión de métricas clave por área (ver sección 5) — no las 17 métricas cada semana, sino el subconjunto vivo esa semana.
  3. Revisión del registro de riesgos: qué entró, qué se cerró, qué escaló.
  4. Decisiones tomadas se registran en el acta el mismo día, con responsable y fecha.

### 3.2 Daily asíncrono (dueño: cada responsable)

- **Cuándo:** todos los días hábiles L-V, **antes de las 9:00 am**.
- **Canal:** chat del equipo (hilo único por día para mantener trazabilidad).
- **Objetivo:** dar visibilidad temprana de avance, plan del día y bloqueos sin convocar reunión.

**Estructura simple de respuesta (copiar/pegar):**

```text
[DAILY - YYYY-MM-DD]
1) Ayer completé:
- ...

2) Hoy haré antes de terminar el día:
- ...

3) Bloqueos / riesgos:
- ... (si no hay, escribir: "Sin bloqueos")

4) Necesito de alguien:
- @nombre - ... (si no aplica, escribir: "No aplica")
```

**Reglas mínimas de operación:**

1. Cada persona publica una sola actualización diaria antes de las 9:00 am.
2. Si aparece un bloqueo crítico, no se espera al cierre del día: se reporta de inmediato en el mismo hilo.
3. El Delivery Manager revisa el hilo a las 9:00 am y consolida bloqueos que requieran escalamiento.

### 3.3 Reuniones adicionales

Se convocan **solo** ante: bloqueo importante, decisión técnica que no puede esperar al miércoles, reunión con cliente, o revisión de arquitectura. El equipo es responsable de que toda reunión adicional tenga agenda previa, objetivo claro, participantes estrictamente necesarios y acuerdos documentados — para proteger el foco del equipo, que es el recurso más escaso en un equipo de 5 personas con dedicación parcial.

### 3.4 Principio Lean aplicado a la cadencia

Cada reunión que no cambia una decisión es desperdicio. El DM debe poder cancelar la semanal si no hay nada que decidir (raro, pero posible) y debe resistir la tentación de agregar reuniones "de seguimiento" que el dashboard puede resolver sin sincronía.

---

## 4. Definition of Ready y Definition of Done — control de gate

El DM no define el contenido de DoR/DoD (eso es un acuerdo de equipo), pero es **responsable de que se aplique como gate real** y no como checklist decorativo.

**Definition of Ready** (mínimo para iniciar una iniciativa):
Cliente identificado · Problema claramente definido · Hipótesis de valor · Responsable asignado · Alcance del MVP definido · Historias priorizadas · Criterios de aceptación definidos · Riesgo principal identificado · Viabilidad con la capacidad disponible del equipo.

**Definition of Done** (mínimo para cerrar una funcionalidad o MVP):
Cumple criterios de aceptación · Funciona correctamente · Revisado técnicamente · Documentado · Evidencia funcional (demo o video) · Desplegado en el ambiente correspondiente · Aprendizajes documentados · Aceptado por el Product Owner.

**Mecanismo de control propuesto:** en el `checklist-mvp-xxx.xlsx`, cada MVP tiene una fila de DoR y una de DoD con verificación por ítem. El DM no permite que un MVP entre a un Sprint si el DoR no está al 100 %, y no lo reporta como "Done" ante el cliente o en el reporte ejecutivo si el DoD no está al 100 %. Las excepciones (por ejemplo, avanzar con un ítem pendiente por decisión de negocio) se documentan explícitamente con quién la autorizó — no se saltan en silencio.

---

## 5. Sistema de seguimiento

El DM mantiene cinco artefactos vivos. Todos deben poder consultarse sin necesidad de preguntar "¿cómo vamos?" en Slack:

| Artefacto | Contenido | Actualización |
|---|---|---|
| Backlog de Oportunidades | Toda idea registrada con problema, cliente, valor esperado, evidencia, fuente | Continua; revisión formal quincenal |
| Roadmap de ejecución | MVPs activos, fase actual, fecha objetivo | Semanal (post-reunión de miércoles) |
| `checklist-mvp.xlsx` | DoR, DoD, entregables por rol, métricas por MVP | Continua, dueño por fila = responsable del entregable |
| Registro de riesgos | Riesgo, impacto, mitigación, estado, fecha de escalamiento | Semanal como mínimo, inmediato si es crítico |
| Actas y decisiones | Acuerdos de cada sprint, con responsable y fecha | Inmediata (mismo día de la reunión) |

### 5.1 Matriz de seguimiento por MVP (plantilla)

| MVP | Fase actual | % DoR cumplido | % DoD cumplido | Próximo hito | Riesgo principal | Responsable | Última actualización |
|---|---|---|---|---|---|---|---|
| MVP-01 | Desarrollo | 100% | 60% | Demo Sprint 3 | Dependencia validación cliente | Alejandro | 2026-07-21 |

Esta fila vive en el Excel adjunto (pestaña "Dashboard") y es la base del **reporte ejecutivo del estado del MVP** que el DM entrega semanalmente.

---

## 6. Métricas: rol del Delivery Manager

El DM no genera todas las métricas — cada rol reporta las suyas — pero es responsable de **consolidarlas, darles cadencia y asegurarse de que se usen para decidir**, no solo para archivar.

| Categoría | Dueño del dato | Cadencia de revisión propuesta |
|---|---|---|
| Negocio | Juan Carlos | Mensual (con tendencia acumulada) |
| Producto | Olav + Alejandro | Quincenal |
| Desarrollo | Alejandro | Semanal |
| IA | Olav | Quincenal |
| Equipo | Delivery Manager | Semanal |

Ver sección 8 (análisis crítico) para los ajustes propuestos a estas métricas y su cadencia.

---

## 7. Gestión de riesgos y escalamiento

Tabla base de riesgos conocidos (heredada del documento de metodología, sección de riesgos):

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Disponibilidad parcial del equipo | Alto | Planificar según capacidad real declarada; limitar trabajo en curso (WIP) |
| Cambios frecuentes de prioridades | Alto | Un solo frente prioritario; nuevas ideas van al Backlog de Oportunidades |
| Alcance excesivo del MVP | Alto | Definir MVP mínimo; validar antes de agregar funcionalidades |
| Dependencia del cliente para validar | Alto | Acordar desde el inicio tiempos y responsables de revisión con cliente |
| Falta de documentación | Medio | Ninguna tarea se cierra sin decisión registrada |
| Retrasos por bloqueos técnicos | Medio | Identificación semanal y escalamiento temprano |
| Desarrollo sin validación de negocio | Alto | Ningún desarrollo inicia sin pasar evaluación y definición del problema |
| Desalineación del equipo | Medio | Revisión semanal de objetivos, avances y responsabilidades |
| Falta de generación de ingresos | Alto | Priorizar iniciativas con cliente identificado y monetización de corto plazo |

**Protocolo de escalamiento propuesto (nuevo, ver sección 8):** todo riesgo marcado "Alto" que permanezca abierto más de 2 semanas se escala automáticamente a reunión adicional, sin esperar al miércoles. El DM es responsable de detectar ese vencimiento, no de esperar a que alguien lo levante.

---

## 8. Análisis crítico y ajustes propuestos

Como Delivery Manager, mi responsabilidad no es solo aplicar el proceso, sino señalar dónde el proceso tal como está definido puede generar fricción, ambigüedad o falta de foco. Estos son los puntos que ajustaría:

**1. El Backlog de Oportunidades no tiene dueño ni cadencia de revisión definida.**
El método dice "toda idea se registra", pero no dice quién lo revisa ni cada cuánto. Sin dueño, se llena y nunca se prioriza. *Propuesta:* Juan Carlos es dueño del contenido, el DM es dueño de la cadencia — revisión quincenal obligatoria, con salida explícita a "descartada / semilla / experimento / aprobada" para cada ítem, no solo para los nuevos.

**2. "Feedback positivo del cliente" y "Precisión de resultados" son métricas cualitativas sin escala definida.**
Tal como están, son subjetivas y no comparables entre MVPs. *Propuesta:* definir "Feedback positivo del cliente" como CSAT 1–5 recolectado en cada sesión de validación, y "Precisión de resultados" (IA) con un umbral numérico acordado por caso de uso (ej. % de respuestas correctas sobre una muestra de referencia).

**3. Faltan métricas de costo/ROI en el bloque de Negocio.**
Se mide "ingresos generados" pero no cuánto cuesta construir cada MVP (tiempo del equipo, herramientas, IA). Sin eso no se puede calcular retorno real ni comparar MVPs entre sí. *Propuesta:* agregar "Costo estimado invertido por MVP" y, cuando aplique, "ROI o payback estimado".

**4. "Compromisos cumplidos" y "Cumplimiento de Sprint Goal" se solapan.**
Ambas miden esencialmente lo mismo desde ángulos distintos y duplican esfuerzo de reporte. *Propuesta:* consolidar en una sola métrica de equipo ("% de compromisos del Sprint cumplidos") y usar "Bloqueos abiertos" y "Velocidad" como las métricas complementarias reales.

**5. "Cobertura documental" y "Bugs críticos" no tienen umbral ni SLA.**
Sin un número objetivo, son difíciles de accionar en la reunión semanal. *Propuesta:* cobertura documental = % de decisiones/specs con documento asociado sobre el total requerido por el DoD; bugs críticos con SLA de resolución (ej. 48–72 h) y alerta automática si se incumple.

**6. El DoR no cuantifica "viable con la capacidad disponible".**
Es el ítem más subjetivo del checklist y el que más se salta bajo presión. *Propuesta:* exigir que quien marca este ítem indique explícitamente cuántas horas/semana tiene disponibles el equipo asignado versus lo que el alcance requiere, aunque sea una estimación gruesa.

**7. No hay definición explícita de "MVP validado con cliente".**
Es una métrica de negocio central pero no tiene criterio de corte. *Propuesta:* definir mínimo (ej. N entrevistas o sesiones de uso real + evidencia de que el problema se resolvió) antes de contar un MVP como "validado".

**8. Cadencia única semanal para todas las métricas genera ruido.**
Revisar métricas de negocio (que cambian lentas) con la misma frecuencia que métricas de equipo (que cambian rápido) diluye la atención en la reunión de miércoles. *Propuesta:* la cadencia diferenciada de la sección 6 — equipo/desarrollo semanal, producto/IA quincenal, negocio mensual — con la reunión semanal mostrando solo lo que cambió.


Estos nueve ajustes están incorporados en el `checklist-mvp.xlsx` adjunto (pestañas de Métricas y DoR/DoD) para que no queden solo como recomendación en un documento, sino como control operativo desde ya.

---

## 9. Matriz RACI resumida

| Actividad | David | Alejandro | Olav | Juan Carlos | Iván (DM) |
|---|---|---|---|---|---|
| Arquitectura del MVP | R/A | C | I | I | I |
| Desarrollo de funcionalidades | C | R/A | C | I | I |
| Descubrimiento con cliente / automatización / product spec | I | I | R/A | C | I |
| Propuesta de valor y GTM | I | I | C | R/A | I |
| Cadencia, riesgos, DoR/DoD, reporte | I | I | I | I | R/A |
| Decisión de continuar/iterar/pivotar/cerrar | C | C | C | C/A | R |

*R = Responsable de ejecutar, A = Aprueba/rinde cuentas, C = Consultado, I = Informado.*

---

## 10. Resultado esperado de este sistema de gestión

El equipo mantiene foco, ritmo y coordinación entre arquitectura, desarrollo, IA y producto, reduciendo bloqueos y asegurando que cada MVP llegue a producción dentro del plazo acordado — con trazabilidad completa de por qué se tomó cada decisión y qué se aprendió, sin depender de la memoria de una persona.
