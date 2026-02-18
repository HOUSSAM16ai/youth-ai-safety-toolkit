from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    ComplexityStats,
    LineStats,
)


class StatisticsAnalyzer:
    """Analyzer for code statistics."""

    def count_lines(self, lines: list[str]) -> LineStats:
        """
        Count different types of lines.

        Args:
            lines: List of file lines

        Returns:
            LineStats: Basic line statistics
        """
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1

        return LineStats(
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
        )

    def calculate_complexity_stats(self, functions: list[dict[str, object]]) -> ComplexityStats:
        """
        Calculate complexity and nesting statistics.

        Args:
            functions: List of function details

        Returns:
            ComplexityStats: Complexity and nesting summary
        """
        function_complexities = [f["complexity"] for f in functions]
        nesting_depths = [f["nesting_depth"] for f in functions]

        if not function_complexities:
            return ComplexityStats(
                avg_complexity=0.0,
                max_complexity=0,
                max_func_name="",
                std_dev=0.0,
                avg_nesting=0.0,
            )

        avg_complexity = sum(function_complexities) / len(function_complexities)
        max_complexity = max(function_complexities)

        # Find function with max complexity
        max_func_name = ""
        for f in functions:
            if f["complexity"] == max_complexity:
                max_func_name = f["name"]
                break

        # Calculate standard deviation
        std_dev = self.calculate_standard_deviation(function_complexities, avg_complexity)
        avg_nesting = sum(nesting_depths) / len(nesting_depths) if nesting_depths else 0.0

        return ComplexityStats(
            avg_complexity=avg_complexity,
            max_complexity=max_complexity,
            max_func_name=max_func_name,
            std_dev=std_dev,
            avg_nesting=avg_nesting,
        )

    def calculate_standard_deviation(self, values: list[float], mean: float) -> float:
        """
        Calculate standard deviation of a list of values.

        Args:
            values: Values to calculate standard deviation for
            mean: Mean of the values

        Returns:
            float: Standard deviation
        """
        if len(values) <= 1:
            return 0.0
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return variance**0.5
