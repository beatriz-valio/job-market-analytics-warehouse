import json
import logging
from pathlib import Path
from datetime import datetime, timezone, date

from storage import build_raw_output_path, save_jobs_to_raw

import pandas as pd
from jobspy import scrape_jobs


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "raw"


# Load config
def load_config(config_file):
    with open(config_file, encoding="utf-8") as file:
        return json.load(file)


def json_safe(value):
    """
    Converte valores vindos do pandas/jobspy para formatos seguros em JSON.
    """

    if value is None:
        return None

    # Datas e timestamps
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    # Valores nulos do pandas/numpy
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    # Dicionários
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}

    # Listas
    if isinstance(value, list):
        return [json_safe(item) for item in value]

    # Tuplas
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    return value

# Main scraping logic
def scrape_and_store(config):
    sites = ["linkedin", "indeed"]

    output_path = build_raw_output_path()
    total_saved = 0

    logger.info(f"📁 Raw output file: {output_path}")

    for site in sites:
        for keyword in config["keywords"]:
            for location in config["locations"]:
                try:
                    logger.info(f"🔎 Scraping {site} for '{keyword}' in '{location}'")

                    jobs = scrape_jobs(
                        site_name=[site],
                        search_term=keyword,
                        location=location,
                        results_wanted=100,
                        hours_old=int(config["days_to_scrape"]) * 24,
                        country_indeed=config["country_indeed"],
                        linkedin_fetch_description=True
                    )

                    logger.info(
                        f"Found {len(jobs)} jobs for '{keyword}' in '{location}' on {site}"
                    )

                    if jobs.empty:
                        continue

                    df = jobs.copy()

                    # Filter by description keywords if provided
                    if config.get("desc_words"):
                        desc_words = config["desc_words"]

                        pattern = "|".join(desc_words)

                        df = df[
                            df["description"]
                            .fillna("")
                            .str.contains(pattern, case=False, na=False)
                        ]

                        logger.info(
                            f"📉 Filtered down to {len(df)} jobs after description keyword filtering"
                        )

                    if df.empty:
                        continue

                    saved = save_jobs_to_raw(
                        df=df,
                        source=site,
                        keyword=keyword,
                        location=location,
                        output_path=output_path
                    )

                    total_saved += saved

                    logger.info(
                        f"✅ Saved {saved} jobs to raw file for '{keyword}' in '{location}' on {site}"
                    )

                except Exception as e:
                    logger.error(
                        f"❌ Error scraping for '{keyword}' in '{location}' on {site}: {e}"
                    )

    logger.info(f"🎯 Finished. Total jobs saved locally: {total_saved}")
    logger.info(f"📁 File saved at: {output_path}")


# Entry point
if __name__ == "__main__":
    config_path = "config.json"
    config = load_config(config_path)
    scrape_and_store(config)
