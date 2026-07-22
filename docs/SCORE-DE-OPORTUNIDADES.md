# Score de oportunidades X-ponential

## Estado

Version congelada v1.0.

## Proposito

Este documento define la metodologia formal para evaluar oportunidades, proyectos, MVPs o iniciativas que puedan requerir foco, tiempo, reputacion, capital, capacidad tecnica o energia del equipo X-ponential.

No busca reemplazar el criterio del equipo. Busca ordenar la conversacion para decidir con evidencia, proporcion y responsabilidad.

La pregunta central no es solamente:

> Que tan buena parece esta idea?

La pregunta correcta es:

> Esta oportunidad merece recursos del equipo en este momento?

## Principio base

No toda oportunidad rentable es una buena oportunidad para X-ponential. Y no toda oportunidad valiosa debe monetizar desde el primer dia.

El portafolio debe equilibrar caja, aprendizaje, activos, capital e impacto, sin comprometer integridad, reputacion, salud, familia, fe, independencia responsable ni excelencia tecnica.

## Flujo de decision

Toda oportunidad que aspire a recibir recursos relevantes del equipo debe pasar por cuatro pasos:

1. Filtros no negociables.
2. Score ponderado de oportunidad.
3. Matriz esfuerzo vs ingreso.
4. Decision y siguiente puerta de revision.

## 1. Filtros no negociables

Antes de puntuar, la oportunidad debe pasar estos filtros.

Si falla uno de forma grave, la oportunidad no deberia avanzar aunque tenga buen puntaje comercial.

| Filtro | Pregunta |
| --- | --- |
| Integridad | Depende de engano, abuso, manipulacion, opacidad o aprovechamiento indebido? |
| Reputacion | Puede comprometer la reputacion colectiva por promesas exageradas, atajos o alianzas incompatibles? |
| Salud y vida sostenible | Exige normalizar deterioro de salud, familia o vida personal del equipo? |
| Fe y conciencia | La decision puede sostenerse delante de las convicciones profundas del equipo? |
| Independencia responsable | Nos ata a clientes, capital o agendas que no podemos respaldar? |
| Excelencia tecnica | Puede validarse simple, pero sin negligencia tecnica? |
| Riesgo legal / regulatorio | El riesgo es identificable, controlable y proporcional al aprendizaje esperado? |
| Promesa responsable | Estamos prometiendo algo que realmente podemos sostener con calidad? |

Resultado posible:

- **Pasa**: puede entrar al score.
- **Pasa condicionado**: puede entrar al score, pero con restricciones explicitas.
- **No pasa**: se descarta, se pausa o se reformula antes de evaluar.

## 2. Score ponderado de oportunidad

El score mide que tan razonable es asignar recursos del equipo a una oportunidad.

Cada criterio se califica con la escala Fibonacci de madurez definida en este documento.

| Criterio | Peso |
| --- | ---: |
| Problema real y dolor relevante | 15 % |
| Cliente, usuario o beneficiario claro | 10 % |
| Evidencia disponible | 12 % |
| Potencial de caja o monetizacion | 12 % |
| Potencial de activo escalable | 12 % |
| Velocidad de validacion | 10 % |
| Encaje con capacidades del equipo | 10 % |
| Riesgo tecnico, legal, reputacional y operativo | 10 % |
| Coherencia con ADN y principios | 6 % |
| Aprendizaje estrategico aunque no escale | 3 % |
| **Total** | **100 %** |

### Escala Fibonacci de madurez

La escala no es lineal. Representa saltos de madurez.

| Nivel | Valor | Significado |
| --- | ---: | --- |
| Vacio | 0 | No hay senal suficiente. |
| Semilla | 1 | Existe intuicion, idea o interes inicial. |
| Hipotesis | 2 | Hay logica defendible, pero poca evidencia. |
| Evidencia inicial | 3 | Hay insumos, senales, conversaciones o prototipo inicial. |
| Evidencia fuerte | 5 | Hay validacion clara, cliente/problema definido, material real o compromiso serio. |
| Traccion | 8 | Hay cliente pago, contrato, uso real, anticipo, piloto activo o evidencia comercial fuerte. |

### Formula de score

Para cada criterio:

```text
Puntaje ponderado = (valor Fibonacci / 8) x peso
```

El puntaje total es la suma de todos los puntajes ponderados.

### Rangos de decision

| Score total | Decision sugerida |
| ---: | --- |
| 85 - 100 | Priorizar / avanzar con recursos. |
| 70 - 84 | Aprobar validacion formal. |
| 55 - 69 | Mantener como semilla o pedir ajustes. |
| 40 - 54 | Pausar hasta nueva evidencia. |
| < 40 | Descartar por ahora. |

## 3. Matriz esfuerzo vs ingreso

El score principal responde si una oportunidad merece atencion. La matriz esfuerzo vs ingreso responde si es razonable invertirle ahora.

La pregunta central es:

> Cuanto esfuerzo requiere esta oportunidad frente a que tan cerca esta de generar ingreso?

### Eje de esfuerzo

El esfuerzo no se mide solo por horas. Se mide por madurez, codigo existente, complejidad, riesgo y dependencia del equipo.

| Factor | Pregunta | Peso sugerido |
| --- | --- | ---: |
| Madurez de producto | Que tan claro esta el producto? | 25 % |
| Codigo existente | Ya hay base tecnica reutilizable creada por el equipo? | 25 % |
| Complejidad tecnica | Que tan dificil es construirlo bien? | 20 % |
| Riesgo operativo / legal | Que controles exige antes de operar? | 15 % |
| Dependencia del equipo | Cuantas personas, roles o decisiones requiere? | 15 % |

### Escala de esfuerzo

En esfuerzo, la escala Fibonacci se interpreta de forma inversa: a mayor valor, mayor carga.

| Valor | Lectura |
| ---: | --- |
| 1 | Muy bajo: casi listo, poco ajuste. |
| 2 | Bajo: requiere orden y ajustes menores. |
| 3 | Medio: requiere construccion acotada. |
| 5 | Alto: requiere varias capas nuevas. |
| 8 | Muy alto: requiere arquitectura, operacion, seguridad o equipo completo. |

### Eje de cercania a ingreso

Este eje mide que tan cerca esta la oportunidad de caja real.

| Valor | Lectura |
| ---: | --- |
| 0 | No hay ruta clara de ingreso. |
| 1 | Idea monetizable, sin cliente. |
| 2 | Segmento posible, interes supuesto. |
| 3 | Interes real o conversaciones abiertas. |
| 5 | Cliente/prospecto claro o piloto vendible. |
| 8 | Cliente pago, contrato, anticipo o ingreso activo. |

### Lectura de matriz

| | Ingreso bajo | Ingreso medio | Ingreso alto |
| --- | --- | --- | --- |
| Esfuerzo bajo | Explorar rapido | Validar ya | Prioridad comercial |
| Esfuerzo medio | Mantener como semilla | Piloto acotado | Priorizar si hay responsable |
| Esfuerzo alto | Pausar | Validar antes de construir | Avanzar solo con sponsor, cliente o equipo asignado |

### Ejemplo de lectura

```text
Score X-ponential: 78 / 100
Madurez general: evidencia inicial
Esfuerzo: 5
Cercania a ingreso: 3
Lectura: piloto acotado, no desarrollo completo.
```

## 4. Decision y puerta de revision

Cada evaluacion debe terminar con una decision explicita.

Opciones:

- Priorizar.
- Aprobar validacion formal.
- Mantener como semilla.
- Solicitar ajustes.
- Pausar.
- Descartar por ahora.

Tambien debe definir:

- responsable,
- proximo entregable,
- fecha de revision,
- criterios para continuar,
- criterios para detener.

## Reglas de uso

- El score no decide solo; ordena el criterio.
- Toda calificacion debe tener justificacion breve.
- La evidencia debe distinguir hechos, inferencias e hipotesis.
- Los filtros no negociables tienen prioridad sobre el puntaje.
- Caja temprana acelera prioridad, pero no elimina riesgos ni principios.
- Una oportunidad puede ser valiosa y aun asi no ser prioridad del momento.
- El score debe revisarse cuando aparezca nueva informacion relevante.
- Si una decision compromete recursos relevantes del equipo, debe quedar registrada en `docs/decisiones`.

## Contrato operativo

Este documento se complementa con:

- `docs/schemas/oportunidad-score.v1.json`
- `docs/evaluaciones/TEMPLATE.md`

El documento explica el criterio. El schema define la estructura. La plantilla permite aplicar el metodo a oportunidades concretas.

La intencion es que este contrato pueda convertirse mas adelante en:

- formulario,
- UI interna,
- GitHub Action,
- script de evaluacion,
- comentario automatizado en issues,
- o flujo asistido por Codex/ChatGPT.

## Plantilla resumida de evaluacion

```markdown
## Oportunidad

Nombre:
Responsable:
Fecha:
Issue:

## Filtros no negociables

| Filtro | Estado | Justificacion |
| --- | --- | --- |
| Integridad | Pasa / Condicionado / No pasa |  |
| Reputacion | Pasa / Condicionado / No pasa |  |
| Salud y vida sostenible | Pasa / Condicionado / No pasa |  |
| Fe y conciencia | Pasa / Condicionado / No pasa |  |
| Independencia responsable | Pasa / Condicionado / No pasa |  |
| Excelencia tecnica | Pasa / Condicionado / No pasa |  |
| Riesgo legal / regulatorio | Pasa / Condicionado / No pasa |  |
| Promesa responsable | Pasa / Condicionado / No pasa |  |

## Score ponderado

| Criterio | Peso | Valor Fibonacci | Puntaje | Justificacion |
| --- | ---: | ---: | ---: | --- |
| Problema real y dolor relevante | 15 % |  |  |  |
| Cliente, usuario o beneficiario claro | 10 % |  |  |  |
| Evidencia disponible | 12 % |  |  |  |
| Potencial de caja o monetizacion | 12 % |  |  |  |
| Potencial de activo escalable | 12 % |  |  |  |
| Velocidad de validacion | 10 % |  |  |  |
| Encaje con capacidades del equipo | 10 % |  |  |  |
| Riesgo tecnico, legal, reputacional y operativo | 10 % |  |  |  |
| Coherencia con ADN y principios | 6 % |  |  |  |
| Aprendizaje estrategico aunque no escale | 3 % |  |  |  |

Score total:
Decision sugerida:

## Matriz esfuerzo vs ingreso

Esfuerzo:
Cercania a ingreso:
Lectura:

## Decision

Decision final:
Responsable:
Proximo entregable:
Fecha de revision:
Criterios para continuar:
Criterios para detener:
```
