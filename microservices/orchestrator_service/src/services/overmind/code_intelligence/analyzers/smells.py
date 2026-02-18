from typing import ClassVar

from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    FileMetrics,
)


class StructuralSmellDetector:
    """Structural Smell Detector"""

    # God class thresholds
    GOD_CLASS_LOC_THRESHOLD = 500
    GOD_CLASS_METHODS_THRESHOLD = 20

    # Layer mixing patterns

    LAYER_PATTERNS: ClassVar[dict[str, list[str]]] = {
        "api": ["api", "routers", "endpoints", "controllers"],
        "service": ["services", "use_cases", "application"],
        "infrastructure": ["infrastructure", "repositories", "adapters"],
        "domain": ["domain", "models", "entities"],
    }

    def detect_smells(
        self, file_path: str, metrics: FileMetrics, imports: list[str]
    ) -> dict[str, bool]:
        """Detect structural smells"""
        smells = {
            "is_god_class": False,
            "has_layer_mixing": False,
            "has_cross_layer_imports": False,
        }

        # God class detection
        if metrics.num_classes > 0 and (
            metrics.code_lines > self.GOD_CLASS_LOC_THRESHOLD
            or metrics.num_functions > self.GOD_CLASS_METHODS_THRESHOLD
        ):
            smells["is_god_class"] = True

        # Detect current file layer
        current_layer = self._detect_layer(file_path)

        # Check for layer mixing in imports
        if current_layer:
            import_layers = set()
            for imp in imports:
                imp_layer = self._detect_layer(imp)
                if imp_layer and imp_layer != current_layer:
                    import_layers.add(imp_layer)

            # Cross-layer imports (e.g., service importing from api)
            if import_layers:
                smells["has_cross_layer_imports"] = True

                # Layer mixing (multiple responsibilities)
                if len(import_layers) > 1:
                    smells["has_layer_mixing"] = True

        return smells

    def _detect_layer(self, path: str) -> str | None:
        """Detect architectural layer from path"""
        path_lower = path.lower()
        for layer, patterns in self.LAYER_PATTERNS.items():
            if any(pattern in path_lower for pattern in patterns):
                return layer
        return None
