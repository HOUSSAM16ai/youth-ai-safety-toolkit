"""
Metrics Artist
==============

Responsible for visualizing software metrics artistically.
"""

import math

from microservices.orchestrator_service.src.services.overmind.art.styles import (
    ArtStyle,
    VisualTheme,
)


class MetricsArtist:
    """
    Artist for visualizing code metrics.

    CS73: Numbers can be beautiful.
    """

    def __init__(self, style: ArtStyle = ArtStyle.NATURE):
        """Initialize the artist"""
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def create_radial_chart(self, metrics: dict[str, float], title: str = "Code Metrics") -> str:
        """
        Create an artistic radial chart.

        CS73: Circles are more appealing than traditional bars.

        Args:
            metrics: Metrics to visualize
            title: Chart title

        Returns:
            str: SVG radial chart

        Complexity: O(n) where n is number of metrics
        """
        width, height = 500, 500
        center_x, center_y = width // 2, height // 2
        max_radius = 180

        # Build SVG from components
        svg = self._create_svg_header(width, height, title)
        svg += self._create_circular_grid(center_x, center_y, max_radius)

        if not metrics:
            return svg + "</svg>"

        points, metrics_svg = self._create_metric_points(metrics, center_x, center_y, max_radius)
        svg += metrics_svg
        svg += self._create_connecting_polygon(points)
        svg += "</svg>"

        return svg

    def _create_svg_header(self, width: int, height: int, title: str) -> str:
        """Create SVG header with title."""
        return f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="20"
                  font-weight="bold">{title}</text>
        '''

    def _create_circular_grid(self, center_x: int, center_y: int, max_radius: int) -> str:
        """Create circular grid background."""
        grid_svg = ""
        for i in range(1, 5):
            radius = (max_radius / 4) * i
            grid_svg += f'''
            <circle cx="{center_x}" cy="{center_y}"
                    r="{radius}"
                    fill="none"
                    stroke="{self.palette.secondary}"
                    stroke-width="1"
                    opacity="0.2"/>
            '''
        return grid_svg

    def _create_metric_points(
        self, metrics: dict[str, float], center_x: int, center_y: int, max_radius: int
    ) -> tuple[list[tuple[float, float]], str]:
        """Create metric points and their SVG elements."""
        num_metrics = len(metrics)
        angle_step = 360 / num_metrics
        max_value = max(metrics.values()) if metrics else 1

        gradient = VisualTheme.create_gradient(
            self.palette.primary, self.palette.accent, steps=num_metrics
        )

        points = []
        svg = ""

        for i, (key, value) in enumerate(metrics.items()):
            point, point_svg = self._create_single_metric_point(
                i, key, value, angle_step, max_value, max_radius, center_x, center_y, gradient[i]
            )
            points.append(point)
            svg += point_svg

        return points, svg

    def _create_single_metric_point(
        self,
        index: int,
        key: str,
        value: float,
        angle_step: float,
        max_value: float,
        max_radius: int,
        center_x: int,
        center_y: int,
        color: str,
    ) -> tuple[tuple[float, float], str]:
        """Create a single metric point with SVG elements."""
        angle = index * angle_step - 90  # Start from top
        angle_rad = math.radians(angle)

        normalized = value / max_value if max_value > 0 else 0
        radius = normalized * max_radius

        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)

        svg = f'''
            <line x1="{center_x}" y1="{center_y}"
                  x2="{x}" y2="{y}"
                  stroke="{color}"
                  stroke-width="2"
                  opacity="0.6"/>

            <circle cx="{x}" cy="{y}"
                    r="6"
                    fill="{color}"/>

            <!-- Label -->
            <text x="{x + 15}" y="{y}"
                  fill="{self.palette.text}"
                  font-size="12">{key}: {value:.1f}</text>
        '''

        return (x, y), svg

    def _create_connecting_polygon(self, points: list[tuple[float, float]]) -> str:
        """Create the polygon connecting the points."""
        if len(points) <= 2:
            return ""

        polygon_points = " ".join([f"{x},{y}" for x, y in points])
        return f'''
            <polygon points="{polygon_points}"
                     fill="{self.palette.primary}"
                     opacity="0.2"
                     stroke="{self.palette.primary}"
                     stroke-width="2"/>
        '''

    def create_bar_art(self, data: dict[str, float], title: str = "Artistic Bar Chart") -> str:
        """
        Artistic bar chart.

        CS73: Even traditional charts can be artistic.

        Args:
            data: Data to display
            title: Title

        Returns:
            str: SVG bar chart with artistic styling
        """
        width, height = 600, 400
        margin = 50
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        svg = self._create_bar_chart_header(width, height, title)

        if not data:
            return svg + "</svg>"

        bar_config = self._calculate_bar_dimensions(data, chart_width, chart_height)
        bars_svg = self._draw_bars(data, bar_config, margin, height, chart_height)

        return svg + bars_svg + "</svg>"

    def _create_bar_chart_header(self, width: int, height: int, title: str) -> str:
        """Create bar chart header."""
        return f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="20"
                  font-weight="bold">{title}</text>
        '''

    def _calculate_bar_dimensions(
        self, data: dict[str, float], chart_width: int, chart_height: int
    ) -> dict[str, object]:
        """Calculate bar dimensions and spacing."""
        num_bars = len(data)
        bar_width = chart_width / (num_bars * 2)
        spacing = bar_width
        max_value = max(data.values()) if data else 1

        gradient = VisualTheme.create_gradient(
            self.palette.primary, self.palette.secondary, steps=num_bars
        )

        return {
            "num_bars": num_bars,
            "bar_width": bar_width,
            "spacing": spacing,
            "max_value": max_value,
            "gradient": gradient,
        }

    def _draw_bars(
        self,
        data: dict[str, float],
        config: dict[str, object],
        margin: int,
        height: int,
        chart_height: int,
    ) -> str:
        """Draw all bars with labels."""
        svg = ""
        bar_width = config["bar_width"]
        spacing = config["spacing"]
        max_value = config["max_value"]
        gradient = config["gradient"]

        for i, (key, value) in enumerate(data.items()):
            x = margin + i * (bar_width + spacing)
            normalized = value / max_value if max_value > 0 else 0
            bar_height = normalized * chart_height
            y = height - margin - bar_height
            color = gradient[i]

            svg += self._draw_single_bar(
                i, x, y, bar_width, bar_height, color, value, key, height, margin
            )

        return svg

    def _draw_single_bar(
        self,
        index: int,
        x: float,
        y: float,
        bar_width: float,
        bar_height: float,
        color: str,
        value: float,
        key: str,
        height: int,
        margin: int,
    ) -> str:
        """Draw a single bar with gradient and labels."""
        return f'''
            <rect x="{x}" y="{y}"
                  width="{bar_width}"
                  height="{bar_height}"
                  fill="url(#grad{index})"
                  rx="5"/>

            <defs>
                <linearGradient id="grad{index}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:{color};stop-opacity:1" />
                    <stop offset="100%" style="stop-color:{color};stop-opacity:0.5" />
                </linearGradient>
            </defs>

            <!-- Value Label -->
            <text x="{x + bar_width / 2}" y="{y - 5}"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="12"
                  font-weight="bold">{value:.1f}</text>

            <!-- Key Label -->
            <text x="{x + bar_width / 2}" y="{height - margin + 20}"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="10"
                  transform="rotate(-45 {x + bar_width / 2} {height - margin + 20})">
                {key}
            </text>
        '''
