# app/services/overmind/art/visualizer.py
"""
🎨 CS73: Data Visualization as Art
===================================

تحويل البيانات البرمجية إلى فن بصري.
يطبق مبادئ التصميم الجرافيكي والتصور الإبداعي.

CS73 Core Concepts:
- Data as Medium: البيانات كوسيط فني
- Algorithmic Composition: التركيب الخوارزمي
- Interactive Aesthetics: الجماليات التفاعلية
- Visual Storytelling: السرد البصري
"""

from microservices.orchestrator_service.src.services.overmind.art.styles import (
    ArtStyle,
    VisualTheme,
)


class CodeArtVisualizer:
    """
    محول البيانات البرمجية إلى تصور فني.

    CS73: يعامل البيانات كمادة فنية خام يمكن تشكيلها
    وتحويلها إلى أعمال بصرية ذات معنى وجمال.
    """

    def __init__(self, style: ArtStyle = ArtStyle.MINIMALIST):
        """
        تهيئة المصور الفني.

        Args:
            style: النمط الفني المستخدم
        """
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def create_complexity_art(
        self, complexity_data: dict[str, object], title: str = "Code Complexity Landscape"
    ) -> str:
        """
        إنشاء فن بصري من بيانات التعقيد.

        CS73 Concept: التعقيد البرمجي كمنحوتة طبوغرافية.

        Args:
            complexity_data: بيانات التعقيد (complexity, functions, etc.)
            title: عنوان العمل الفني

        Returns:
            str: تمثيل HTML/SVG للفن

        Example:
            >>> visualizer = CodeArtVisualizer(ArtStyle.CYBERPUNK)
            >>> art = visualizer.create_complexity_art({
            ...     "avg_complexity": 5.2,
            ...     "max_complexity": 15,
            ...     "functions": 42
            ... })
        """
        avg_complexity = complexity_data.get("avg_complexity", 0)
        max_complexity = complexity_data.get("max_complexity", 0)
        functions = complexity_data.get("functions", 0)

        # إنشاء تدرج لوني يمثل التعقيد
        complexity_ratio = min(avg_complexity / 10, 1.0)
        gradient_colors = VisualTheme.create_gradient(
            self.palette.success, self.palette.error, steps=10
        )
        color_index = int(complexity_ratio * (len(gradient_colors) - 1))
        complexity_color = gradient_colors[color_index]

        # SVG Art: دوائر متحدة المركز تمثل التعقيد
        return self._generate_complexity_circles_svg(
            avg_complexity, max_complexity, functions, complexity_color, title
        )

    def _generate_complexity_circles_svg(
        self, avg: float, max_val: float, count: int, color: str, title: str
    ) -> str:
        """
        توليد دوائر SVG تمثل التعقيد.

        CS73: الأشكال الهندسية البسيطة يمكن أن تحمل معنى عميق.
        """
        width, height = 600, 400
        center_x, center_y = width // 2, height // 2

        # حساب نصف قطر الدوائر
        max_radius = min(width, height) // 3
        avg_radius = int(max_radius * (avg / max_val)) if max_val > 0 else 0

        return f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <!-- Title -->
            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="20"
                  font-weight="bold">{title}</text>

            <!-- Max Complexity Circle (Outer) -->
            <circle cx="{center_x}" cy="{center_y}"
                    r="{max_radius}"
                    fill="none"
                    stroke="{self.palette.secondary}"
                    stroke-width="2"
                    stroke-dasharray="5,5"
                    opacity="0.3"/>

            <!-- Average Complexity Circle (Middle) -->
            <circle cx="{center_x}" cy="{center_y}"
                    r="{avg_radius}"
                    fill="{color}"
                    opacity="0.6"/>

            <!-- Center Point -->
            <circle cx="{center_x}" cy="{center_y}"
                    r="5"
                    fill="{self.palette.accent}"/>

            <!-- Function Count Visualization -->
            <text x="{width // 2}" y="{height - 30}"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="14">
                Functions: {count} | Avg: {avg:.1f} | Max: {max_val:.0f}
            </text>

        </svg>'''

    def create_metrics_dashboard(
        self, metrics: dict[str, object], title: str = "Code Metrics Art"
    ) -> str:
        """
        إنشاء لوحة فنية من المقاييس البرمجية.

        CS73: تحويل الأرقام إلى قصة بصرية.

        Args:
            metrics: مقاييس مختلفة (lines, classes, functions, etc.)
            title: عنوان اللوحة

        Returns:
            str: HTML dashboard
        """
        html = f"""
        <div style="background: {self.palette.background};
                    padding: 20px;
                    border-radius: 10px;
                    color: {self.palette.text};
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">

            <h2 style="color: {self.palette.primary}; text-align: center;">
                {title}
            </h2>

            <div style="display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin-top: 20px;">
        """

        # إنشاء بطاقة لكل مقياس
        for key, value in metrics.items():
            color = self._get_metric_color(key)
            card_html = self._create_metric_card(key, value, color)
            html += card_html

        html += """
            </div>
        </div>
        """

        return html

    def _get_metric_color(self, metric_name: str) -> str:
        """اختيار لون مناسب لكل مقياس"""
        metric_colors = {
            "lines": self.palette.info,
            "classes": self.palette.primary,
            "functions": self.palette.secondary,
            "complexity": self.palette.warning,
            "errors": self.palette.error,
            "warnings": self.palette.warning,
            "success": self.palette.success,
        }

        for key, color in metric_colors.items():
            if key in metric_name.lower():
                return color

        return self.palette.accent

    def _create_metric_card(self, name: str, value: object, color: str) -> str:
        """إنشاء بطاقة فنية لمقياس واحد"""
        text_color = VisualTheme.get_contrasting_color(color)

        return f"""
        <div style="background: {color};
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                    transition: transform 0.2s;">

            <div style="font-size: 14px;
                        color: {text_color};
                        opacity: 0.9;
                        text-transform: uppercase;
                        letter-spacing: 1px;">
                {name.replace("_", " ")}
            </div>

            <div style="font-size: 32px;
                        color: {text_color};
                        font-weight: bold;
                        margin-top: 10px;">
                {value}
            </div>
        </div>
        """


class MissionFlowArtist:
    """
    فنان تصور سير المهام (Mission Flow).

    CS73: تحويل سير العمل إلى سرد بصري.
    """

    def __init__(self, style: ArtStyle = ArtStyle.MODERN):
        """تهيئة الفنان"""
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def create_mission_timeline(
        self, mission_data: dict[str, object], title: str = "Mission Journey"
    ) -> str:
        """
        إنشاء خط زمني فني للمهمة.

        CS73: الزمن كبعد فني.

        Args:
            mission_data: بيانات المهمة (events, phases, timestamps)
            title: عنوان الخط الزمني

        Returns:
            str: SVG timeline art
        """
        events = mission_data.get("events", [])
        width, height = 800, 300

        svg = f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="24"
                  font-weight="bold">{title}</text>

            <!-- Timeline Line -->
            <line x1="50" y1="{height // 2}"
                  x2="{width - 50}" y2="{height // 2}"
                  stroke="{self.palette.primary}"
                  stroke-width="4"/>
        '''

        # إضافة نقاط الأحداث
        if events:
            step = (width - 100) / max(len(events) - 1, 1)
            for i, event in enumerate(events):
                x = 50 + i * step
                y = height // 2

                event_name = event.get("name", f"Event {i + 1}")
                event_color = self._get_event_color(event.get("type", "info"))

                svg += f'''
                <!-- Event Point -->
                <circle cx="{x}" cy="{y}"
                        r="10"
                        fill="{event_color}"
                        stroke="{self.palette.background}"
                        stroke-width="3"/>

                <!-- Event Label -->
                <text x="{x}" y="{y + 40}"
                      text-anchor="middle"
                      fill="{self.palette.text}"
                      font-size="12">{event_name}</text>
                '''

        svg += "</svg>"
        return svg

    def _get_event_color(self, event_type: str) -> str:
        """تحديد لون الحدث حسب نوعه"""
        event_colors = {
            "start": self.palette.info,
            "success": self.palette.success,
            "error": self.palette.error,
            "warning": self.palette.warning,
            "info": self.palette.accent,
        }
        return event_colors.get(event_type.lower(), self.palette.primary)


class DataArtGenerator:
    """
    مولد الفن التوليدي من البيانات.

    CS73: الخوارزميات كأداة فنية.
    """

    def __init__(self, style: ArtStyle = ArtStyle.GRADIENT):
        """تهيئة المولد"""
        self.style = style
        self.palette = VisualTheme.get_palette(style)

    def generate_code_pattern(
        self, code_data: dict[str, object], size: tuple[int, int] = (600, 600)
    ) -> str:
        """
        توليد نمط فني من بنية الكود.

        CS73: الكود كبصمة فريدة قابلة للتصور.

        Args:
            code_data: بيانات الكود (structure, patterns, etc.)
            size: حجم الفن (width, height)

        Returns:
            str: SVG pattern art
        """
        width, height = size

        # استخراج الأنماط
        functions = code_data.get("functions", 0)
        classes = code_data.get("classes", 0)
        lines = code_data.get("lines", 0)

        # توليد نمط فريد بناءً على البيانات
        svg = f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">
        '''

        # إنشاء نمط هندسي
        grid_size = 20
        for i in range(0, width, grid_size):
            for j in range(0, height, grid_size):
                # حساب لون بناءً على الموقع والبيانات
                color_index = ((i + j + functions + classes) % 100) / 100
                colors = VisualTheme.create_gradient(
                    self.palette.primary, self.palette.accent, steps=100
                )
                color = colors[int(color_index * (len(colors) - 1))]

                # رسم مربع صغير
                opacity = 0.3 + (lines % 7) / 10
                svg += f'''
                <rect x="{i}" y="{j}"
                      width="{grid_size - 2}"
                      height="{grid_size - 2}"
                      fill="{color}"
                      opacity="{opacity}"/>
                '''

        svg += "</svg>"
        return svg

    def create_data_sculpture(self, data: dict[str, float], title: str = "Data Sculpture") -> str:
        """
        إنشاء منحوتة بيانات ثلاثية الأبعاد (pseudo-3D).

        CS73: البيانات كمادة نحتية.

        Args:
            data: قيم مختلفة للنحت
            title: عنوان المنحوتة

        Returns:
            str: SVG 3D-like visualization
        """
        width, height = 500, 500
        center_x, center_y = width // 2, height // 2

        svg = f'''<svg width="{width}" height="{height}"
                       xmlns="http://www.w3.org/2000/svg"
                       style="background: {self.palette.background};">

            <text x="{width // 2}" y="30"
                  text-anchor="middle"
                  fill="{self.palette.text}"
                  font-size="20"
                  font-weight="bold">{title}</text>
        '''

        # إنشاء طبقات متعددة تمثل البيانات
        max_value = max(data.values()) if data else 1
        radius_step = 150 / len(data) if data else 0

        for i, (key, value) in enumerate(data.items()):
            radius = 50 + i * radius_step
            normalized_value = value / max_value if max_value > 0 else 0

            # اختيار لون من التدرج
            gradient = VisualTheme.create_gradient(
                self.palette.primary, self.palette.secondary, steps=len(data)
            )
            color = gradient[i] if i < len(gradient) else self.palette.accent

            # رسم دائرة تمثل القيمة
            opacity = 0.3 + normalized_value * 0.5
            svg += f'''
            <circle cx="{center_x}" cy="{center_y}"
                    r="{radius}"
                    fill="{color}"
                    opacity="{opacity}"
                    stroke="{self.palette.accent}"
                    stroke-width="2"/>

            <text x="{center_x + radius}" y="{center_y}"
                  fill="{self.palette.text}"
                  font-size="12">{key}: {value:.2f}</text>
            '''

        svg += "</svg>"
        return svg
