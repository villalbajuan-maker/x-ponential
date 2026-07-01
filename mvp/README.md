# OCR Licitaciones MVP

MVP local para procesar documentos de licitaciones con revision humana en cada checkpoint.

## Que hace esta version

- Levanta un backend local con FastAPI.
- Sirve `index.html` desde `/`.
- Expone `GET /health`.
- Permite guardar el perfil de empresa en `company/SEASIM/data.json`.
- Permite importar un perfil de empresa desde un JSON seleccionado por ti.
- Permite subir documentos originales a `company/SEASIM/originales/` sin modificarlos.
- Guarda las extracciones revisables en `company/SEASIM/actualizados/`.
- Clasifica archivos, extrae texto, aplica OCR cuando hace falta y genera un JSON de extraccion.
- La logica de OCR y extraccion de texto vive en `ocr.py`.
- La consulta SECOP y la descarga de archivos oficiales viven en `secop.py`.
- Permite revisar cada hallazgo y decidir si se acepta, edita o descarta.
- Si falta un dato reutilizable necesario para completar un documento, la interfaz lo convierte en una pregunta minimalista de una sola respuesta por vez, con flechas para avanzar.

## Estructura

```text
mvp/
|-- main.py
|-- ocr.py
|-- secop.py
|-- index.html
|-- requirements.txt
|-- README.md
`-- company/
    `-- SEASIM/
        |-- originales/
        |-- actualizados/
        `-- data.json
```

## Instalacion

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Tesseract local

La extraccion OCR usa `pytesseract`, asi que Tesseract debe estar instalado en la maquina local.

- Windows: instalar Tesseract y agregarlo al `PATH`.
- Linux: instalarlo con el gestor de paquetes de la distribucion.
- macOS: instalarlo con Homebrew u otro gestor equivalente.

## Ejecucion

Arrancar el backend, modo rapido:

```bash
cd mvp
python -m uvicorn main:app --port 8001
```

`main.py` dentro de `mvp/` contiene la app principal del MVP
y agrega las rutas de `secop.py` en un solo servidor.

Si necesitas recarga automatica durante desarrollo, usa una recarga acotada para
evitar que el watcher revise todo el workspace:

```bash
cd mvp
python -m uvicorn main:app --reload --reload-dir . --reload-dir ../referencia --port 8001
```

Abrir la interfaz:

- `http://127.0.0.1:8001/`

Probar el estado del backend:

- `http://127.0.0.1:8001/health`

## Probar el flujo

1. Cargar o editar el perfil de empresa.
   - Si ya tienes un JSON de perfil, seleccionarlo e importarlo primero.
   - Si faltan datos, completa las preguntas que aparecen debajo del perfil.
2. Subir un documento original.
3. Copiar el `document_id` en el formulario de proceso.
4. Procesar el documento.
5. Revisar el JSON de extraccion, el texto resumido y los campos detectados.
6. Abrir la revision humana y decidir por cada dato si se acepta, se edita o se descarta.
7. Si corresponde, guardar el dato reutilizable en el perfil de empresa solo con aprobacion expresa.

## Siguiente paso

El siguiente checkpoint agregara plantillas DOCX y XLSX con merge controlado.
