"""
Network Artist
==============

Responsible for visualizing networks and relationships.
"""

import math

from microservices.orchestrator_service.src.services.overmind.art.styles import (
    ArtStyle,
    VisualTheme,
)


class NetworkArtist:
    """
    Artist for visualizing networks and relationships.

    CS73: Code relationships as a beautiful web.
    """

    def __init__(self, style: ArtStyle = ArtStyle.DARK):
        """Initialize the artist"""
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def create_dependency_web(
        self,
        nodes: list[dict[str, object]],
        edges: list[tuple[str, str]],
        title: str = "Code Dependencies",
    ) -> str:
        """
        Create an artistic dependency web.

        CS73: Dependencies as a connected web of life.

        Args:
            nodes: List of nodes (modules, classes, etc.)
            edges: List of connections (from, to)
            title: Title

        Returns:
            str: SVG network visualization

        Complexity: O(n + e) where n is nodes, e is edges
        """
        width, height = 700, 700
        center_x, center_y = width // 2, height // 2
        radius = 250

        svg = self._create_network_header(width, height, title)

        if not nodes:
            return svg + "</svg>"

        node_positions = self._calculate_node_positions(nodes, center_x, center_y, radius)
        svg += self._draw_edges(edges, node_positions)
        svg += self._draw_nodes(nodes, node_positions)
        svg += "</svg>"

        return svg

    def _create_network_header(self, width: int, height: int, title: str) -> str:
        """Create network header."""
        return f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="20"
                  font-weight="bold">{title}</text>
        '''

    def _calculate_node_positions(
        self, nodes: list[dict[str, object]], center_x: int, center_y: int, radius: int
    ) -> dict[str, tuple[float, float]]:
        """Calculate node positions in a circle."""
        num_nodes = len(nodes)
        angle_step = 360 / num_nodes
        node_positions: dict[str, tuple[float, float]] = {}

        for i, node in enumerate(nodes):
            angle = i * angle_step - 90
            angle_rad = math.radians(angle)

            x = center_x + radius * math.cos(angle_rad)
            y = center_y + radius * math.sin(angle_rad)

            node_id = node.get("id", f"node_{i}")
            node_positions[node_id] = (x, y)

        return node_positions

    def _draw_edges(
        self, edges: list[tuple[str, str]], node_positions: dict[str, tuple[float, float]]
    ) -> str:
        """Draw connections between nodes."""
        svg = ""
        for source, target in edges:
            if source in node_positions and target in node_positions:
                x1, y1 = node_positions[source]
                x2, y2 = node_positions[target]

                svg += f'''
                <line x1="{x1}" y1="{y1}"
                      x2="{x2}" y2="{y2}"
                      stroke="{self.palette.secondary}"
                      stroke-width="1"
                      opacity="0.3"/>
                '''
        return svg

    def _draw_nodes(
        self, nodes: list[dict[str, object]], node_positions: dict[str, tuple[float, float]]
    ) -> str:
        """Draw nodes with labels."""
        num_nodes = len(nodes)
        gradient = VisualTheme.create_gradient(
            self.palette.primary, self.palette.accent, steps=num_nodes
        )

        svg = ""
        for i, node in enumerate(nodes):
            node_id = node.get("id", f"node_{i}")
            if node_id not in node_positions:
                continue

            x, y = node_positions[node_id]
            color = gradient[i]
            label = node.get("label", node_id)

            svg += f'''
            <circle cx="{x}" cy="{y}"
                    r="20"
                    fill="{color}"
                    stroke="{self.palette.background}"
                    stroke-width="3"/>

            <text x="{x}" y="{y + 35}"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="11">{label}</text>
            '''

        return svg
