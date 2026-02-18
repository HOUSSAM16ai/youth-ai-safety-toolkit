"""
Code Pattern Artist
===================

Responsible for generating generative art patterns based on code structures.
"""

import math
import random

from microservices.orchestrator_service.src.services.overmind.art.styles import (
    ArtStyle,
    VisualTheme,
)


class CodePatternArtist:
    """
    Artist for generative code patterns.

    CS73: Every software project has its unique artistic fingerprint.
    """

    def __init__(self, style: ArtStyle = ArtStyle.CYBERPUNK):
        """Initialize the artist"""
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def generate_fractal_tree(self, complexity: int = 5, seed: int | None = None) -> str:
        """
        Generate a fractal tree representing code structure.

        CS73: Fractals represent recursion and self-similarity in programming.

        Args:
            complexity: Depth level (number of branches)
            seed: Random seed for reproducibility

        Returns:
            str: SVG fractal tree

        Complexity: O(2^n) where n is complexity level
        """
        if seed is not None:
            random.seed(seed)

        width, height = 600, 600
        start_x, start_y = width // 2, height - 50

        svg = f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">
        '''

        # Draw fractal tree
        branches = self._draw_branch(
            start_x,
            start_y,
            -90,  # angle (up)
            100,  # length
            complexity,
            self.palette.primary,
        )
        svg += branches

        svg += f'''
            <text x="10" y="30"
                  fill="{self.palette.text}"
                  font-size="16"
                  font-weight="bold">Fractal Code Tree</text>
        </svg>
        '''

        return svg

    def _draw_branch(
        self, x: float, y: float, angle: float, length: float, depth: int, color: str
    ) -> str:
        """
        Draw a branch recursively (Recursive Fractal).

        CS73: Recursion creates beauty from simplicity.
        """
        if depth <= 0 or length < 2:
            return ""

        # Calculate end point
        angle_rad = math.radians(angle)
        end_x = x + length * math.cos(angle_rad)
        end_y = y + length * math.sin(angle_rad)

        # Color gradient by depth
        gradient = VisualTheme.create_gradient(self.palette.primary, self.palette.accent, steps=10)
        color_index = min(10 - depth, len(gradient) - 1)
        branch_color = gradient[color_index]

        # Draw branch
        svg = f'''
        <line x1="{x}" y1="{y}"
              x2="{end_x}" y2="{end_y}"
              stroke="{branch_color}"
              stroke-width="{depth}"
              opacity="0.8"/>
        '''

        # Recursive branches
        new_length = length * 0.7
        angle_variation = 25 + random.uniform(-10, 10)

        # Left branch
        svg += self._draw_branch(
            end_x, end_y, angle - angle_variation, new_length, depth - 1, color
        )

        # Right branch
        svg += self._draw_branch(
            end_x, end_y, angle + angle_variation, new_length, depth - 1, color
        )

        return svg

    def generate_spiral_code(self, iterations: int = 100, data_seed: int = 42) -> str:
        """
        Generate a spiral representing code evolution.

        CS73: The spiral symbolizes continuous growth and development.

        Args:
            iterations: Number of iterations
            data_seed: Data seed

        Returns:
            str: SVG spiral art

        Complexity: O(n)
        """
        width, height = 600, 600
        center_x, center_y = width // 2, height // 2

        svg = f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">
        '''

        # Calculate spiral points
        points = []
        for i in range(iterations):
            angle = i * (360 / 16) * math.pi / 180
            radius = 2 + i * 2

            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append((x, y))

        # Draw connected lines
        gradient = VisualTheme.create_gradient(
            self.palette.primary, self.palette.secondary, steps=iterations
        )

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            color = gradient[i]

            svg += f'''
            <line x1="{x1}" y1="{y1}"
                  x2="{x2}" y2="{y2}"
                  stroke="{color}"
                  stroke-width="2"
                  opacity="0.8"/>
            '''

        svg += f'''
            <text x="10" y="30"
                  fill="{self.palette.text}"
                  font-size="16"
                  font-weight="bold">Code Evolution Spiral</text>
        </svg>
        '''

        return svg
