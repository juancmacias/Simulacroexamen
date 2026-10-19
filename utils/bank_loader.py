"""Cargador de bancos de preguntas: unifica todos los JSON de la carpeta json/."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExamConfig:
    main_count: int = 30
    reserve_count: int = 5
    duration_minutes: int = 35


@dataclass
class BankInfo:
    key: str
    label: str
    count: int


class QuestionBank:
    """Mantiene las preguntas normalizadas de cada fichero y del conjunto unificado."""

    def __init__(self, banks: dict[str, list[dict]], labels: dict[str, str]):
        # banks: {"v1": [...], "v2": [...], "all": [...]}
        self._banks = banks
        self._labels = labels

    @classmethod
    def load_all(cls, json_dir: Path) -> "QuestionBank":
        banks: dict[str, list[dict]] = {}
        labels: dict[str, str] = {}

        for path in sorted(json_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            # Clave corta: "..._V2.json" -> "v2"; si no tiene versión -> "v1"
            stem = path.stem.lower()
            key = "v2" if stem.endswith("_v2") else "v1"
            # Si hubiera más ficheros, evita colisiones
            if key in banks:
                key = path.stem.lower()

            questions = cls._normalize(data, source=key)
            banks[key] = questions
            titulo = data.get("examen") or data.get("name") or path.stem
            labels[key] = f"{titulo} ({len(questions)})"

        # Banco unificado
        all_questions = [q for qs in banks.values() for q in qs]
        banks["all"] = all_questions
        labels["all"] = f"Todos los bancos unificados ({len(all_questions)})"

        return cls(banks, labels)

    @staticmethod
    def _normalize(data: dict, source: str) -> list[dict]:
        """Convierte cualquiera de los esquemas conocidos al formato interno:

        - V1: clave "questions", campos theme/text/correct(letra), options como {A,B,C,D}, explanation.
        - V2: clave "banco_preguntas", tema/pregunta/respuesta_correcta(indice 0..3), opciones(lista), explicacion.
        - (Tambien admite "preguntas" con respuesta_correcta como letra, por compatibilidad.)
        """
        raw = data.get("questions") or data.get("preguntas") or data.get("banco_preguntas")
        if not raw:
            raise ValueError("JSON sin clave 'questions', 'preguntas' ni 'banco_preguntas'.")

        normalized = []
        for q in raw:
            # --- opciones: lista o diccionario {A,B,C,D} ---
            if isinstance(q.get("options"), dict):
                letters = sorted(q["options"].keys())
                options = [q["options"][k] for k in letters]
            else:
                options = list(q.get("opciones") or q.get("options"))
                options = [o[3:] if isinstance(o, str) and o[1:3] == ") " else o for o in options]

            # --- respuesta correcta: letra o indice ---
            correcta = q.get("respuesta_correcta", q.get("correct"))
            if isinstance(correcta, int):
                correct_idx = correcta
            else:
                correct_idx = ord(str(correcta).strip().upper()) - 65
            if not (0 <= correct_idx < len(options)):
                raise ValueError(f"Pregunta {q.get('id')} con respuesta invalida: {correcta}")

            normalized.append({
                "id": q["id"],
                "tema": str(q.get("tema", q.get("theme", ""))),
                "application": q.get("application", ""),
                "question": q.get("pregunta", q.get("text", "")),
                "options": options,
                "correct_idx": correct_idx,
                "explicacion": q.get("explicacion", q.get("explanation", "")),
                "source": source,
            })
        return normalized

    def list_banks(self) -> list[BankInfo]:
        # Solo bancos procedentes de archivos JSON; 'all' es una agrupacion interna.
        keys = sorted(k for k in self._banks if k != "all")
        return [BankInfo(key=k, label=self._labels[k], count=len(self._banks[k])) for k in keys]

    def select(self, bank: str, count: int) -> list[dict]:
        """Devuelve `count` preguntas aleatorias (copias) del banco indicado."""
        import random

        pool = self._banks.get(bank)
        if pool is None:
            raise ValueError(f"Banco '{bank}' no existe.")
        if count > len(pool):
            raise ValueError(f"El banco '{bank}' solo tiene {len(pool)} preguntas.")

        if bank == "all":
            # Reparto equitativo entre bancos; el sobrante de bancos pequenos se redistribuye
            sources = [qs for k, qs in self._banks.items() if k != "all" and qs]
            if len(sources) > 1:
                quotas = [0] * len(sources)
                remaining = count
                while remaining > 0:
                    open_idx = [i for i, qs in enumerate(sources) if quotas[i] < len(qs)]
                    share, extra = divmod(remaining, len(open_idx))
                    random.shuffle(open_idx)
                    given = 0
                    for n, i in enumerate(open_idx):
                        add = min(share + (1 if n < extra else 0), len(sources[i]) - quotas[i])
                        quotas[i] += add
                        given += add
                    remaining -= given
                picked = [dict(q) for qs, n in zip(sources, quotas) for q in random.sample(qs, n)]
                random.shuffle(picked)
                return picked

        return [dict(q) for q in random.sample(pool, count)]


class SessionBankStore:
    """Bancos subidos por sesion (en memoria): cada sesion solo ve lo que ella misma subio."""

    def __init__(self):
        self._questions: dict[str, dict[str, list[dict]]] = {}
        self._labels: dict[str, dict[str, str]] = {}

    def get_bank(self, session_id: str) -> QuestionBank:
        banks = dict(self._questions.get(session_id, {}))
        labels = dict(self._labels.get(session_id, {}))
        all_questions = [q for qs in banks.values() for q in qs]
        banks["all"] = all_questions
        labels["all"] = f"Todos tus bancos subidos ({len(all_questions)})"
        return QuestionBank(banks, labels)

    def add_bank(self, session_id: str, filename: str, data: dict) -> BankInfo:
        stem = Path(filename).stem.lower().replace(" ", "_")
        questions = QuestionBank._normalize(data, source=stem)
        titulo = data.get("examen") or data.get("name") or stem
        label = f"{titulo} ({len(questions)})"
        self._questions.setdefault(session_id, {})[stem] = questions
        self._labels.setdefault(session_id, {})[stem] = label
        return BankInfo(key=stem, label=label, count=len(questions))

    def clear(self, session_id: str) -> None:
        self._questions.pop(session_id, None)
        self._labels.pop(session_id, None)
