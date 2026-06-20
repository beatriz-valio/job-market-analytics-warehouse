# storage.py

import json
import logging
from pathlib import Path
from datetime import datetime, timezone, date

import pandas as pd


logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """
    Encontra a raiz do projeto procurando por arquivos típicos.
    Isso evita problema se o script estiver dentro de src/ingestion/.
    """

    current_path = Path(__file__).resolve()

    for parent in [current_path.parent, *current_path.parents]:
        if (
            (parent / "config.json").exists()
            or (parent / "requirements.txt").exists()
            or (parent / ".git").exists()
        ):
            return parent

    return current_path.parent


PROJECT_ROOT = get_project_root()
RAW_DIR = PROJECT_ROOT / "raw"


def json_safe(value):
    """
    Converte valores vindos do pandas/jobspy para formatos seguros em JSON.
    """

    if value is None:
        return None

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    if isinstance(value, set):
        return [json_safe(item) for item in value]

    return value


def build_raw_output_path(prefix: str = "jobspy_jobs") -> Path:
    """
    Cria a pasta raw/ e gera o caminho do arquivo de saída.
    """

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return RAW_DIR / f"{prefix}_{timestamp}.jsonl"


def save_jobs_to_raw(
    df: pd.DataFrame,
    source: str,
    keyword: str,
    location: str,
    output_path: Path | None = None
) -> int:
    """
    Salva vagas em formato JSONL na pasta raw/.

    Cada linha do arquivo é um JSON independente.
    """

    if df.empty:
        return 0

    if output_path is None:
        output_path = build_raw_output_path()

    records_saved = 0
    scraped_at = datetime.now(timezone.utc).isoformat()

    with output_path.open("a", encoding="utf-8") as file:
        for _, row in df.iterrows():
            raw_record = row.to_dict()

            record = {
                "source": source,
                "search_keyword": keyword,
                "search_location": location,
                "scraped_at": scraped_at,
                "raw": json_safe(raw_record)
            }

            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            records_saved += 1

    logger.info(f"✅ Saved {records_saved} jobs to {output_path}")

    return records_saved
