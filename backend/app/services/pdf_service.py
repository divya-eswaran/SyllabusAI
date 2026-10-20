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
# IT501, CS301, IT23C01, IT23401, EN23C01
RE_SUBJECT_CODE = re.compile(
    r"\b([A-Z]{2,5}\d{2,3}[A-Z]?\d{2,3})\b",
    re.IGNORECASE,
)

# Common hardware chips, protocols, standards, or false-positive codes to ignore as subjects
EXCLUDED_SUBJECT_CODES = {
    "ESP8266", "ESP32", "CDMA2000", "ISO14000", "ISO9001", "ISO9000",
    "IEEE802", "IPV6", "IPV4", "SHA256", "AES128", "AES256", "AES192",
    "RS232", "RS485", "STM32", "ARM7", "ARM9", "ARM11", "WCDMA", "HSDPA",
    "HSUPA", "GSM900", "DCS1800", "HTML5", "CSS3", "MP3", "MPEG4", "H264",
    "TCP4", "TCP6", "UDP4", "UDP6", "USB2", "USB3", "PCI3", "SATA3",
}

# Unit end markers: syllabus text following Unit 5 (textbooks, references, etc.)
RE_UNIT_END_MARKERS = re.compile(
    r"^(?:TOTAL\s*[:\-–]?\s*\d+\s*(?:PERIODS|HOURS)?|TEXT\s*BOOKS?|REFERENCES?|ONLINE\s*REFERENCES?|WEB\s*REFERENCES?|COURSE\s*OUTCOMES?|CO\s*[-–]\s*PO|PO\s*MAPPING|TEACHING\s*METHODOLOGY|LABORATORY\s*EXERCISES?|SUGGESTED\s*EVALUATION\s*METHODS?|CONTINUOUS\s*ASSESSMENT)",
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

# Regulation
RE_REGULATION = re.compile(
    r"(?:regulations?|reg\.?|r)\s*[-–:]?\s*(20\d{2}|19\d{2})",
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
    Clean topic text: remove leading numbering or hours (e.g. '9+3 ', '1.', '1)'),
    collapse multiple whitespaces, and strip edge punctuation.
    """
    text = text.strip()
    # Strip leading unit hours like "9+3 " or "12 "
    text = re.sub(r"^\s*\d+(?:\s*[\+\-]\s*\d+)?\s+", "", text)
    # Remove leading numbering (e.g., "1.", "1)", "1.1", "1 - ")
    text = re.sub(r"^\s*\d+(?:\.\d+)*\s*[\.\):\-]\s*", "", text)
    # Normalize internal spaces / linebreaks
    text = re.sub(r"\s+", " ", text)
    # Strip edge punctuation and dashes
    return text.strip(" \t\n\r:;–—−-‒―.,")


def _is_valid_topic(text: str) -> bool:
    """
    Check if an extracted string is a valid syllabus topic,
    filtering out textbooks, URLs, matrices, period totals, etc.
    """
    if not text or len(text) < 3 or len(text) > 300:
        return False
    lower = text.lower()
    # Check for unit end / noise markers
    if re.search(
        r"\b(?:total\s*:\s*\d+\s*(?:periods|hours)?|text\s*books?|references?|po1\s+po2|co1\s+co2|course\s+outcomes?|course\s+objectives?)\b",
        lower,
    ):
        return False
    # Check for websites/URLs
    if re.search(
        r"^(?:www\.|https?://|[a-z0-9\-]+\.(?:com|org|edu|in|gov|net))\b",
        lower,
    ):
        return False
    # Check for publisher citations
    if re.search(
        r"\b(?:orient\s*blackswan|cambridge\s*university|red\s*globe\s*press|cengage\s*learning|mcgraw\s*hill|prentice\s*hall|springer|pearson|oxford\s*university)\b",
        lower,
    ):
        return False
    # Check if text is just numbers or punctuation
    if re.match(r"^[\d\s\W]+$", text):
        return False
    return True


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
    Filters out hardware acronyms and false-positive codes.
    """

    raw_matches = list(RE_SUBJECT_CODE.finditer(full_text))

    # Filter out hardware, protocols, or excluded codes
    matches = []
    for m in raw_matches:
        code = m.group(1).upper()
        if code in EXCLUDED_SUBJECT_CODES:
            continue
        if re.match(r"^(?:ESP|ISO|CDMA|IEEE|IPV|SHA|AES|RS\d|STM\d|ARM\d|WCDMA|HSDPA|HSUPA)", code):
            continue
        matches.append(m)

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

            # Stop parsing unit if trailing text (textbooks, references, totals, etc.) begins
            if RE_UNIT_END_MARKERS.search(line):
                break

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

            # Bullet / numbered list item → clean and save
            list_match = RE_LIST_ITEM.match(raw_line)
            if list_match:
                item = _clean_topic_text(list_match.group(1).strip())
                if _is_valid_topic(item):
                    section_list[current_section].append(item)
                continue

            # Ordinary line → collect for later hyphen-splitting
            section_block[current_section].append(line)

        # Process each section: join block lines → split on hyphens/dashes
        def _process_section(sec: str) -> list[str]:
            items = []
            for item in section_list[sec]:
                if _is_valid_topic(item):
                    items.append(item)
            block_lines = section_block[sec]
            if block_lines:
                # Join lines to reunite wrapped topics
                combined = " ".join(block_lines)
                # Strip leading unit hours like "9+3 " or "12 "
                combined = re.sub(r"^\s*\d+(?:\s*[\+\-]\s*\d+)?\s+", "", combined)
                # Split on hyphens / dashes:
                # Any hyphen or dash between words forms separate topics
                parts = re.split(
                    r"\s*[\u2012\u2013\u2014\u2015\u2212]\s*|\s*-\s*",
                    combined,
                )
                for part in parts:
                    item = _clean_topic_text(part)
                    if _is_valid_topic(item):
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
        subject_name = " ".join(name_lines).strip()
        subject_name = re.sub(r"\s+\d+\s*$", "", subject_name)
        return clean_subject_name(subject_name)

    return subject_code


# ============================================================
# SUBJECT CODE / SEMESTER / REGULATION MAPPING
# ============================================================

KNOWN_SEMESTER_MAP = {
    # Semester 1
    "EN23C01": ("1", "Foundational Course"),
    "MA23C01": ("1", "Basic Science Course"),
    "PH23C01": ("1", "Basic Science Course"),
    "ME23C01": ("1", "Engineering Science Course"),
    "EE23C02": ("1", "Engineering Science Course"),
    "ME23C04": ("1", "Engineering Science Course"),
    "UC23H01": ("1", "Humanities and Social Sciences"),

    # Semester 2
    "EN23C02": ("2", "Foundational Course"),
    "MA23C03": ("2", "Basic Science Course"),
    "PH23C08": ("2", "Basic Science Course"),
    "CY23C01": ("2", "Basic Science Course"),
    "CS23C04": ("2", "Engineering Science Course"),
    "IT23201": ("2", "Professional Core"),
    "UC23H02": ("2", "Humanities and Social Sciences"),

    # Semester 3
    "MA23C09": ("3", "Basic Science Course"),
    "IT23301": ("3", "Professional Core"),
    "IT23302": ("3", "Professional Core"),
    "IT23303": ("3", "Professional Core"),
    "IT23304": ("3", "Professional Core"),
    "IT23U01": ("3", "Professional Core"),
    "UC23U01": ("3", "Humanities and Social Sciences"),
    "CS301":   ("3", "Professional Core"),

    # Semester 4
    "MA23C05": ("4", "Basic Science Course"),
    "IT23401": ("4", "Professional Core"),
    "IT23C01": ("4", "Professional Core"),
    "IT23402": ("4", "Professional Core"),
    "IT23403": ("4", "Professional Core"),
    "IT23C02": ("4", "Professional Core"),
    "IT23L01": ("4", "Value Added / Self-Learning"),

    # Semester 5
    "IT23501": ("5", "Professional Core"),
    "IT23502": ("5", "Professional Core"),
    "IT23503": ("5", "Professional Core"),
    "IT23504": ("5", "Professional Core"),
    "UC23E01": ("5", "Engineering Science Course"),
    "IT23505": ("5", "Employability Enhancement"),
    "IT23D01": ("5", "Capstone Project"),

    # Semester 6
    "IT23601": ("6", "Professional Core"),
    "IT23602": ("6", "Professional Core"),
    "IT23U02": ("6", "Humanities and Social Sciences"),
    "IT23D02": ("6", "Capstone Project"),

    # Semester 7
    "IT23701": ("7", "Professional Core"),
    "IT23702": ("7", "Professional Core"),
    "IT23D03": ("7", "Capstone Project"),

    # Semester 8
    "IT23801": ("8", "Project Work"),

    # NCC Credit courses
    "UC23P01": ("Elective", "Value Added"),
    "UC23P02": ("Elective", "Value Added"),
    "UC23P03": ("Elective", "Value Added"),
}


def clean_subject_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'\(Common to all branches[^\)]*\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b(COURSE\s+OBJECTIVES?|OBJECTIVES?)\b.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bUNIT\s+[I|V|X\d]+.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bL\s*T\s*P\s*C[\s\d]*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bL\s*T\s*P[\s\d]*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bT\s*P\s*C[\s\d]*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bL\s*T[\s\d]*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bP\s*C[\s\d]*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\bOEC\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[\s:.\-–—]+$', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name.title()


def infer_subject_metadata(subject_code: str, existing_semester: Optional[str] = None):
    code = subject_code.strip().upper()
    reg_match = re.match(r'^[A-Z]{2,4}(\d{2})', code)
    regulation = f"Regulation 20{reg_match.group(1)}" if reg_match else "Regulation 2023"

    if code in KNOWN_SEMESTER_MAP:
        sem, ctype = KNOWN_SEMESTER_MAP[code]
        return sem, regulation, ctype

    m = re.match(r'^[A-Z]{2,4}\d{2}([1-8])\d{2}$', code)
    if m:
        return m.group(1), regulation, "Professional Core"

    if re.match(r'^[A-Z]{2,4}\d{2}0\d{2}$', code) or code.startswith("IT23C") or code.startswith("IT23E"):
        return "Elective", regulation, "Professional Elective"

    if re.match(r'^[A-Z]{2,4}\d{2}9\d{2}$', code):
        return "Elective", regulation, "Open Elective"

    if existing_semester:
        return str(existing_semester), regulation, "Core"

    return "Elective", regulation, "Elective"


# ============================================================
# CURRICULUM SEMESTER MAPPER (FOR 4-YEAR SYLLABUS PDFS)
# ============================================================

def _extract_curriculum_semester_map(full_text: str) -> dict[str, str]:
    """
    In a 4-year curriculum document, tables under 'SEMESTER I' through 'SEMESTER VIII'
    list all subjects for each semester. This function scans those tables and maps
    each subject code to its semester ('1' through '8').
    """
    code_to_sem = {}
    sem_matches = list(re.finditer(r"\b(?:SEMESTER|SEM)\s*[-\u2013:]?\s*(I{1,3}V?|VI{0,3}|[1-8])\b", full_text, re.IGNORECASE))

    for idx, match in enumerate(sem_matches):
        sem_str = match.group(1).upper()
        sem_num = str(_roman_to_int(sem_str))
        start = match.end()
        end = sem_matches[idx + 1].start() if idx + 1 < len(sem_matches) else min(start + 5000, len(full_text))
        chunk = full_text[start:end]

        for code_match in RE_SUBJECT_CODE.finditer(chunk):
            code = code_match.group(1).upper()
            if code not in EXCLUDED_SUBJECT_CODES and not re.match(r"^(?:ESP|ISO|CDMA|IEEE|IPV|SHA|AES|RS\d|STM\d|ARM\d)", code):
                if code not in code_to_sem:
                    code_to_sem[code] = sem_num

    return code_to_sem


# ============================================================
# SUBJECT BLOCK PARSER
# ============================================================

def parse_subject_block(
    block: str,
    default_regulation: Optional[str] = None,
    semester_map: Optional[dict] = None,
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

    if subject_code in EXCLUDED_SUBJECT_CODES or re.match(r"^(?:ESP|ISO|CDMA|IEEE|IPV|SHA|AES|RS\d|STM\d|ARM\d)", subject_code):
        return None

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

    if semester_map and subject_code in semester_map:
        semester = semester_map[subject_code]
    else:
        sem_match = RE_SEMESTER.search(block)
        if sem_match:
            semester = str(_roman_to_int(sem_match.group(1)))
        else:
            # Infer semester from subject code:
            # e.g. IT23601 -> 6, IT23401 -> 4
            code_sem = re.search(r"^[A-Za-z]{2,4}\d{2}([1-8])\d{2}$", subject_code)
            if code_sem:
                semester = code_sem.group(1)
            else:
                code_sem2 = re.search(r"^[A-Za-z]{2}\d([1-8])\d{2}$", subject_code)
                if code_sem2:
                    semester = code_sem2.group(1)

    # --------------------------------------------------------
    # Regulation
    # --------------------------------------------------------

    regulation = None
    reg_match = RE_REGULATION.search(block)

    if reg_match:
        regulation = f"Regulation {reg_match.group(1)}"
    elif default_regulation:
        regulation = default_regulation if "Regulation" in default_regulation else f"Regulation {default_regulation}"
    else:
        # Infer from subject code (e.g. IT23... -> Regulation 2023)
        yr_m = re.search(r"^[A-Za-z]{2,4}(\d{2})", subject_code)
        if yr_m:
            regulation = f"Regulation 20{yr_m.group(1)}"
        else:
            regulation = "Regulation 2021"

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

    inferred_sem, regulation, inferred_type = infer_subject_metadata(subject_code, semester)
    if not semester:
        semester = inferred_sem
    if not course_type:
        course_type = inferred_type

    return {
        "subject_code": subject_code,
        "subject_name": subject_name,
        "regulation": regulation,
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

    # Detect document-level regulation if available
    doc_reg = RE_REGULATION.search(full_text)
    default_regulation = f"Regulation {doc_reg.group(1)}" if doc_reg else None

    # Pre-scan 4-year curriculum semester tables (SEMESTER I to VIII)
    semester_map = _extract_curriculum_semester_map(full_text)
    logger.info(f"Mapped {len(semester_map)} subjects to semesters from curriculum structure")

    # Store the best version of each subject.
    subject_map = {}

    for block in blocks:

        try:

            result = parse_subject_block(
                block,
                default_regulation=default_regulation,
                semester_map=semester_map,
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
    # Build final list (filter out irrelevant subjects with 0 units or 0 topics)
    # --------------------------------------------------------

    subjects = []

    for code, (_, subject) in subject_map.items():
        unit_count = len(subject.get("units", []))
        total_topics = sum(len(u.get("topics", [])) for u in subject.get("units", []))
        if unit_count > 0 and total_topics > 0:
            subjects.append(subject)

    logger.info(
        f"Parsed {len(subjects)} valid subjects with syllabus content from PDF"
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