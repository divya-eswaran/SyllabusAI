"""
PDF Service — extracts structured syllabus data from university PDF files.

Strategy:
1. Use PyMuPDF to extract raw text page by page.
2. Apply rule-based heuristics to detect:
   - Subject codes
   - Subject names
   - Credits
   - L/T/P/C
   - Course type
   - Semester
   - Units and topics
   - Practicals
   - Suggested activities
   - Suggested evaluation methods
   - Course objectives and outcomes
3. Return a list of SubjectData dictionaries ready for DB insertion.
"""

import re
import logging
from typing import Optional

import fitz  # PyMuPDF


logger = logging.getLogger(__name__)


# ============================================================
# REGEX PATTERNS
# ============================================================

# Subject codes:
# IT501
# CS301
# IT23C01
# IT23401
# EN23C01
RE_SUBJECT_CODE = re.compile(
    r"\b([A-Z]{2,5}\d{2,3}[A-Z]?\d{2,3})\b",
    re.IGNORECASE,
)


# Explicit subject/course name
RE_SUBJECT_NAME = re.compile(
    r"(?:subject\s+name|course\s+name|course\s+title)"
    r"\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


# Credits
RE_CREDITS = re.compile(
    r"credits?\s*[:\-]\s*(\d+)",
    re.IGNORECASE,
)


# L/T/P format:
# L/T/P: 3/0/2
RE_LTP = re.compile(
    r"L\s*/\s*T\s*/\s*P\s*[:\-]\s*"
    r"(\d+)\s*/\s*(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)


# L/T/P/C table format:
#
# L T P C
# 3 0 2 4
#
RE_LTPC_TABLE = re.compile(
    r"\bL\s+T\s+P\s+C\b"
    r"[\s\n]+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
    re.IGNORECASE,
)


# Semester
RE_SEMESTER = re.compile(
    r"semester\s*[:\-]\s*"
    r"(I{1,3}V?|VI{0,3}|[1-8])\b",
    re.IGNORECASE,
)


# Course type
RE_COURSE_TYPE = re.compile(
    r"(?:course\s+type|category)\s*[:\-]\s*(.+)",
    re.IGNORECASE,
)


# Unit headers:
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


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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


def _clean_topic_text(text: str) -> str:
    """
    Clean topic text: remove leading numbering, collapse multiple whitespaces,
    and strip edge punctuation (colons, semicolons, hyphens, dashes).
    """
    text = text.strip()
    # Remove leading numbering (e.g., "1.", "1)", "1.1", "1 - ")
    text = re.sub(r"^\s*\d+(?:\.\d+)*\s*[\.\):\-]\s*", "", text)
    # Normalize internal spaces / linebreaks
    text = re.sub(r"\s+", " ", text)
    # Strip edge punctuation and dashes
    return text.strip(" \t\n\r:;–—−-‒―")


def _unique_items(items: list[str]) -> list[str]:
    """Remove duplicate items while preserving order."""

    result = []
    seen = set()

    for item in items:
        item = item.strip()

        if not item:
            continue

        key = item.lower()

        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

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


# ============================================================
# SUBJECT BLOCK SPLITTING
# ============================================================

def _split_into_subject_blocks(full_text: str) -> list[str]:
    """
    Split the PDF text into subject blocks using subject codes.

    Supports:

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


# ============================================================
# UNIT PARSER
# ============================================================

def _parse_units(text: str) -> list[dict]:
    """
    Parse UNIT blocks and keep syllabus sections separate.

    Strategy for topics:
      - Bullet/numbered list items  → each item is one topic.
      - Ordinary lines              → collected into blocks per section,
                                      joined with a space (reuniting wrapped lines),
                                      then split on hyphens and dashes:
                                        – / — / − / ― or " - " / " -" / "- "
                                      so that multi-line entries like:
                                        "Overview of Java – OOPS Fundamentals
                                         in Java: Classes, Objects, Methods and Strings–Array and\\n
                                         Array Lists"
                                      correctly become 3 separate topics:
                                        1. "Overview of Java"
                                        2. "OOPS Fundamentals in Java: Classes, Objects, Methods and Strings"
                                        3. "Array and Array Lists"
    """
    units = []
    unit_matches = list(RE_UNIT_HEADER.finditer(text))

    for idx, match in enumerate(unit_matches):
        unit_roman = match.group(1)
        unit_title_suffix = (match.group(2) or "").strip().rstrip(":-\u2012\u2013\u2014\u2015\u2212")
        unit_num = _roman_to_int(unit_roman)

        # Get text belonging to this unit
        start = match.end()
        end = unit_matches[idx + 1].start() if idx + 1 < len(unit_matches) else len(text)
        unit_body = text[start:end]

        # Unit title
        unit_title = (
            _clean_topic_text(unit_title_suffix)
            if unit_title_suffix
            else f"Unit {unit_num}"
        )

        SECTIONS = (
            "topics",
            "practicals",
            "suggested_activities",
            "suggested_evaluation_methods",
        )
        section_list = {s: [] for s in SECTIONS}
        section_block = {s: [] for s in SECTIONS}

        current_section = "topics"
        _SKIP = {"l", "t", "p", "c", "ltp", "ltpc", "syllabus", "contents"}
        lines = unit_body.split("\n")
        i = 0

        while i < len(lines):
            raw_line = lines[i]
            line = raw_line.strip()
            i += 1

            if not line:
                continue

            # Detect section headers
            normalized = re.sub(r"[\s:.\-]+$", "", line.lower()).strip()

            if normalized in {"practicals", "practical", "practical work", "practical component"}:
                current_section = "practicals"
                continue

            if normalized in {"suggested activities", "suggested activity", "activities"}:
                current_section = "suggested_activities"
                continue

            if normalized in {
                "suggested evaluation methods", "suggested evaluation method",
                "evaluation methods", "evaluation method",
            }:
                current_section = "suggested_evaluation_methods"
                continue

            # Skip unrelated headers
            if re.match(r"^(course objectives?|course outcomes?)", line, re.IGNORECASE):
                continue

            # Skip garbage tokens
            if line.lower() in _SKIP:
                continue

            if len(line) < 3 or len(line) >= 200:
                continue

            if RE_UNIT_HEADER.match(line) or RE_OBJECTIVES.search(line) or RE_OUTCOMES.search(line):
                continue

            # Bullet / numbered list item → already one topic
            list_match = RE_LIST_ITEM.match(raw_line)
            if list_match:
                item = _clean_topic_text(list_match.group(1).strip())
                if item and len(item) >= 3:
                    section_list[current_section].append(item)
                continue

            # Ordinary line → collect for later hyphen-splitting
            section_block[current_section].append(line)

        # Process each section: join block lines → split on hyphens/dashes
        def _process_section(sec: str) -> list[str]:
            items = list(section_list[sec])
            block_lines = section_block[sec]
            if block_lines:
                # Join lines to reunite wrapped topics
                combined = " ".join(block_lines)
                # Split on:
                # 1. Any Unicode dash: en-dash (– \u2013), em-dash (— \u2014), minus sign (− \u2212),
                #    horizontal bar (― \u2015), figure dash (‒ \u2012)
                # 2. ASCII hyphen '-' with whitespace on at least one side (e.g. " - ", " -", "- ")
                #    to avoid breaking intra-word hyphens like 'Object-Oriented' or 'Built-in'
                parts = re.split(
                    r"\s*[\u2012\u2013\u2014\u2015\u2212]\s*|\s+-\s*|\s*-\s+",
                    combined,
                )
                for part in parts:
                    item = _clean_topic_text(part)
                    if item and len(item) >= 3:
                        items.append(item)
            return items

        topics = _unique_items(_process_section("topics"))
        practicals = _unique_items(_process_section("practicals"))
        suggested_activities = _unique_items(_process_section("suggested_activities"))
        suggested_evaluation_methods = _unique_items(_process_section("suggested_evaluation_methods"))

        if topics or practicals or suggested_activities or suggested_evaluation_methods:
            units.append(
                {
                    "unit_number": unit_num,
                    "unit_title": unit_title,
                    "topics": topics,
                    "practicals": practicals,
                    "suggested_activities": suggested_activities,
                    "suggested_evaluation_methods": suggested_evaluation_methods,
                }
            )

    return units


# ============================================================
# SUBJECT NAME EXTRACTION
# ============================================================

def _extract_subject_name(
    block: str,
    code_match,
    subject_code: str,
) -> str:
    """
    Extract the subject name after the subject code.
    """

    # --------------------------------------------------------
    # First try explicit label
    # --------------------------------------------------------

    name_match = RE_SUBJECT_NAME.search(block)

    if name_match:

        return (
            name_match.group(1)
            .strip()
            .title()
        )

    # --------------------------------------------------------
    # Otherwise look after subject code
    # --------------------------------------------------------

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
            "c",
            "ltp",
            "ltpc",
        }:
            continue

        # Ignore lines containing only numbers
        if line.isdigit():
            continue

        # Ignore very long paragraphs
        if len(line) > 120:
            continue

        name_lines.append(line)

        if len(name_lines) >= 3:
            break

    if name_lines:

        subject_name = " ".join(
            name_lines
        ).strip()

        # Remove accidental number at end
        subject_name = re.sub(
            r"\s+\d+\s*$",
            "",
            subject_name,
        )

        return subject_name

    return subject_code


# ============================================================
# SUBJECT BLOCK PARSER
# ============================================================

def parse_subject_block(
    block: str,
) -> Optional[dict]:
    """
    Parse a single subject block.

    Returns None if no subject code can be found.
    """

    # --------------------------------------------------------
    # Subject code
    # --------------------------------------------------------

    code_match = RE_SUBJECT_CODE.search(block)

    if not code_match:
        return None

    subject_code = (
        code_match.group(1)
        .replace(" ", "")
        .strip()
        .upper()
    )

    # --------------------------------------------------------
    # Subject name
    # --------------------------------------------------------

    subject_name = _extract_subject_name(
        block,
        code_match,
        subject_code,
    )

    # --------------------------------------------------------
    # Credits
    # --------------------------------------------------------

    credits = None

    credits_match = RE_CREDITS.search(block)

    if credits_match:

        credits = int(
            credits_match.group(1)
        )

    # --------------------------------------------------------
    # L / T / P / C
    # --------------------------------------------------------

    lecture = None
    tutorial = None
    practical = None
    ltp_credits = None

    # Format:
    #
    # L/T/P: 3/0/2
    #

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

    else:

        # Format:
        #
        # L T P C
        # 3 0 2 4
        #

        ltpc_match = RE_LTPC_TABLE.search(block)

        if ltpc_match:

            lecture = int(
                ltpc_match.group(1)
            )

            tutorial = int(
                ltpc_match.group(2)
            )

            practical = int(
                ltpc_match.group(3)
            )

            ltp_credits = int(
                ltpc_match.group(4)
            )

    # If C was present in L/T/P/C table,
    # use it as credits.
    if ltp_credits is not None:
        credits = ltp_credits

    # --------------------------------------------------------
    # Semester
    # --------------------------------------------------------

    semester = None

    sem_match = RE_SEMESTER.search(block)

    if sem_match:

        semester = (
            sem_match.group(1)
            .upper()
        )

    # --------------------------------------------------------
    # Course type
    # --------------------------------------------------------

    course_type = None

    ct_match = RE_COURSE_TYPE.search(block)

    if ct_match:

        course_type = (
            ct_match.group(1)
            .strip()
        )

    # --------------------------------------------------------
    # Course objectives
    # --------------------------------------------------------

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

            list_match = RE_LIST_ITEM.match(line)

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

    # --------------------------------------------------------
    # Course outcomes
    # --------------------------------------------------------

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

            co_match = RE_CO_LINE.match(line)

            if co_match:

                outcomes.append(
                    {
                        "code":
                            co_match.group(1).strip(),

                        "description":
                            co_match.group(2).strip(),
                    }
                )

            if len(outcomes) >= 10:
                break

    # --------------------------------------------------------
    # Units
    # --------------------------------------------------------

    units = _parse_units(block)

    # --------------------------------------------------------
    # Return structured subject
    # --------------------------------------------------------

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


# ============================================================
# MAIN PDF PROCESSOR
# ============================================================

async def process_pdf(
    pdf_bytes: bytes,
) -> list[dict]:
    """
    Main entry point.

    Parse PDF and return a list of subject dictionaries.

    If the same subject code appears multiple times,
    prefer the occurrence containing more detailed syllabus
    information.
    """

    logger.info(
        "Starting PDF processing"
    )

    pages = extract_pdf_text_pages(
        pdf_bytes
    )

    full_text = "\n".join(
        p["text"]
        for p in pages
    )

    logger.info(
        f"Extracted text from "
        f"{len(pages)} PDF pages"
    )

    blocks = _split_into_subject_blocks(
        full_text
    )

    logger.info(
        f"Found {len(blocks)} subject blocks"
    )

    # Store the best version of each subject.
    subject_map = {}

    for block in blocks:

        try:

            result = parse_subject_block(
                block
            )

            if not result:
                continue

            code = result["subject_code"]

            # ------------------------------------------------
            # Calculate usefulness score
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Keep most detailed block
            # ------------------------------------------------

            if code not in subject_map:

                subject_map[code] = (
                    score,
                    result,
                )

            elif score > subject_map[code][0]:

                subject_map[code] = (
                    score,
                    result,
                )

        except Exception as e:

            logger.warning(
                f"Failed to parse subject block: {e}"
            )

    # --------------------------------------------------------
    # Build final list
    # --------------------------------------------------------

    subjects = []

    for code, (_, subject) in subject_map.items():

        subjects.append(subject)

    logger.info(
        f"Parsed {len(subjects)} subjects from PDF"
    )

    # --------------------------------------------------------
    # Debug information
    # --------------------------------------------------------

    for subject in subjects:

        logger.info(
            f"Detected subject: "
            f"{subject['subject_code']} - "
            f"{subject['subject_name']} - "
            f"{len(subject['units'])} units"
        )

    return subjects