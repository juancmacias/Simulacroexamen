# Reescribe main.py con el contrato que espera el frontend (opciones como objeto, score con wrong/blank/grade_over_10)
content = '''import random
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils.bank_loader import ExamConfig, QuestionBank

BASE_DIR = Path(__file__).parent
JSON_DIR = BASE_DIR / "json"

EXAM_CONFIG = ExamConfig(main_count=30, reserve_count=5, duration_minutes=35)

# Unifica todos los bancos .json de la carpeta json/ (V1 + V2 = 1200 preguntas)
BANKS = QuestionBank.load_all(JSON_DIR)

# Etiqueta legible de la fuente para mostrar en pantalla
SOURCE_LABELS = {
    "v1": "Banco 400",
    "v2": "Banco 800",
}

app = FastAPI(title="Simulador de Examenes", version="2.0.0")

# Sesiones de examen en memoria: exam_id -> lista de preguntas seleccionadas
exam_sessions: dict[str, list[dict]] = {}

LETTERS = ["A", "B", "C", "D"]


class GradeRequest(BaseModel):
    exam_id: str
    answers: dict[int, str]  # indice de pregunta -> letra elegida ("A", "B", ...)


def _public_question(i: int, q: dict) -> dict:
    """Formato que espera el frontend: opciones como objeto {A,B,C,D}."""
    return {
        "index": i,
        "id": q["id"],
        "application": SOURCE_LABELS.get(q["source"], q["source"]),
        "theme": q["tema"],
        "text": q["question"],
        "options": {LETTERS[k]: opt for k, opt in enumerate(q["options"])},
        "reserve": i >= EXAM_CONFIG.main_count,
    }


@app.get("/api/banks")
def list_banks():
    """Lista los bancos disponibles ('all' = unificado) y la configuracion."""
    return {
        "banks": [
            {"key": b.key, "label": b.label, "count": b.count}
            for b in BANKS.list_banks()
        ],
        "main_count": EXAM_CONFIG.main_count,
        "reserve_count": EXAM_CONFIG.reserve_count,
        "duration_minutes": EXAM_CONFIG.duration_minutes,
    }


@app.get("/api/exam")
def create_exam(bank: str = "all"):
    """Genera un examen aleatorio de 30 + 5 reservas del banco elegido."""
    try:
        selected = BANKS.select(bank, EXAM_CONFIG.main_count + EXAM_CONFIG.reserve_count)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Baraja las opciones de cada pregunta y recalcula la letra correcta
    for q in selected:
        order = list(range(len(q["options"])))
        random.shuffle(order)
        q["options"] = [q["options"][j] for j in order]
        q["correct_letter"] = LETTERS[order.index(q["correct_idx"])]

    exam_id = uuid.uuid4().hex
    exam_sessions[exam_id] = selected

    return {
        "exam_id": exam_id,
        "bank": bank,
        "duration_seconds": EXAM_CONFIG.duration_minutes * 60,
        "main_count": EXAM_CONFIG.main_count,
        "reserve_count": EXAM_CONFIG.reserve_count,
        "questions": [_public_question(i, q) for i, q in enumerate(selected)],
    }


def _tally(items: list[dict]) -> dict:
    correct = sum(1 for r in items if r["is_correct"])
    blank = sum(1 for r in items if r["user_answer"] is None)
    wrong = len(items) - correct - blank
    total = len(items)
    return {
        "correct": correct,
        "wrong": wrong,
        "blank": blank,
        "total": total,
        "grade_over_10": round(correct / total * 10, 2) if total else 0.0,
    }


@app.post("/api/grade")
def grade_exam(req: GradeRequest):
    """Corrige en el servidor: principales /30, reservas /5, con explicaciones."""
    questions = exam_sessions.get(req.exam_id)
    if questions is None:
        raise HTTPException(status_code=404, detail="Examen no encontrado o ya corregido.")

    results = []
    for i, q in enumerate(questions):
        user_answer = req.answers.get(str(i))
        if user_answer is None:
            user_answer = req.answers.get(i)
        correct = q["correct_letter"]
        pub = _public_question(i, q)
        results.append({
            **pub,
            "user_answer": user_answer,
            "correct_answer": correct,
            "is_correct": user_answer == correct,
            "explanation": q["explicacion"],
        })

    main = [r for r in results if not r["reserve"]]
    reserve = [r for r in results if r["reserve"]]

    exam_sessions.pop(req.exam_id, None)

    return {
        "score": {
            "main": _tally(main),
            "reserve": _tally(reserve),
        },
        "results": results,
    }


# --- Frontend estatico ---
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
'''

with open("main.py", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

import ast
ast.parse(open("main.py", encoding="utf-8").read())
print("main.py reescrito y sintaxis OK")
