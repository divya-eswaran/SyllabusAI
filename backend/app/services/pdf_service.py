"""
PDF Service — extracts structured syllabus data from university PDF files.

Strategy:
1. Use PyMuPDF to extract raw text page by page.
2. Apply rule-based heuristics to detect:
   - Subject codes
   - Subject names
   - Credits
   - L/T/P
   - Course type
   - Semester
   - Units and topics
   - Course objectives and outcomes
3. Return a list of SubjectData dictionaries ready for DB insertion.
"""

import re
import logging
from typing import Optional

import fitz  # PyMuPDF


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ─────────────────────────────────────────────────────────────

# Supports both:
#
#   Subject Code: IT501
#   Course Code: CS301
#
# and Anna University style codes:
#
#   IT23C01
#   IT23401
#   IT23501
#   EN23C01
#   MA23C01
#
RE_SUBJECT_CODE = re.compile(
    r"\b([A-Z]{2,5}\d{2,3}[A-Z]?\d{2,3})\b",
    re.IGNORECASE,
)


# Explicit subject/course name
RE_SUBJECT_NAME = re.compile(
    r"(?:subject\s+name|course\s+name|course\s+title)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


# Credits
RE_CREDITS = re.compile(
    r"credits?\s*[:\-]\s*(\d+)",
    re.IGNORECASE,
)


# L/T/P
RE_LTP = re.compile(
    r"L\s*/\s*T\s*/\s*P\s*[:\-]\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)


# Semester
RE_SEMESTER = re.compile(
    r"semester\s*[:\-]\s*(I{1,3}V?|VI{0,3}|[1-8])\b",
    re.IGNORECASE,
)


# Course type
RE_COURSE_TYPE = re.compile(
    r"(?:course\s+type|category)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


# UNIT headers:
#
# UNIT I
# UNIT - II
# Unit 1
# MODULE I
#
RE_UNIT_HEADER = re.compile(
    r"^(?:UNIT|MODULE)\s*[-–]?\s*"
    r"(I{1,4}V?|VI{0,3}|\d{1,2})"
    r"\s*[-–]?\s*(.*)?$",
    re.IGNORECASE | re.MULTILINE,
)


# Course objectives / outcomes
RE_OBJECTIVES = re.compile(
    r"course\s+objective",
    re.IGNORECASE,
)

RE_OUTCOMES = re.compile(
    r"course\s+outcome",
    re.IGNORECASE,
)


# Bullet / numbered list items
RE_LIST_ITEM = re.compile(
    r"^[\s]*(?:[\•\-\*\u2022\u25cb\u25cf]|\d+[\.\)])\s+(.+)$"
)


# CO lines:
#
# CO1: ...
# CO 1 - ...
# CO1 – ...
#
RE_CO_LINE = re.compile(
    r"^(CO\s*\d+)\s*[:\-–]\s*(.+)$",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def _roman_to_int(roman: str) -> int:
    """Convert Roman numeral or numeric string to integer."""

    roman = roman.upper().strip()

    mapping = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
    }

    if roman in mapping:
        return mapping[roman]

    if roman.isdigit():
        return int(roman)

    return 1


def extract_pdf_text_pages(pdf_bytes: bytes) -> list[dict]:
    """
    Extract text from every page of the PDF.

    Returns:
        [
            {
                "page_num": 1,
                "text": "..."
            },
            ...
        ]
    """

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf",
    )

    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text")

        pages.append(
            {
                "page_num": i + 1,
                "text": text,
            }
        )

    doc.close()

    return pages


# ─────────────────────────────────────────────────────────────
# SUBJECT BLOCK SPLITTING
# ─────────────────────────────────────────────────────────────

def _split_into_subject_blocks(full_text: str) -> list[str]:
    """
    Split the PDF text into subject blocks using subject codes.

    Supports formats such as:

        IT23C01 Design and Analysis of Algorithms

    or:

        IT23C01
        Design and Analysis of Algorithms

    Subject names can continue onto multiple lines.
    """

    matches = list(
        RE_SUBJECT_CODE.finditer(full_text)
    )

    if not matches:
        logger.warning(
            "No subject codes found in PDF text"
        )
        return []

    blocks = []

    for i, match in enumerate(matches):

        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(full_text)

        block = full_text[start:end].strip()

        if block:
            blocks.append(block)

    return blocks


# ─────────────────────────────────────────────────────────────
# LIST ITEM EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_list_items(
    lines: list[str],
    start_idx: int,
    stop_pattern,
) -> tuple[list[str], int]:
    """
    Collect bullet / numbered list items until a stop pattern.
    """

    items = []

    i = start_idx

    while i < len(lines):

        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if stop_pattern and stop_pattern.search(line):
            break

        match = RE_LIST_ITEM.match(lines[i])

        if match:
            items.append(
                match.group(1).strip()
            )

        elif len(line) > 5 and line[0].isupper():

            if len(line) < 200:
                items.append(line)

        i += 1

    return items, i


# ─────────────────────────────────────────────────────────────
# UNIT PARSER
# ─────────────────────────────────────────────────────────────

def _parse_units(text: str) -> list[dict]:
    """
    Parse UNIT blocks from a subject text block.

    Returns:

        [
            {
                "unit_number": 1,
                "unit_title": "...",
                "topics": [...]
            }
        ]
    """

    units = []

    unit_matches = list(
        RE_UNIT_HEADER.finditer(text)
    )

    for idx, match in enumerate(unit_matches):

        unit_roman = match.group(1)

        unit_title_suffix = (
            match.group(2) or ""
        ).strip().rstrip(":-–")

        unit_num = _roman_to_int(
            unit_roman
        )

        # Text between this UNIT and next UNIT
        start = match.end()

        if idx + 1 < len(unit_matches):
            end = unit_matches[idx + 1].start()
        else:
            end = len(text)

        unit_body = text[start:end]

        if unit_title_suffix:
            unit_title = unit_title_suffix
        else:
            unit_title = f"Unit {unit_num}"

        topics = []

        for line in unit_body.split("\n"):

            line = line.strip()

            if not line or len(line) < 3:
                continue

            list_match = RE_LIST_ITEM.match(line)

            if list_match:

                topics.append(
                    list_match.group(1).strip()
                )

            elif (
                line[0].isupper()
                and len(line) < 150
                and not RE_UNIT_HEADER.match(line)
                and not RE_OBJECTIVES.search(line)
                and not RE_OUTCOMES.search(line)
            ):

                topics.append(line)

        if topics:

            units.append(
                {
                    "unit_number": unit_num,
                    "unit_title": unit_title,
                    "topics": topics[:30],
                }
            )

    return units


# ─────────────────────────────────────────────────────────────
# SUBJECT NAME EXTRACTION
# ─────────────────────────────────────────────────────────────

def _extract_subject_name(
    block: str,
    code_match,
    subject_code: str,
) -> str:
    """
    Extract the subject name after the subject code.

    Handles names split across multiple PDF lines.

    Example:

        IT23402 Computer Organization
        and Architecture

    becomes:

        Computer Organization and Architecture
    """

    # ---------------------------------------------------------
    # First try explicit label:
    #
    # Subject Name: Database Management Systems
    # ---------------------------------------------------------

    name_match = RE_SUBJECT_NAME.search(block)

    if name_match:

        return (
            name_match.group(1)
            .strip()
            .title()
        )

    # ---------------------------------------------------------
    # Otherwise look after the subject code.
    # ---------------------------------------------------------

    remaining_text = block[
        code_match.end():
    ]

    name_lines = []

    for line in remaining_text.split("\n")[:8]:

        line = line.strip()

        if not line:
            continue

        # Stop if another subject code appears
        if RE_SUBJECT_CODE.search(line):
            break

        # Ignore table/header labels
        if line.lower() in {
            "course code",
            "course title",
            "subject code",
            "subject name",
            "credits",
            "credit",
            "l",
            "t",
            "p",
            "ltp",
        }:
            continue

        # Ignore lines containing only numbers
        if line.isdigit():
            continue

        # Ignore very long paragraphs
        if len(line) > 120:
            continue

        name_lines.append(line)

        # Most subject names fit within 3 lines
        if len(name_lines) >= 3:
            break

    if name_lines:

        subject_name = " ".join(
            name_lines
        ).strip()

        # Remove accidental table values at the end
        subject_name = re.sub(
            r"\s+\d+\s*$",
            "",
            subject_name,
        )

        return subject_name

    return subject_code


# ─────────────────────────────────────────────────────────────
# SUBJECT BLOCK PARSER
# ─────────────────────────────────────────────────────────────

def parse_subject_block(
    block: str,
) -> Optional[dict]:
    """
    Parse a single subject block.

    Returns None if no subject code can be found.
    """

    lines = block.split("\n")

    # ---------------------------------------------------------
    # Subject code
    # ---------------------------------------------------------

    code_match = RE_SUBJECT_CODE.search(block)

    if not code_match:
        return None

    subject_code = (
        code_match.group(1)
        .replace(" ", "")
        .strip()
        .upper()
    )

    # ---------------------------------------------------------
    # Subject name
    # ---------------------------------------------------------

    subject_name = _extract_subject_name(
        block,
        code_match,
        subject_code,
    )

    # ---------------------------------------------------------
    # Credits
    # ---------------------------------------------------------

    credits = None

    credits_match = RE_CREDITS.search(block)

    if credits_match:

        credits = int(
            credits_match.group(1)
        )

    # ---------------------------------------------------------
    # L / T / P
    # ---------------------------------------------------------

    lecture = None
    tutorial = None
    practical = None

    ltp_match = RE_LTP.search(block)

    if ltp_match:

        lecture = int(
            ltp_match.group(1)
        )

        tutorial = int(
            ltp_match.group(2)
        )

        practical = int(
            ltp_match.group(3)
        )

    # ---------------------------------------------------------
    # Semester
    # ---------------------------------------------------------

    semester = None

    sem_match = RE_SEMESTER.search(block)

    if sem_match:

        semester = (
            sem_match.group(1)
            .upper()
        )

    # ---------------------------------------------------------
    # Course type
    # ---------------------------------------------------------

    course_type = None

    ct_match = RE_COURSE_TYPE.search(block)

    if ct_match:

        course_type = (
            ct_match.group(1)
            .strip()
        )

    # ---------------------------------------------------------
    # Course objectives
    # ---------------------------------------------------------

    objectives = []

    obj_match = RE_OBJECTIVES.search(block)

    if obj_match:

        obj_lines = (
            block[obj_match.end():]
            .split("\n")
        )

        for line in obj_lines[:20]:

            line = line.strip()

            if not line:
                continue

            list_match = RE_LIST_ITEM.match(
                line
            )

            if list_match:

                objectives.append(
                    list_match.group(1).strip()
                )

            elif (
                len(line) > 10
                and line[0].isupper()
            ):

                objectives.append(line)

            if len(objectives) >= 10:
                break

    # ---------------------------------------------------------
    # Course outcomes
    # ---------------------------------------------------------

    outcomes = []

    out_match = RE_OUTCOMES.search(block)

    if out_match:

        out_lines = (
            block[out_match.end():]
            .split("\n")
        )

        for line in out_lines[:25]:

            line = line.strip()

            if not line:
                continue

            co_match = RE_CO_LINE.match(
                line
            )

            if co_match:

                outcomes.append(
                    {
                        "code": co_match.group(1).strip(),
                        "description": co_match.group(2).strip(),
                    }
                )

            if len(outcomes) >= 10:
                break

    # ---------------------------------------------------------
    # Units and topics
    # ---------------------------------------------------------

    units = _parse_units(block)

    # ---------------------------------------------------------
    # Return structured subject
    # ---------------------------------------------------------

    return {
        "subject_code": subject_code,
        "subject_name": subject_name,
        "semester": semester,
        "credits": credits,
        "lecture_hours": lecture,
        "tutorial_hours": tutorial,
        "practical_hours": practical,
        "course_type": course_type,
        "course_objectives": objectives,
        "course_outcomes": outcomes,
        "units": units,
    }


# ─────────────────────────────────────────────────────────────
# MAIN PDF PROCESSOR
# ─────────────────────────────────────────────────────────────

async def process_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Main entry point: parse a PDF and return a list of subject dicts.

    If the same subject code appears multiple times in the PDF,
    prefer the occurrence containing detailed syllabus units/topics.
    """

    logger.info("Starting PDF processing")

    pages = extract_pdf_text_pages(pdf_bytes)
    full_text = "\n".join(p["text"] for p in pages)

    logger.info(f"Extracted text from {len(pages)} PDF pages")

    blocks = _split_into_subject_blocks(full_text)
    logger.info(f"Found {len(blocks)} subject blocks")

    # Store the best version of each subject.
    subject_map = {}

    for block in blocks:
        try:
            result = parse_subject_block(block)

            if not result:
                continue

            code = result["subject_code"]

            # How much useful syllabus information does this block contain?
            score = 0

            if result.get("units"):
                score += 100

            if result.get("course_objectives"):
                score += 20

            if result.get("course_outcomes"):
                score += 20

            if result.get("credits") is not None:
                score += 5

            if result.get("lecture_hours") is not None:
                score += 5

            # Keep the block with the most detailed information.
            if code not in subject_map:
                subject_map[code] = (score, result)
            elif score > subject_map[code][0]:
                subject_map[code] = (score, result)

        except Exception as e:
            logger.warning(f"Failed to parse subject block: {e}")

    subjects = []

    for code, (_, subject) in subject_map.items():
        subjects.append(subject)

    logger.info(f"Parsed {len(subjects)} subjects from PDF")

    for subject in subjects:
        logger.info(
            f"Detected subject: "
            f"{subject['subject_code']} - "
            f"{subject['subject_name']} - "
            f"{len(subject['units'])} units"
        )

    return subjects