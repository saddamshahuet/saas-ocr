"""MLOps and Continuous Learning service

Provides model training, versioning, A/B testing, and performance monitoring.
NOTE: This is a framework implementation for MLOps pipeline.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model status"""
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    created_at: datetime
    status: ModelStatus
    metrics: Dict[str, float]
    parameters: Dict[str, Any]
    deployment_percentage: float = 0.0  # For A/B testing

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "deployment_percentage": self.deployment_percentage
        }


class ModelRegistry:
    """Model registry for version management"""

    def __init__(self):
        self.models: Dict[str, List[ModelVersion]] = {}

    def register_model(
        self,
        model_id: str,
        version: str,
        metrics: Dict[str, float],
        parameters: Dict[str, Any]
    ) -> ModelVersion:
        """Register a new model version"""
        model_version = ModelVersion(
            model_id=model_id,
            version=version,
            created_at=datetime.now(),
            status=ModelStatus.TRAINED,
            metrics=metrics,
            parameters=parameters
        )

        if model_id not in self.models:
            self.models[model_id] = []

        self.models[model_id].append(model_version)

        logger.info(f"Registered model {model_id} version {version}")
        return model_version

    def get_model(self, model_id: str, version: Optional[str] = None) -> Optional[ModelVersion]:
        """Get model version"""
        if model_id not in self.models:
            return None

        if version:
            for model in self.models[model_id]:
                if model.version == version:
                    return model
            return None
        else:
            # Return latest version
            return self.models[model_id][-1] if self.models[model_id] else None

    def get_deployed_models(self, model_id: str) -> List[ModelVersion]:
        """Get deployed model versions"""
        if model_id not in self.models:
            return []

        return [
            model for model in self.models[model_id]
            if model.status == ModelStatus.DEPLOYED
        ]

    def deploy_model(
        self,
        model_id: str,
        version: str,
        deployment_percentage: float = 100.0
    ) -> bool:
        """Deploy a model version"""
        model = self.get_model(model_id, version)
        if not model:
            return False

        model.status = ModelStatus.DEPLOYED
        model.deployment_percentage = deployment_percentage

        logger.info(f"Deployed model {model_id} v{version} at {deployment_percentage}%")
        return True


@dataclass
class TrainingDataPoint:
    """Training data point from user corrections"""
    document_id: str
    field_name: str
    original_value: Any
    corrected_value: Any
    confidence: float
    created_at: datetime

    def to_dict(self) -> Dict:
        return {
            "document_id": self.document_id,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "corrected_value": self.corrected_value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }


class TrainingDataManager:
    """Manage training data from user feedback"""

    def __init__(self):
        self.data_points: List[TrainingDataPoint] = []

    def add_correction(
        self,
        document_id: str,
        field_name: str,
        original_value: Any,
        corrected_value: Any,
        confidence: float = 0.0
    ):
        """Add user correction as training data"""
        data_point = TrainingDataPoint(
            document_id=document_id,
            field_name=field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            confidence=confidence,
            created_at=datetime.now()
        )

        self.data_points.append(data_point)
        logger.info(f"Added training data point for {field_name}")

    def get_training_data(
        self,
        min_samples: int = 100
    ) -> List[TrainingDataPoint]:
        """Get training data for retraining"""
        return self.data_points[-min_samples:] if len(self.data_points) >= min_samples else []

    def export_training_data(self) -> str:
        """Export training data as JSON"""
        return json.dumps([dp.to_dict() for dp in self.data_points], indent=2)


class PerformanceMonitor:
    """Monitor model performance"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            "accuracy": [],
            "confidence": [],
            "processing_time": []
        }

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(value)

    def get_average_metric(self, metric_name: str, window: int = 100) -> float:
        """Get average metric over window"""
        if metric_name not in self.metrics:
            return 0.0

        values = self.metrics[metric_name][-window:]
        return sum(values) / len(values) if values else 0.0

    def get_metrics_summary(self) -> Dict[str, float]:
        """Get summary of all metrics"""
        return {
            name: self.get_average_metric(name)
            for name in self.metrics.keys()
        }


class ABTestManager:
    """Manage A/B testing of models"""

    def __init__(self):
        self.experiments: Dict[str, Dict] = {}

    def create_experiment(
        self,
        experiment_id: str,
        model_a: str,
        model_b: str,
        traffic_split: float = 0.5
    ):
        """Create A/B test experiment"""
        self.experiments[experiment_id] = {
            "model_a": model_a,
            "model_b": model_b,
            "traffic_split": traffic_split,
            "results": {
                "a": {"count": 0, "total_confidence": 0.0},
                "b": {"count": 0, "total_confidence": 0.0}
            }
        }

        logger.info(f"Created A/B experiment: {experiment_id}")

    def record_result(
        self,
        experiment_id: str,
        variant: str,  # "a" or "b"
        confidence: float
    ):
        """Record experiment result"""
        if experiment_id not in self.experiments:
            return

        results = self.experiments[experiment_id]["results"]
        if variant in results:
            results[variant]["count"] += 1
            results[variant]["total_confidence"] += confidence

    def get_experiment_results(self, experiment_id: str) -> Dict:
        """Get experiment results"""
        if experiment_id not in self.experiments:
            return {}

        exp = self.experiments[experiment_id]
        results = exp["results"]

        avg_conf_a = (
            results["a"]["total_confidence"] / results["a"]["count"]
            if results["a"]["count"] > 0 else 0
        )
        avg_conf_b = (
            results["b"]["total_confidence"] / results["b"]["count"]
            if results["b"]["count"] > 0 else 0
        )

        return {
            "experiment_id": experiment_id,
            "model_a": exp["model_a"],
            "model_b": exp["model_b"],
            "results_a": {
                "count": results["a"]["count"],
                "avg_confidence": avg_conf_a
            },
            "results_b": {
                "count": results["b"]["count"],
                "avg_confidence": avg_conf_b
            },
            "winner": "a" if avg_conf_a > avg_conf_b else "b"
        }


# Singletons
_model_registry = ModelRegistry()
_training_data_manager = TrainingDataManager()
_performance_monitor = PerformanceMonitor()
_ab_test_manager = ABTestManager()


def get_model_registry() -> ModelRegistry:
    """Get model registry singleton"""
    return _model_registry


def get_training_data_manager() -> TrainingDataManager:
    """Get training data manager singleton"""
    return _training_data_manager


def get_performance_monitor() -> PerformanceMonitor:
    """Get performance monitor singleton"""
    return _performance_monitor


def get_ab_test_manager() -> ABTestManager:
    """Get A/B test manager singleton"""
    return _ab_test_manager
