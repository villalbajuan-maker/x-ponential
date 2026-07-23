# Evaluacion de oportunidad: [Nombre]

## Estado

Evaluacion v1 aplicada con el [Score de oportunidades X-ponential](../SCORE-DE-OPORTUNIDADES.md).

## Oportunidad

| Campo | Valor |
| --- | --- |
| Nombre |  |
| Responsable |  |
| Fecha |  |
| Issue |  |
| Etapa | Semilla / Validacion / Piloto / Producto / Pausada / Descartada |

## Tabla resumida de decision

| Caracteristica | Resultado | Valor / lectura |
| --- | --- | --- |
| Filtros no negociables | **No pasa / Pasa condicionado / Pasa** | Check inicial; sin peso en el resultado global |
| Score ponderado | **0.00 / 100**; nivel: **1 / 2 / 3 / 4 / 5** | Peso global: **62 %** |
| Matriz esfuerzo vs ingreso | Nivel resumido: **1 / 2 / 3 / 4 / 5** | Peso global: **19 %** |
| Decision y siguiente puerta | Nivel resumido: **1 / 2 / 3 / 4 / 5** | Peso global: **19 %** |

Discretizacion del score: **1 = 0 a < 20; 2 = 20 a < 40; 3 = 40 a < 60; 4 = 60 a < 80; 5 = 80 a 100**.

El valor consolidado de no negociables corresponde al menor valor asignado entre todos los filtros y funciona exclusivamente como check inicial.

Resultado del check inicial: **rechazar / continuar condicionado / continuar**.

Si el check inicial permite continuar, calcular:

```text
(score x 62 %) + (matriz x 19 %) + (decision x 19 %)
```

Resultado global final: **0.00 / 5**.

Los no negociables no participan en el promedio y no pueden ser compensados por un buen score.

Nivel de matriz: **1 pausar; 2 validar antes de construir; 3 piloto acotado; 4 validar ya o avanzar controladamente; 5 prioridad comercial**.

Nivel de decision: **1 descartar; 2 pausar; 3 mantener semilla o solicitar ajustes; 4 aprobar validacion formal; 5 priorizar**.

## Lectura ejecutiva

Sintesis breve de la oportunidad, su estado real, su potencial y la recomendacion principal.

Debe responder en lenguaje claro:

- Que es?
- Por que merece o no merece atencion ahora?
- Cual es la decision razonable?
- Que condicion o limite principal debe respetarse?

## Filtros no negociables

| Filtro | Valor | Estado equivalente | Justificacion |
| --- | ---: | --- | --- |
| Integridad | 1 / 2 / 3 / 4 / 5 |  |  |
| Reputacion | 1 / 2 / 3 / 4 / 5 |  |  |
| Salud y vida sostenible | 1 / 2 / 3 / 4 / 5 |  |  |
| Fe y conciencia | 1 / 2 / 3 / 4 / 5 |  |  |
| Independencia responsable | 1 / 2 / 3 / 4 / 5 |  |  |
| Excelencia tecnica | 1 / 2 / 3 / 4 / 5 |  |  |
| Riesgo legal / regulatorio | 1 / 2 / 3 / 4 / 5 |  |  |
| Promesa responsable | 1 / 2 / 3 / 4 / 5 |  |  |

Escala: **1 no pasa; 2 puede pasar condicionalmente; 3 pasa condicionalmente y requiere validacion; 4 pasa condicionalmente; 5 pasa absolutamente**.

Valor consolidado: **1 / 2 / 3 / 4 / 5** (usar el menor valor de los filtros).

Resultado: **no pasa / puede pasar condicionalmente / pasa para validacion controlada / pasa condicionado / pasa absolutamente**.

## Score ponderado

Escala Fibonacci: 0, 1, 2, 3, 5, 8.

| Criterio | Peso | Valor Fibonacci | Puntaje | Justificacion |
| --- | ---: | ---: | ---: | --- |
| Problema real y dolor relevante | 15 % |  |  |  |
| Cliente, usuario o beneficiario claro | 15 % |  |  |  |
| Evidencia disponible | 9 % |  |  |  |
| Potencial de caja o monetizacion | 25 % |  |  |  |
| Potencial de activo escalable | 9 % |  |  |  |
| Velocidad de validacion | 7 % |  |  |  |
| Encaje con capacidades del equipo | 7 % |  |  |  |
| Riesgo tecnico, legal, reputacional y operativo | 7 % |  |  |  |
| Coherencia con ADN y principios | 4 % |  |  |  |
| Aprendizaje estrategico aunque no escale | 2 % |  |  |  |

**Score total: 0.00 / 100**

**Nivel discretizado: 1 / 2 / 3 / 4 / 5**.

Rangos: **1 = 0 a < 20; 2 = 20 a < 40; 3 = 40 a < 60; 4 = 60 a < 80; 5 = 80 a 100**.

Decision sugerida por score: **priorizar / aprobar validacion formal / mantener como semilla o pedir ajustes / pausar hasta nueva evidencia / descartar por ahora**.

Decision final propuesta: **priorizar / aprobar validacion formal condicionada / mantener semilla / solicitar ajustes / pausar / descartar por ahora**.

## Interpretacion del score

Explicar que significa el puntaje.

Debe distinguir:

- lo que la oportunidad ya confirma,
- lo que todavia no demuestra,
- y por que la decision final puede coincidir o diferir de la decision sugerida por rango.

## Matriz esfuerzo vs ingreso

### Esfuerzo

Escala: 1 muy bajo, 2 bajo, 3 medio, 5 alto, 8 muy alto.

| Factor | Peso | Valor | Justificacion |
| --- | ---: | ---: | --- |
| Madurez de producto | 25 % |  |  |
| Codigo existente | 25 % |  |  |
| Complejidad tecnica | 20 % |  |  |
| Riesgo operativo / legal | 15 % |  |  |
| Dependencia del equipo | 15 % |  |  |

Esfuerzo resultante: **1 / 2 / 3 / 5 / 8 - lectura**.

### Cercania a ingreso

Escala: 0 sin ruta clara, 1 idea monetizable, 2 segmento posible, 3 interes real, 5 piloto vendible, 8 ingreso activo.

Valor: **0 / 1 / 2 / 3 / 5 / 8 - lectura**.

Justificacion:

### Lectura

**Prioridad comercial / Validar ya / Piloto acotado / Validar antes de construir / Pausar.**

Explicar la consecuencia operativa de la matriz.

## Evidencia

### Hechos

- 

### Inferencias

- 

### Hipotesis

- 

## Decision

| Campo | Valor |
| --- | --- |
| Decision final |  |
| Responsable |  |
| Proximo entregable |  |
| Fecha de revision |  |

### Criterios para continuar

- 

### Criterios para detener o replantear

- 

## Recomendacion final

Cerrar con una recomendacion ejecutiva breve.

Debe dejar claro:

- si se avanza, se valida, se pausa o se descarta,
- cual es el siguiente paso verificable,
- y que evidencia debe cambiar para modificar la decision.
