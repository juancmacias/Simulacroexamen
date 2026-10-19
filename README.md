# Simulador de Exámenes

Aplicación web para realizar simulacros de examen tipo test a partir de bancos de preguntas en JSON subidos por el propio usuario. Backend en FastAPI y frontend estático (HTML).

## Características

- Subida de bancos de preguntas en `.json`; cada sesión (cookie `session_id`) solo ve los bancos que ha subido.
- Generación de exámenes con preguntas principales (por defecto 30) y de reserva (por defecto 5).
- Opción "todos los bancos": las preguntas se reparten a partes iguales entre los bancos subidos; si un banco es pequeño, el sobrante se redistribuye.
- Orden de las opciones barajado en cada examen.
- Corrección en el servidor con puntuación, penalización por error (por defecto 1/3) y explicaciones.
- Se puede corregir el mismo examen varias veces y hacer simulacros ilimitados.
- Ayuda integrada con el [prompt](prompt/prompt.md) para generar un banco de preguntas con una IA.
- Con 2 o más bancos subidos aparece "Todos los bancos mezclados" como opción por defecto.
- Footer con la versión de la app, enlazado al repositorio de GitHub.
- Icono de la app (`static/img/icono.png`) usado como favicon.

## Estructura

```
main.py              API FastAPI y servidor estático
passenger_wsgi.py    Entrada WSGI (Passenger) mediante a2wsgi
utils/bank_loader.py Carga, normalización y selección de preguntas
static/index.html    Interfaz de usuario
static/img/icono.png Icono de la app (favicon)
prompt/prompt.md     Prompt de ayuda para generar bancos de preguntas
requirements.txt     Dependencias
```

## Requisitos

- Python 3.10 o superior
- Dependencias: `fastapi`, `uvicorn`, `python-multipart`, `a2wsgi`

## Ejecución local

```bash
pip install -r requirements.txt
python main.py
```

La app queda en `http://localhost:8000`. El puerto se puede cambiar con la variable de entorno `PORT`.

## Despliegue

- **Passenger (cPanel u hosting similar):** se usa `passenger_wsgi.py`, que expone `main.app` como aplicación WSGI.
- **Plataformas tipo Render:** `python main.py` escucha en `0.0.0.0` y en `$PORT`.

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/banks` | Lista los bancos de la sesión y la configuración |
| POST | `/api/upload` | Sube un banco `.json` (multipart, campo `file`) |
| GET | `/api/prompt-help` | Devuelve el texto de [prompt/prompt.md](prompt/prompt.md) |
| GET | `/api/version` | Versión de la app (`APP_VERSION` en `main.py`) y URL del repo |
| GET | `/favicon.ico` | Icono de la app (`static/img/icono.png`) |
| GET | `/api/exam?bank=...&main_count=30&reserve_count=5` | Genera un examen (`bank=all` para todos) |
| POST | `/api/grade` | Corrige un examen: `{exam_id, answers: {índice: letra}, wrong_penalty}` |

## Formato de los bancos de preguntas

Claves de lista admitidas: `questions`, `preguntas` o `banco_preguntas`. Cada pregunta necesita:

- `id`
- Enunciado: `text` o `pregunta`
- Opciones: `options` (objeto `{A,B,C,D}`) u `opciones` (lista)
- Respuesta correcta: `correct` o `respuesta_correcta` (letra o índice desde 0)
- Opcionales: `theme`/`tema`, `application`, `explanation`/`explicacion`

El prompt completo para generar un banco con una IA está en [prompt/prompt.md](prompt/prompt.md).

## Puntuación

- Nota principal sobre 10: `(aciertos - errores × penalización) / total × 10`, con mínimo 0.
- Las preguntas en blanco no penalizan.
- Las reservas se puntúan por separado.

## Persistencia

- Los exámenes generados se guardan como archivos JSON en la carpeta temporal del sistema (`simulacro_exams`) y se eliminan a las 24 horas.
- Los bancos subidos se mantienen en memoria del proceso: se pierden al reiniciar el servidor.

## Versiones

- La versión se define a mano en `APP_VERSION` de [main.py](main.py) y se muestra en el footer.
- Cada release debe llevar el mismo número como tag de git:

```bash
git tag -a v1.2.0 -m "Versión 1.2.0"
git push origin main
git push origin v1.2.0
```

## Icono

Coloca la imagen en `static/img/icono.png`. Se sirve en `/static/img/icono.png` y `/favicon.ico`, y se enlaza en el `<head>` de [static/index.html](static/index.html). Si el fichero no existe, el navegador no mostrará icono.
