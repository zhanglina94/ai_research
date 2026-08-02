"""MLflow experiment tracking client."""

import logging
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MLflowClient:
    def __init__(self) -> None:
        self._available = False
        self._tracking_uri = settings.mlflow_tracking_uri

    def connect(self) -> bool:
        if self._available:
            return True
        try:
            import mlflow

            mlflow.set_tracking_uri(self._tracking_uri)
            self._available = True
            return True
        except Exception as e:
            logger.warning("MLflow unavailable (degraded mode): %s", e)
            return False

    def create_experiment(self, name: str) -> str | None:
        if not self.connect():
            return None
        try:
            import mlflow

            exp = mlflow.get_experiment_by_name(name)
            if exp:
                return exp.experiment_id
            return mlflow.create_experiment(name)
        except Exception as e:
            logger.error("MLflow create_experiment failed: %s", e)
            return None

    def log_run(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        tags: dict[str, str] | None = None,
        artifacts: dict[str, str] | None = None,
    ) -> str | None:
        if not self.connect():
            return self._local_run_id(run_name)

        try:
            import mlflow

            exp_id = self.create_experiment(experiment_name)
            if not exp_id:
                return None

            with mlflow.start_run(experiment_id=exp_id, run_name=run_name) as run:
                for k, v in params.items():
                    mlflow.log_param(k, v)
                for k, v in metrics.items():
                    mlflow.log_metric(k, float(v))
                if tags:
                    mlflow.set_tags(tags)
                if artifacts:
                    for name, path in artifacts.items():
                        p = Path(path) if not isinstance(path, Path) else path
                        if p.exists():
                            mlflow.log_artifact(str(p), artifact_path=name)
                return run.info.run_id
        except Exception as e:
            logger.error("MLflow log_run failed: %s", e)
            return self._local_run_id(run_name)

    def list_experiments(self) -> list[dict[str, Any]]:
        if not self.connect():
            return []
        try:
            import mlflow

            return [
                {"experiment_id": e.experiment_id, "name": e.name, "lifecycle_stage": e.lifecycle_stage}
                for e in mlflow.search_experiments()
            ]
        except Exception as e:
            logger.error("MLflow list_experiments failed: %s", e)
            return []

    def _local_run_id(self, run_name: str) -> str:
        return f"local-{run_name}"


_mlflow_client: MLflowClient | None = None


def get_mlflow_client() -> MLflowClient:
    global _mlflow_client
    if _mlflow_client is None:
        _mlflow_client = MLflowClient()
    return _mlflow_client
