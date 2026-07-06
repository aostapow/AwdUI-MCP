"""Multi-backend UI detection for AwdUI."""

from detection.element_model import DetectedElement, element_to_dict
from detection.orchestrator import DetectionOrchestrator, get_orchestrator

__all__ = [
    "DetectedElement",
    "element_to_dict",
    "DetectionOrchestrator",
    "get_orchestrator",
]
