
Genera un banco de preguntas tipo test sobre el TEMA indicado al final.

Devuelve ÚNICAMENTE un JSON válido, listo para descargar, sin explicaciones, comentarios ni bloques Markdown.

DATOS:
- TEMA: [TEMA]
- NÚMERO DE PREGUNTAS: [NÚMERO]
- CONTEXTO: [OPCIONAL]
- VERSIÓN/EDICIÓN: [OPCIONAL]
- FUENTES: oficiales
- IDIOMA: Español

REGLAS:

1. Genera exactamente el número de preguntas solicitado y todas deben estar relacionadas con el TEMA.

2. Cada pregunta debe tener 4 opciones (A, B, C, D) y exactamente una respuesta correcta.

3. Las preguntas deben evaluar conocimiento real. Evita preguntas demasiado obvias o cuya respuesta aparezca literalmente en el enunciado.

4. Los distractores deben ser plausibles y pertenecer al mismo ámbito que la respuesta correcta. No utilices opciones absurdas.

5. Combina preguntas de conocimiento, comprensión, aplicación, procedimiento, diferencias, excepciones y casos prácticos cuando el TEMA lo permita.

6. Evita preguntas repetidas o simples reformulaciones de otras.

7. Distribuye de forma equilibrada la posición de las respuestas correctas entre A, B, C y D.

8. La explicación debe indicar brevemente por qué la respuesta correcta lo es.

9. Utiliza el campo "theme" para identificar el tema o apartado correspondiente y "application" para indicar la materia, área, herramienta, concepto o subtema al que pertenece la pregunta.

10. Los "tags" deben servir para clasificar la pregunta.

11. Si se proporciona una versión, edición, normativa o fuente concreta, respétala y no mezcles información de otras versiones.

12. Antes de responder, comprueba que:
   - hay exactamente el número solicitado de preguntas;
   - todos los ID son únicos;
   - todas tienen A, B, C y D;
   - existe una sola respuesta correcta;
   - el valor de "correct" coincide con una opción;
   - no existen duplicados;
   - el JSON es válido.

ESTRUCTURA OBLIGATORIA:

{
  "name": "Banco de preguntas [TEMA]",
  "version": "1.0",
  "language": "es-ES",
  "scope": "[CONTEXTO]",
  "target_version": "[VERSIÓN/EDICIÓN O 'No aplica']",
  "created": "[FECHA ACTUAL]",
  "metadata": {
    "description": "Banco de preguntas tipo test con cuatro opciones y una respuesta correcta.",
    "sources": [
      "[FUENTE]"
    ]
  },
  "questions": [
    {
      "id": "001",
      "theme": "[TEMA/APARTADO]",
      "application": "[MATERIA, ÁREA O SUBTEMA]",
      "text": "[PREGUNTA]",
      "options": {
        "A": "[OPCIÓN A]",
        "B": "[OPCIÓN B]",
        "C": "[OPCIÓN C]",
        "D": "[OPCIÓN D]"
      },
      "correct": "A",
      "explanation": "[EXPLICACIÓN]",
      "tags": [
        "[ETIQUETA]"
      ]
    }
  ]
}

IMPORTANTE:
No añadas campos adicionales.
No elimines campos.
Mantén exactamente esta estructura.
NO quiero que muestres el cuestionario como respuesta de texto.
NO quiero una explicación.
NO quiero una vista previa.
NO quiero Markdown.
NO quiero un bloque ```json.


Utiliza este formato:
LexStudyAI_[TEMA]_[NUMERO]_preguntas.json
Sustituye espacios y caracteres problemáticos por "_".
Ejemplo:
LexStudyAI_Excel_Microsoft365_100_preguntas.json

TEMA:
del documento adjunto sobre la constitución

NÚMERO DE PREGUNTAS:
160