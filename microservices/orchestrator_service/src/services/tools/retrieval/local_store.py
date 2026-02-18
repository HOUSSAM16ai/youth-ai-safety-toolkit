"""
Local Knowledge Base Retrieval (Fallback Mechanism).
Infrastructure Layer.
"""

from pathlib import Path

import yaml

from microservices.orchestrator_service.src.core.logging import get_logger
from . import parsing

_SUBJECT_VARIANTS = {
    "رياضيات": {"mathematics", "math", "الرياضيات", "مادة الرياضيات"},
    "mathematics": {"رياضيات", "math", "الرياضيات"},
}

_BRANCH_VARIANTS = {
    "علوم تجريبية": {"experimental sciences", "experimental_sciences", "science", "sciences"},
    "experimental sciences": {"علوم تجريبية", "science", "sciences"},
    "experimental_sciences": {"علوم تجريبية", "experimental sciences", "science", "sciences"},
}

_EXAM_REF_VARIANTS = {
    "الموضوع الأول": {"subject 1", "subject_1", "الموضوع 1", "موضوع 1"},
    "الموضوع الثاني": {"subject 2", "subject_2", "الموضوع 2", "موضوع 2"},
    "الموضوع الثالث": {"subject 3", "subject_3", "الموضوع 3", "موضوع 3"},
}

logger = get_logger("tool-retrieval-local")

# Directories to search for content
SEARCH_DIRECTORIES = [
    Path("knowledge_base"),
    Path("data/knowledge"),
    Path("content"),  # Recursive search might be needed here
]


def search_local_knowledge_base(
    query: str,
    year: str | None,
    subject: str | None,
    branch: str | None,
    exam_ref: str | None,
) -> str:
    """
    بحث احتياطي في الملفات المحلية في حال تعطل خدمة الذاكرة أو عدم وجود نتائج.
    """
    matches = []

    # Collect all MD files from all directories
    md_files = []
    for directory in SEARCH_DIRECTORIES:
        if not directory.exists():
            continue
        # Use rglob for recursive search (especially for 'content/')
        md_files.extend(directory.rglob("*.md"))

    if not md_files:
        return "قاعدة المعرفة المحلية غير موجودة أو فارغة."

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Extract frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_raw = parts[1]
                    body = parts[2]

                    try:
                        metadata = yaml.safe_load(frontmatter_raw)
                        meta_dict = metadata.get("metadata", {})

                        # Handle flat metadata (some files might not have 'metadata' key nested)
                        if (
                            not meta_dict
                            and isinstance(metadata, dict)
                            and ("year" in metadata or "subject" in metadata)
                        ):
                            # Check if keys like 'year' are at root
                            meta_dict = metadata

                        # Flexible Matching Logic for Fallback
                        # 1. Check Year
                        if year and str(meta_dict.get("year", "")) != str(year):
                            continue

                        # 2. Check Subject
                        if subject:
                            file_subject = str(meta_dict.get("subject", "")).lower()
                            if not _matches_semantic_value(
                                subject, file_subject, _SUBJECT_VARIANTS
                            ):
                                continue

                        # 3. Check Branch
                        if branch:
                            file_branch = meta_dict.get("branch", "")
                            branch_query = branch.lower().replace("_", " ")

                            if isinstance(file_branch, list):
                                # Normalize file branches too
                                file_branches_norm = [
                                    str(b).lower().replace("_", " ") for b in file_branch
                                ]
                                if not any(
                                    b in branch_query or branch_query in b
                                    for b in file_branches_norm
                                ):
                                    continue
                            else:
                                file_branch_norm = str(file_branch).lower().replace("_", " ")
                                if not _matches_semantic_value(
                                    branch_query, file_branch_norm, _BRANCH_VARIANTS
                                ):
                                    continue

                        # 4. Check Exam Ref
                        # Exam Ref might be 'set' in some files
                        if exam_ref:
                            file_ref = str(
                                meta_dict.get("exam_ref", "") or meta_dict.get("set", "")
                            ).lower()
                            if not _matches_semantic_value(exam_ref, file_ref, _EXAM_REF_VARIANTS):
                                continue

                        # 5. Extract Specific Exercise if requested
                        extracted_exercise = parsing.extract_specific_exercise(body, query)

                        is_specific = parsing.is_specific_request(query)

                        if extracted_exercise:
                            matches.append(extracted_exercise)
                        elif not is_specific:
                            # Only append full body if request was NOT specific
                            matches.append(body.strip())
                        elif _is_relevant_fallback(meta_dict, body, query) or (year and subject):
                            # Fallback: If specific but not found in headers,
                            # check if the file itself is the "specific" thing requested.
                            # e.g. Title contains the query topic or tags contain it.
                            # OR if strong metadata (Year + Subject) is present, implies relevance.

                            # If the user did NOT explicitly ask for the solution, strip it.
                            if not parsing.is_solution_request(query):
                                clean_body = parsing.remove_solution_section(body)
                                matches.append(clean_body)
                            else:
                                matches.append(body.strip())

                    except yaml.YAMLError:
                        logger.error(f"Failed to parse YAML in {md_file}")
                        continue
            else:
                metadata, body = _parse_inline_metadata(content)
                if not metadata:
                    continue

                if year and str(metadata.get("year", "")) != str(year):
                    continue

                if subject:
                    file_subject = str(metadata.get("subject", "")).lower()
                    if not _matches_semantic_value(subject, file_subject, _SUBJECT_VARIANTS):
                        continue

                if branch:
                    file_branch_norm = str(metadata.get("branch", "")).lower().replace("_", " ")
                    branch_query = branch.lower().replace("_", " ")
                    if not _matches_semantic_value(
                        branch_query, file_branch_norm, _BRANCH_VARIANTS
                    ):
                        continue

                if exam_ref:
                    file_ref = str(metadata.get("exam_ref", "") or metadata.get("set", "")).lower()
                    if not _matches_semantic_value(exam_ref, file_ref, _EXAM_REF_VARIANTS):
                        continue

                extracted_exercise = parsing.extract_specific_exercise(body, query)
                is_specific = parsing.is_specific_request(query)

                if extracted_exercise:
                    matches.append(extracted_exercise)
                elif (
                    not is_specific
                    or _is_relevant_fallback(metadata, body, query)
                    or (year and subject)
                ):
                    # Check for solution stripping in fallback case too
                    if not parsing.is_solution_request(query):
                        clean_body = parsing.remove_solution_section(body)
                        matches.append(clean_body)
                    else:
                        matches.append(body.strip())

            # Support files without frontmatter or with different format?
            # For now, we stick to frontmatter-based files as per original logic,
            # but 'content/' files often have frontmatter too.

        except Exception as e:
            logger.error(f"Error reading file {md_file}: {e}")
            continue

    if not matches:
        return "لم يتم العثور على محتوى مطابق في الملفات المحلية (وضع عدم الاتصال)."

    # Deduplicate matches
    unique_matches = parsing.deduplicate_contents(matches)

    return "\n\n".join(unique_matches[:3]).strip()


def _matches_semantic_value(query: str, file_value: str, variants_map: dict[str, set[str]]) -> bool:
    """
    مطابقة مرنة بين قيم الاستعلام والقيم المخزنة في الملفات.
    """
    query_norm = query.lower().strip()
    file_norm = file_value.lower().strip()

    if query_norm in file_norm or file_norm in query_norm:
        return True

    variants = variants_map.get(query_norm, set())
    return any(variant in file_norm or file_norm in variant for variant in variants)


def _is_relevant_fallback(metadata: dict, body: str, query: str) -> bool:
    """
    Check if the file is relevant to the specific query (topic/keyword)
    even if a specific section wasn't extracted.
    """
    query_norm = query.lower().strip()
    query_tokens = query_norm.split()

    # Check title
    title = str(metadata.get("title", "")).lower()
    for token in query_tokens:
        if len(token) < 3:  # Skip short words to avoid noise
            continue
        if token in title:
            return True

    # Check tags
    tags = metadata.get("tags", [])
    if isinstance(tags, list):
        for tag in tags:
            tag_str = str(tag).lower()
            for token in query_tokens:
                if len(token) < 3:
                    continue
                if token in tag_str:
                    return True

    return False


def _parse_inline_metadata(content: str) -> tuple[dict[str, object], str]:
    """
    استخراج بيانات وصفية في حال كانت في بداية الملف بدون فاصل YAML.
    """
    lines = content.splitlines()
    metadata_lines: list[str] = []
    body_start = 0

    for idx, line in enumerate(lines):
        if not line.strip():
            body_start = idx + 1
            break
        if ":" not in line:
            metadata_lines = []
            body_start = 0
            break
        metadata_lines.append(line)

    if not metadata_lines:
        return {}, content

    try:
        metadata = yaml.safe_load("\n".join(metadata_lines)) or {}
    except yaml.YAMLError:
        return {}, content

    body = "\n".join(lines[body_start:]).strip()
    return metadata if isinstance(metadata, dict) else {}, body
