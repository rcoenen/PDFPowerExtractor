"""
Canonical Markdown formatter for PDFPowerExtractor.

Converts extracted form text to a standardized markdown format.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FieldType(Enum):
    TEXT = "text"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    ADDRESS = "address"
    SECTION = "section"


@dataclass
class FormField:
    """Represents a form field with its extracted data"""
    field_id: str  # e.g., "2.1", "3.4"
    label: str
    field_type: FieldType
    value: Optional[str] = None  # For text fields
    options: List[Tuple[bool, str]] = field(default_factory=list)  # For radio/checkbox: (selected, label)
    sub_fields: Dict[str, str] = field(default_factory=dict)  # For address: {sublabel: value}


@dataclass
class FormSection:
    """Represents a form section"""
    section_id: str  # e.g., "2"
    title: str
    description: str = ""
    fields: List[FormField] = field(default_factory=list)


class MarkdownFormatter:
    """
    Converts extracted text to canonical markdown format.

    Output format:
    ## 2. Section Title

    Section description paragraph.

    ### 2.1 Field Label
    value: `filled value`

    ### 2.7 Radio Question
    (type: radio)
    - (x) selected option
    - ( ) unselected option

    ### 5.2 Checkbox Group
    (type: checkbox)
    - [x] checked item
    - [ ] unchecked item
    """

    # Regex patterns for parsing
    SECTION_PATTERN = re.compile(r'^(\d+)\.\s*(.+)$')
    FIELD_PATTERN = re.compile(r'^(\d+\.\d+)\s+(.+)$')
    RADIO_SELECTED = re.compile(r'^[●◉]\s*(.+)$')
    RADIO_UNSELECTED = re.compile(r'^[○◯]\s*(.+)$')
    CHECKBOX_CHECKED = re.compile(r'^[☒☑✓✔]\s*(.+)$')
    CHECKBOX_UNCHECKED = re.compile(r'^[☐□]\s*(.+)$')
    VALUE_LINE = re.compile(r'^(.+?):\s*(.*)$')

    def __init__(self, use_unicode_symbols: bool = False):
        """
        Initialize formatter.

        Args:
            use_unicode_symbols: If True, use ●○☒☐. If False, use (x)( )[x][ ]
        """
        self.use_unicode = use_unicode_symbols

    def format_text_field(self, field: FormField) -> str:
        """Format a text field"""
        value = field.value or ""
        return f"### {field.field_id} {field.label}\nvalue: `{value}`"

    def format_radio_group(self, field: FormField) -> str:
        """Format a radio button group"""
        lines = [f"### {field.field_id} {field.label}", "(type: radio)"]

        for selected, option_label in field.options:
            if self.use_unicode:
                marker = "●" if selected else "○"
            else:
                marker = "(x)" if selected else "( )"
            lines.append(f"- {marker} {option_label}")

        return "\n".join(lines)

    def format_checkbox_group(self, field: FormField) -> str:
        """Format a checkbox group"""
        lines = [f"### {field.field_id} {field.label}", "(type: checkbox)"]

        for checked, option_label in field.options:
            if self.use_unicode:
                marker = "☒" if checked else "☐"
            else:
                marker = "[x]" if checked else "[ ]"
            lines.append(f"- {marker} {option_label}")

        return "\n".join(lines)

    def format_address_field(self, field: FormField) -> str:
        """Format an address/multi-line field"""
        lines = [f"### {field.field_id} {field.label}"]

        for sublabel, value in field.sub_fields.items():
            lines.append(f"{sublabel}: `{value}`")

        return "\n".join(lines)

    def format_section(self, section: FormSection) -> str:
        """Format a complete section"""
        lines = [f"## {section.section_id}. {section.title}"]

        if section.description:
            lines.append("")
            lines.append(section.description)

        lines.append("")

        for field in section.fields:
            if field.field_type == FieldType.TEXT:
                lines.append(self.format_text_field(field))
            elif field.field_type == FieldType.RADIO:
                lines.append(self.format_radio_group(field))
            elif field.field_type == FieldType.CHECKBOX:
                lines.append(self.format_checkbox_group(field))
            elif field.field_type == FieldType.ADDRESS:
                lines.append(self.format_address_field(field))
            lines.append("")

        return "\n".join(lines)

    def parse_extracted_text(self, text: str) -> List[FormSection]:
        """
        Parse extracted text into structured form data.

        This attempts to identify:
        - Section headers (e.g., "2. Uw gegevens")
        - Field labels (e.g., "2.1 BSN")
        - Radio/checkbox options (lines starting with ●○☒☐)
        - Values (text after field labels or in subsequent lines)
        """
        sections = []
        current_section = None
        current_field = None
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Check for section header
            section_match = self.SECTION_PATTERN.match(line)
            if section_match and not self.FIELD_PATTERN.match(line):
                if current_section:
                    if current_field:
                        current_section.fields.append(current_field)
                        current_field = None
                    sections.append(current_section)

                current_section = FormSection(
                    section_id=section_match.group(1),
                    title=section_match.group(2)
                )
                i += 1
                continue

            # Check for field header (e.g., "2.1 BSN")
            field_match = self.FIELD_PATTERN.match(line)
            if field_match:
                if current_field and current_section:
                    current_section.fields.append(current_field)

                current_field = FormField(
                    field_id=field_match.group(1),
                    label=field_match.group(2),
                    field_type=FieldType.TEXT
                )
                i += 1
                continue

            # Check for radio button option
            radio_sel = self.RADIO_SELECTED.match(line)
            radio_unsel = self.RADIO_UNSELECTED.match(line)
            if radio_sel or radio_unsel:
                if current_field:
                    current_field.field_type = FieldType.RADIO
                    if radio_sel:
                        current_field.options.append((True, radio_sel.group(1)))
                    else:
                        current_field.options.append((False, radio_unsel.group(1)))
                i += 1
                continue

            # Check for checkbox option
            check_sel = self.CHECKBOX_CHECKED.match(line)
            check_unsel = self.CHECKBOX_UNCHECKED.match(line)
            if check_sel or check_unsel:
                if current_field:
                    current_field.field_type = FieldType.CHECKBOX
                    if check_sel:
                        current_field.options.append((True, check_sel.group(1)))
                    else:
                        current_field.options.append((False, check_unsel.group(1)))
                i += 1
                continue

            # Check for value line (Label: Value)
            value_match = self.VALUE_LINE.match(line)
            if value_match and current_field:
                sublabel = value_match.group(1)
                value = value_match.group(2).strip()

                # If it looks like an address sub-field
                if any(kw in sublabel.lower() for kw in ['straat', 'postcode', 'plaats', 'land', 'street', 'city', 'country']):
                    current_field.field_type = FieldType.ADDRESS
                    current_field.sub_fields[sublabel] = value
                elif not current_field.value:
                    current_field.value = value

                i += 1
                continue

            # Regular text - might be a value for the current field
            if current_field and current_field.field_type == FieldType.TEXT and not current_field.value:
                # Check if this looks like a value (not another label)
                if not self.SECTION_PATTERN.match(line) and not self.FIELD_PATTERN.match(line):
                    current_field.value = line

            i += 1

        # Don't forget the last field and section
        if current_field and current_section:
            current_section.fields.append(current_field)
        if current_section:
            sections.append(current_section)

        return sections

    def convert_to_markdown(self, text: str) -> str:
        """
        Convert extracted text to canonical markdown format.

        Args:
            text: Raw extracted text with ●○☒☐ symbols

        Returns:
            Canonical markdown formatted string
        """
        sections = self.parse_extracted_text(text)

        output_lines = ["# Form Extraction Results", ""]

        for section in sections:
            output_lines.append(self.format_section(section))

        return "\n".join(output_lines)

    def convert_symbols_to_markdown(self, text: str) -> str:
        """
        Simple conversion: replace unicode symbols with markdown-style markers.

        This is a lighter-weight conversion that doesn't parse structure,
        just replaces symbols:
        - ● → (x)
        - ○ → ( )
        - ☒/☑ → [x]
        - ☐ → [ ]
        """
        result = text

        # Radio buttons
        result = re.sub(r'^([●◉])\s+', '(x) ', result, flags=re.MULTILINE)
        result = re.sub(r'^([○◯])\s+', '( ) ', result, flags=re.MULTILINE)

        # Checkboxes
        result = re.sub(r'^([☒☑✓✔])\s+', '[x] ', result, flags=re.MULTILINE)
        result = re.sub(r'^([☐□])\s+', '[ ] ', result, flags=re.MULTILINE)

        return result


def format_as_canonical_markdown(text: str, use_unicode: bool = False) -> str:
    """
    Convenience function to convert extracted text to canonical markdown.

    Args:
        text: Raw extracted text
        use_unicode: Use unicode symbols (●○) or ASCII markers ((x)( ))

    Returns:
        Formatted markdown string
    """
    formatter = MarkdownFormatter(use_unicode_symbols=use_unicode)
    return formatter.convert_to_markdown(text)


def convert_symbols_only(text: str) -> str:
    """
    Quick conversion of just the radio/checkbox symbols to ASCII.

    Args:
        text: Text with unicode radio/checkbox symbols

    Returns:
        Text with ASCII markers
    """
    formatter = MarkdownFormatter()
    return formatter.convert_symbols_to_markdown(text)
