"""API backend do PIPPA Emendas — serve dados dos parquets e re-executa o pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from dashboard_builder import build_all_data
from models import PipelineStats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pippa-emendas-api")

app = FastAPI(title="PIPPA Emendas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROCESSED = Path(__file__).parent / "data" / "processed"
OUTPUT = Path(__file__).parent / "output"

pipeline_status = {"running": False, "last_error": None}


@app.get("/")
async def index():
    return FileResponse(OUTPUT / "pippa_emendas_completo.html", media_type="text/html")


@app.get("/api/dados")
async def get_dados(ano: int | None = None):
    """Retorna dados agregados dos parquets como JSON."""
    sufixo = f"_{ano}" if ano else "_completo"
    try:
        df_estado = pd.read_parquet(PROCESSED / f"agg_por_estado{sufixo}.parquet")
        df_municipio = pd.read_parquet(PROCESSED / f"agg_por_municipio{sufixo}.parquet")
        df_autor = pd.read_parquet(PROCESSED / f"agg_por_autor{sufixo}.parquet")
        df_partido = pd.read_parquet(PROCESSED / f"agg_por_partido{sufixo}.parquet")
        df_tipo = pd.read_parquet(PROCESSED / f"agg_por_tipo{sufixo}.parquet")
        df_serie = pd.read_parquet(PROCESSED / f"agg_serie_temporal{sufixo}.parquet")
        df_emendas = pd.read_parquet(PROCESSED / f"emendas_enriquecidas{sufixo}.parquet")

        funcao_path = PROCESSED / f"agg_por_funcao{sufixo}.parquet"
        df_funcao = pd.read_parquet(funcao_path) if funcao_path.exists() else None

        data = build_all_data(
            df_estado, df_municipio, df_autor, df_partido, df_tipo, df_serie, df_emendas, df_funcao
        )

        total_autores = len(set(d["nome"] for d in data["autores"]))
        total_emendas = sum(d["qtd"] for d in data["estados"])

        data["_stats"] = {
            "total_emendas": total_emendas,
            "total_autores_unicos": total_autores,
        }

        logger.info(
            "Dados servidos: %d estados, %d autores, %d municipios",
            len(data["estados"]),
            len(data["autores"]),
            len(data["municipios"]),
        )
        return JSONResponse(content=data)

    except FileNotFoundError as e:
        return JSONResponse(
            content={"error": f"Parquets nao encontrados. Execute o pipeline primeiro: {e}"},
            status_code=404,
        )


@app.post("/api/pipeline")
async def run_pipeline_endpoint(background_tasks: BackgroundTasks, ano: int | None = None):
    """Dispara o pipeline completo em background (coleta + processamento)."""
    if pipeline_status["running"]:
        return JSONResponse(
            content={"status": "Pipeline ja esta em execucao"}, status_code=409
        )
    pipeline_status["running"] = True
    pipeline_status["last_error"] = None
    background_tasks.add_task(_run_pipeline, ano)
    return {"status": "Pipeline iniciado em background"}


@app.get("/api/pipeline/status")
async def pipeline_state():
    return pipeline_status


def _run_pipeline(ano: int | None):
    try:
        from pipeline import run_pipeline
        logger.info("Pipeline iniciado (ano=%s)", ano)
        run_pipeline(ano_filtro=ano)
        logger.info("Pipeline concluido com sucesso")
    except Exception as e:
        logger.error("Pipeline falhou: %s", e)
        pipeline_status["last_error"] = str(e)
    finally:
        pipeline_status["running"] = False


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("PIPPA Emendas API")
    print("Acesse: http://localhost:8050")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8050)
