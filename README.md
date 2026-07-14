# Business Bridge

Business Bridge es el repositorio de trabajo para el piloto de licitaciones y la documentación que mantiene la base de código comprensible para un equipo.

## Qué hay aquí

- `src/business_bridge/api/`: punto de entrada canónico de FastAPI, esquemas e interfaz estática.
- `src/business_bridge/adapters/`: adaptadores canónicos de OCR y SECOP usados por el piloto.
- `docs/`: memoria del proyecto, notas de arquitectura, decisiones y guías prácticas.
- `specs/`: especificaciones, planes, tareas y listas de verificación.
- `company/Business_Bridge/`: datos de trabajo de la empresa para el piloto.
- `codex_agents/`: sistema de agentes exclusivo de Codex para investigación, arquitectura, calidad y retroalimentación.
- `.codex-state/`: estado local mutable de los agentes, ignorado por Git.
- `.github/`: plantillas de issues y pull requests.

## Memoria del proyecto

La documentación fundacional actual sigue viviendo en `docs/` y sigue siendo parte del mapa del repo:

- `docs/ADN.md`
- `docs/PORQUE.md`
- `docs/PRINCIPIOS.md`
- `docs/CRITERIOS-DE-OPORTUNIDAD.md`
- `docs/INDICADORES.md`
- `docs/ACUERDOS.md`
- `docs/EQUIPO.md`
- `docs/KICKOFF.md`
- `docs/TABLERO.md`
- `docs/GITHUB.md`
- `docs/PAUTAS.md`
- `docs/decisiones/`
- `docs/propuestas/`
- `docs/reuniones/`

## Cómo fluye el trabajo

1. Registrar el cambio en `specs/`.
2. Convertir la especificación en un plan y una lista de tareas.
3. Implementar en `src/business_bridge/` y mantener el punto de entrada de la API en `src/business_bridge/api/`.
4. Agregar o actualizar pruebas.
5. Registrar las decisiones técnicas en `docs/decisiones/`.
6. Mover el material histórico a `docs/archive/`.

## Flujo actual del piloto

- cargar o actualizar el perfil de la empresa
- subir un documento original
- procesar texto y OCR
- revisar los campos detectados
- guardar respuestas reutilizables con aprobación humana

## Cobertura canonica

- `python -m pytest` genera y actualiza `coverage.json` en la raiz del repositorio.
- El archivo se sobrescribe en cada corrida para evitar versiones viejas.
- El umbral minimo actual es del `90%` y la corrida falla si baja de ese valor.

## Empieza aquí

- Panorama de arquitectura: [docs/architecture/overview.md](docs/architecture/overview.md)
- Guías prácticas: [docs/how-to/README.md](docs/how-to/README.md)
- Archivo histórico: [docs/archive/README.md](docs/archive/README.md)
- Pruebas: [tests/README.md](tests/README.md)
- Datos de ejemplo: [sample_data/README.md](sample_data/README.md)
- Paquete canónico: [src/business_bridge/README.md](src/business_bridge/README.md)
- Runtime de la API: [src/business_bridge/api/main.py](src/business_bridge/api/main.py)
- Flujo de especificaciones: [specs/README.md](specs/README.md)
- Plan de trabajo: [PLAN_DE_CORRECCIONES.md](PLAN_DE_CORRECCIONES.md)
