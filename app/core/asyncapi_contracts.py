"""أدوات تحقق خفيفة لضمان صلاحية عقود AsyncAPI ضمن نهج API-First."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AsyncAPIContractReport:
    """يمثل تقرير تحقق مبسط لعقد AsyncAPI."""

    errors: tuple[str, ...]

    def is_clean(self) -> bool:
        """يتحقق مما إذا كان التقرير خالياً من الأخطاء."""
        return not self.errors


def default_asyncapi_contract_path() -> Path:
    """يبني المسار الافتراضي لعقد AsyncAPI الأساسي."""
    return (
        Path(__file__).resolve().parents[2] / "docs" / "contracts" / "asyncapi" / "events-api.yaml"
    )


def validate_asyncapi_contract_structure(spec_path: Path) -> AsyncAPIContractReport:
    """
    يتحقق من البنية الأساسية لعقد AsyncAPI بشكل حازم ومباشر.

    هذا التحقق لا يعوض المدققات الرسمية، لكنه يمنع الفجوات الأساسية
    مثل غياب `asyncapi` أو القنوات.
    """
    if not spec_path.exists():
        return AsyncAPIContractReport(errors=(f"AsyncAPI spec not found: {spec_path}",))

    text = spec_path.read_text(encoding="utf-8")
    top_level = _scan_top_level_keys(text)

    errors: list[str] = []
    if "asyncapi" not in top_level:
        errors.append("Missing asyncapi version in contract.")
    if "info" not in top_level:
        errors.append("Missing info section in contract.")
    if "channels" not in top_level:
        errors.append("Missing channels section in contract.")

    channels = _extract_channels_from_yaml(text)
    if not channels:
        errors.append("Channels section must be a non-empty mapping.")

    channels_missing_ops = [name for name, has_ops in channels.items() if not has_ops]
    for channel in channels_missing_ops:
        errors.append(f"Channel {channel} must define publish, subscribe, or messages.")

    return AsyncAPIContractReport(errors=tuple(errors))


def _scan_top_level_keys(text: str) -> set[str]:
    """يمسح هذا التابع المفاتيح العليا في YAML لتجنب محللات معقدة."""
    keys: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith(" "):
            continue
        if ":" in stripped:
            key = stripped.split(":", maxsplit=1)[0].strip()
            if key:
                keys.add(key)
    return keys


def _extract_channels_from_yaml(text: str) -> dict[str, bool]:
    """يستخرج القنوات ويحدد ما إذا كانت تحتوي publish أو subscribe."""
    # This is a very basic parser and prone to errors with complex YAML,
    # but serves the purpose of a quick check.
    import yaml

    try:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return {}
        channels = data.get("channels", {})
        if not isinstance(channels, dict):
            return {}

        result = {}
        for name, content in channels.items():
            if not isinstance(content, dict):
                result[name] = False
                continue

            # AsyncAPI 2.x uses publish/subscribe
            has_pub_sub = "publish" in content or "subscribe" in content
            # AsyncAPI 3.0 uses messages
            has_messages = "messages" in content

            result[name] = has_pub_sub or has_messages

        return result
    except Exception:
        # Fallback to manual parsing if yaml fails or dependency missing
        return _extract_channels_from_yaml_manual(text)


def _extract_channels_from_yaml_manual(text: str) -> dict[str, bool]:
    """يستخرج القنوات ويحدد ما إذا كانت تحتوي publish أو subscribe (manual fallback)."""
    lines = text.splitlines()
    channels_indent: int | None = None
    channels: dict[str, bool] = {}
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if stripped == "channels:":
            channels_indent = len(line) - len(line.lstrip(" "))
            index += 1
            break
        index += 1

    if channels_indent is None:
        return channels

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= channels_indent:
            break

        if stripped.endswith(":") and indent == channels_indent + 2:
            channel_name = stripped[:-1]
            channels[channel_name] = _channel_has_operations(
                lines,
                start=index + 1,
                base_indent=indent,
            )
        index += 1

    return channels


def _channel_has_operations(
    lines: list[str],
    *,
    start: int,
    base_indent: int,
) -> bool:
    """يتحقق مما إذا كانت القناة تحتوي publish أو subscribe."""
    index = start
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= base_indent:
            break
        if stripped in {"publish:", "subscribe:", "messages:"}:
            return True
        index += 1
    return False
