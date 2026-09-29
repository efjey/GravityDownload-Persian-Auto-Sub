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

def protect_rtl_text(
    text
):
    """
    Improve display of Persian/Arabic text containing
    English words, numbers and technical terms.

    Example:

        در DaVinci Resolve کار می‌کنیم

    gets Unicode directional markers around LTR runs
    so media players are less likely to reorder them.
    """

    if not text:
        return ""

    text = str(
        text
    )

    # --------------------------------------------------------
    # Normalize invisible direction characters first
    # --------------------------------------------------------

    text = text.replace(
        "\u200e",
        ""
    )

    text = text.replace(
        "\u200f",
        ""
    )

    text = text.replace(
        "\u202a",
        ""
    )

    text = text.replace(
        "\u202b",
        ""
    )

    text = text.replace(
        "\u202c",
        ""
    )

    text = text.replace(
        "\u202d",
        ""
    )

    text = text.replace(
        "\u202e",
        ""
    )

    # --------------------------------------------------------
    # Process each line separately
    # --------------------------------------------------------

    lines = text.split(
        "\n"
    )

    processed_lines = []

    for line in lines:

        processed_lines.append(
            _protect_rtl_line(
                line
            )
        )

    return "\n".join(
        processed_lines
    )


def _protect_rtl_line(
    line
):
    """
    Protect LTR sequences inside RTL Persian text.
    """

    if not line:
        return line

    # --------------------------------------------------------
    # Detect Latin / numeric runs.
    #
    # Examples:
    #   DaVinci
    #   Resolve
    #   RTX 4060
    #   Python
    #   v19.2
    #   4K
    #   MP4
    # --------------------------------------------------------

    pattern = re.compile(
        r"""
        (?:
            [A-Za-z]
            [A-Za-z0-9_.+\-/#:@]*

            (?:
                \s+
                [A-Za-z0-9_.+\-/#:@]+
            )*
        )
        """,
        re.VERBOSE,
    )

    result = []

    last_end = 0

    for match in pattern.finditer(
        line
    ):

        start = match.start()
        end = match.end()

        # ----------------------------------------------------
        # Avoid wrapping ordinary numbers that are already
        # inside a Persian word structure.
        # ----------------------------------------------------

        value = match.group(
            0
        )

        # Skip if empty
        if not value:
            continue

        # ----------------------------------------------------
        # Text before LTR segment
        # ----------------------------------------------------

        result.append(
            line[
                last_end:start
            ]
        )

        # ----------------------------------------------------
        # Add LTR markers
        # ----------------------------------------------------

        result.append(
            LRM
        )

        result.append(
            value
        )

        result.append(
            LRM
        )

        last_end = end

    result.append(
        line[
            last_end:
        ]
    )

    final_text = "".join(
        result
    )

    # --------------------------------------------------------
    # Add RLM around complete RTL subtitle line.
    #
    # This helps some players determine that the subtitle
    # should primarily be rendered RTL.
    # --------------------------------------------------------

    if _contains_rtl(final_text):

        final_text = (
            RLM
            + final_text
            + RLM
        )

    return final_text


def _contains_rtl(
    text
):
    """
    Check whether text contains Persian/Arabic RTL
    characters.
    """

    return bool(
        re.search(
            r"[\u0590-\u08FF]",
            text
        )
    )


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