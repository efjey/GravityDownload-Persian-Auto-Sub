import logging
import re
from pathlib import Path


logger = logging.getLogger(
    "gravitydownload"
)


# ============================================================
# Unicode BiDi Characters
# ============================================================

# Left-to-Right Mark
LRM = "\u200e"

# Right-to-Left Mark
RLM = "\u200f"


# ============================================================
# Timestamp
# ============================================================

def format_timestamp(
    seconds
):
    """
    Convert seconds to SRT timestamp.

    Example:
        65.123
        ->
        00:01:05,123
    """

    if seconds is None:
        seconds = 0

    seconds = max(
        0,
        float(seconds)
    )

    total_milliseconds = int(
        round(
            seconds * 1000
        )
    )

    hours = (
        total_milliseconds
        // 3_600_000
    )

    remainder = (
        total_milliseconds
        % 3_600_000
    )

    minutes = (
        remainder
        // 60_000
    )

    remainder %= 60_000

    secs = (
        remainder
        // 1000
    )

    milliseconds = (
        remainder
        % 1000
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


# ============================================================
# BiDi Protection
# ============================================================

# Unicode Bidirectional Isolation characters.
# LRI/PDI isolate English words, model names and numbers from
# surrounding Persian text without changing the actual text.
LRI = "\u2066"
PDI = "\u2069"
RLM = "\u200f"

# Directional controls that may have been inserted by older
# versions of the application.
_DIRECTIONAL_CONTROLS = str.maketrans("", "", "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def protect_rtl_text(text):
    """
    Make mixed Persian/English subtitle lines render correctly.

    The text itself is not translated or reordered. LTR runs such as
    "DaVinci Resolve", "RTX 4060", "Windows 11", "Python 3" and
    "4K" are isolated with Unicode LRI/PDI controls. An RLM at the
    start of an RTL line gives players a strong RTL paragraph cue.

    This is preferable to wrapping the whole line with RLM, which can
    cause punctuation and embedded English words to visually jump.
    """
    if not text:
        return ""

    text = str(text).translate(_DIRECTIONAL_CONTROLS)

    return "\n".join(
        _protect_rtl_line(line)
        for line in text.split("\n")
    )


def _protect_rtl_line(line):
    if not line:
        return line

    if not _contains_rtl(line):
        return line

    # Match Latin/numeric runs, including common technical notation.
    # A whole English phrase is kept together instead of isolating each
    # word independently, which improves punctuation and readability.
    pattern = re.compile(
        r"""
        (?<![A-Za-z0-9])
        (?:
            [A-Za-z0-9]
            [A-Za-z0-9_.+\-/#:@%]*
        )
        (?:
            \s+
            [A-Za-z0-9]
            [A-Za-z0-9_.+\-/#:@%]*
        ){0,12}
        (?![A-Za-z0-9])
        """,
        re.VERBOSE,
    )

    result = []
    last_end = 0
    found_ltr = False

    for match in pattern.finditer(line):
        value = match.group(0)

        if not value.strip():
            continue

        found_ltr = True
        result.append(line[last_end:match.start()])
        result.append(LRI)
        result.append(value)
        result.append(PDI)
        last_end = match.end()

    result.append(line[last_end:])
    final_text = "".join(result)

    # Only add a paragraph-direction hint at the beginning. Do not put
    # RLM at both ends because trailing punctuation can then jump sides.
    if found_ltr:
        return RLM + final_text

    return RLM + final_text


def _contains_rtl(text):
    return bool(re.search(r"[\u0590-\u08FF]", text))


# ============================================================
# SRT Writer
# ============================================================

def write_srt(
    segments,
    output_path,
    protect_rtl=True,
):
    """
    Write subtitle segments to an SRT file.

    UTF-8 BOM is used for better Windows/media-player
    compatibility.
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    logger.info(
        f"در حال ساخت فایل SRT: "
        f"{output_path.name}"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8-sig",
        newline="\n",
    ) as file:

        for position, segment in enumerate(
            segments,
            start=1
        ):

            index = segment.get(
                "index",
                position
            )

            start = segment.get(
                "start",
                0
            )

            end = segment.get(
                "end",
                0
            )

            text = (
                segment.get(
                    "translated_text"
                )
                or
                segment.get(
                    "text",
                    ""
                )
            )

            text = str(
                text
            ).strip()

            if protect_rtl:

                text = protect_rtl_text(
                    text
                )

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{format_timestamp(start)} "
                f"--> "
                f"{format_timestamp(end)}\n"
            )

            file.write(
                f"{text}\n"
            )

            file.write(
                "\n"
            )

    logger.info(
        f"فایل SRT ساخته شد: "
        f"{output_path}"
    )

    return output_path