import json
import os
import random
import re
import tempfile
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils.bank_loader import ExamConfig, SessionBankStore

BASE_DIR = Path(__file__).parent

EXAM_CONFIG = ExamConfig(main_count=30, reserve_count=5, duration_minutes=35)

# Bancos subidos por cada sesion (en memoria); cada sesion solo ve los suyos
SESSION_STORE = SessionBankStore()

# Contenido de ayuda para crear el JSON, cargado una sola vez al arrancar
PROMPT_HELP_PATH = BASE_DIR / "prompt" / "prompt.md"
PROMPT_HELP_TEXT = PROMPT_HELP_PATH.read_text(encoding="utf-8") if PROMPT_HELP_PATH.exists() else ""

app = FastAPI(title="Simulador de Examenes", version="2.0.0")

# Examenes en disco (compartidos entre procesos/workers): exam_id -> preguntas seleccionadas
EXAM_DIR = Path(tempfile.gettempdir()) / "simulacro_exams"
EXAM_DIR.mkdir(parents=True, exist_ok=True)
EXAM_TTL_SECONDS = 60 * 60 * 24


def _exam_path(exam_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", exam_id):
        raise HTTPException(status_code=404, detail="Examen no encontrado.")
    return EXAM_DIR / f"{exam_id}.json"


def save_exam(exam_id: str, questions: list[dict]) -> None:
    now = time.time()
    for old in EXAM_DIR.glob("*.json"):
        try:
            if now - old.stat().st_mtime > EXAM_TTL_SECONDS:
                old.unlink()
        except OSError:
            pass
    _exam_path(exam_id).write_text(json.dumps(questions), encoding="utf-8")


def load_exam(exam_id: str) -> list[dict] | None:
    path = _exam_path(exam_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias


def get_session_id(response: Response, session_id: str | None = Cookie(default=None)) -> str:
    """Obtiene (o crea) el id de sesion del usuario a partir de una cookie httponly."""
    if not session_id:
        session_id = uuid.uuid4().hex
    response.set_cookie(
        "session_id", session_id, httponly=True, samesite="lax", max_age=SESSION_COOKIE_MAX_AGE
    )
    return session_id


class GradeRequest(BaseModel):
    exam_id: str
    answers: dict[int, str]
    wrong_penalty: float = 0.3333333333333333


@app.get("/api/banks")
def list_banks(session_id: str = Depends(get_session_id)):
    """Lista los bancos subidos por esta sesion ('all' = unificado) y la configuracion."""
    bank = SESSION_STORE.get_bank(session_id)
    return {
        "banks": [
            {"key": b.key, "label": b.label, "count": b.count}
            for b in bank.list_banks()
        ],
        "main_count": EXAM_CONFIG.main_count,
        "reserve_count": EXAM_CONFIG.reserve_count,
        "duration_minutes": EXAM_CONFIG.duration_minutes,
    }


@app.get("/api/prompt-help")
def get_prompt_help():
    """Devuelve el texto de ayuda (prompt.md) para generar un banco de preguntas."""
    return {"content": PROMPT_HELP_TEXT}


@app.post("/api/upload")
async def upload_bank(file: UploadFile = File(...), session_id: str = Depends(get_session_id)):
    """Sube un fichero .json de preguntas y lo asocia solo a la sesion actual."""
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Solo se admiten ficheros .json")
    raw = await file.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"JSON invalido: {exc}") from exc
    try:
        info = SESSION_STORE.add_bank(session_id, file.filename, data)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Formato de banco invalido: {exc}") from exc
    return {"key": info.key, "label": info.label, "count": info.count}


@app.get("/api/exam")
def create_exam(
    bank: str,
    session_id: str = Depends(get_session_id),
    main_count: int = Query(default=EXAM_CONFIG.main_count, ge=1),
    reserve_count: int = Query(default=EXAM_CONFIG.reserve_count, ge=0, le=10),
):
    """Genera un examen con preguntas principales y de reserva del banco de la sesion."""
    try:
        selected = SESSION_STORE.get_bank(session_id).select(bank, main_count + reserve_count)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    exam_id = uuid.uuid4().hex

    questions = []
    for i, q in enumerate(selected):
        q["reserve"] = i >= main_count
        order = list(range(len(q["options"])))
        random.shuffle(order)
        shuffled = [q["options"][j] for j in order]
        correct_idx = order.index(q["correct_idx"])
        q["correct_letter"] = chr(65 + correct_idx)
        q["exam_options"] = {chr(65 + k): option for k, option in enumerate(shuffled)}

        questions.append({
            "index": i,
            "id": q["id"],
            "source": q["source"],
            "application": q["application"],
            "theme": q["tema"],
            "text": q["question"],
            "options": q["exam_options"],
            "reserve": q["reserve"],
        })

    save_exam(exam_id, selected)

    return {
        "exam_id": exam_id,
        "bank": bank,
        "duration_seconds": (main_count + reserve_count) * 60,
        "main_count": main_count,
        "reserve_count": reserve_count,
        "questions": questions,
    }


@app.post("/api/grade")
def grade_exam(req: GradeRequest):
    """Corrige en el servidor: principales /30, reservas /5, con explicaciones."""
    questions = load_exam(req.exam_id)
    if questions is None:
        raise HTTPException(status_code=404, detail="Examen no encontrado o caducado. Genera un nuevo simulacro.")

    results = []
    for i, q in enumerate(questions):
        user_answer = req.answers.get(i)
        correct = q["correct_letter"]
        results.append({
            "index": i,
            "id": q["id"],
            "source": q["source"],
            "application": q["application"],
            "theme": q["tema"],
            "text": q["question"],
            "options": q["exam_options"],
            "user_answer": user_answer,
            "correct_answer": correct,
            "is_correct": user_answer == correct,
            "explanation": q["explicacion"],
            "reserve": q["reserve"],
        })

    main = [r for r in results if not r["reserve"]]
    reserve = [r for r in results if r["reserve"]]
    main_correct = sum(1 for r in main if r["is_correct"])
    reserve_correct = sum(1 for r in reserve if r["is_correct"])
    main_blank = sum(1 for r in main if r["user_answer"] is None)
    reserve_blank = sum(1 for r in reserve if r["user_answer"] is None)
    main_wrong = len(main) - main_correct - main_blank
    reserve_wrong = len(reserve) - reserve_correct - reserve_blank

    penalty_rate = max(0.0, req.wrong_penalty)
    main_penalty = main_wrong * penalty_rate
    main_net = max(0.0, main_correct - main_penalty)
    main_grade = round((main_net / len(main)) * 10, 2) if main else 0.0

    reserve_penalty = reserve_wrong * penalty_rate
    reserve_net = max(0.0, reserve_correct - reserve_penalty)

    return {
        "score": {
            "main": {
                "correct": main_correct,
                "wrong": main_wrong,
                "blank": main_blank,
                "total": len(main),
                "wrong_penalty_rate": penalty_rate,
                "penalty_deduction": round(main_penalty, 2),
                "net_points": round(main_net, 2),
                "grade_over_10": main_grade,
            },
            "reserve": {
                "correct": reserve_correct,
                "wrong": reserve_wrong,
                "blank": reserve_blank,
                "total": len(reserve),
                "wrong_penalty_rate": penalty_rate,
                "penalty_deduction": round(reserve_penalty, 2),
                "net_points": round(reserve_net, 2),
            },
            "percent": round((main_net / len(main)) * 100, 1) if main else 0,
        },
        "results": results,
    }


# --- Frontend estatico ---
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


if __name__ == "__main__":
    # Host 0.0.0.0 y puerto via $PORT: necesario para plataformas como Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
