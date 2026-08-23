"""Email message parser."""

import email
import logging
from dataclasses import dataclass, field
from email.message import Message
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AttachmentInfo:
    """Information about an email attachment."""

    filename: str
    content_type: str
    size: int
    payload: bytes = field(default_factory=bytes)

    @property
    def size_formatted(self) -> str:
        """Return human-readable size."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"


@dataclass
class ParsedEmail:
    """Parsed email message."""

    from_: str
    to: str
    subject: str
    date: str
    body_plain: str
    body_html: str
    attachments: list[AttachmentInfo]
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def body(self) -> str:
        """Get the best available body content."""
        if self.body_plain:
            return self.body_plain
        return self.body_html


class HTMLToTextParser(HTMLParser):
    """Simple HTML to text converter."""

    def __init__(self):
        super().__init__()
        self._text_parts: list[str] = []
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style"):
            if tag.lower() == "script":
                self._in_script = True
            if tag.lower() == "style":
                self._in_style = True

        if tag.lower() in ("br", "p", "div"):
            self._text_parts.append("\n")
        elif tag.lower() in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._text_parts.append("\n\n")
        elif tag.lower() == "li":
            self._text_parts.append("\n• ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._in_script = False
        elif tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if not self._in_script and not self._in_style:
            self._text_parts.append(data)

    def get_text(self) -> str:
        """Get converted text."""
        text = "".join(self._text_parts)
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)


class EmailParser:
    """Parses raw email messages."""

    @staticmethod
    def parse(raw_message: bytes) -> ParsedEmail:
        """Parse a raw email message.

        Args:
            raw_message: Raw email bytes.

        Returns:
            ParsedEmail object.
        """
        msg = email.message_from_bytes(raw_message)

        # Extract headers
        from_ = EmailParser._decode_header(msg.get("From", ""))
        to = EmailParser._decode_header(msg.get("To", ""))
        subject = EmailParser._decode_header(msg.get("Subject", ""))
        date = EmailParser._decode_header(msg.get("Date", ""))

        # Extract body and attachments
        body_plain = ""
        body_html = ""
        attachments: list[AttachmentInfo] = []

        if msg.is_multipart():
            body_plain, body_html, attachments = EmailParser._parse_multipart(msg)
        else:
            body_plain, body_html = EmailParser._parse_single_part(msg)

        # Collect all headers
        headers = {}
        for key, value in msg.items():
            headers[key] = EmailParser._decode_header(value)

        return ParsedEmail(
            from_=from_,
            to=to,
            subject=subject,
            date=date,
            body_plain=body_plain,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
        )

    @staticmethod
    def _parse_multipart(
        msg: Message,
    ) -> tuple[str, str, list[AttachmentInfo]]:
        """Parse multipart message.

        Args:
            msg: Email message object.

        Returns:
            Tuple of (plain_body, html_body, attachments).
        """
        body_plain = ""
        body_html = ""
        attachments: list[AttachmentInfo] = []

        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = part.get_content_disposition()
            filename = part.get_filename()

            # Check if it's an attachment
            is_attachment = (
                content_disposition == "attachment"
                or (content_disposition == "inline" and filename)
                or content_type.startswith("application/")
            )

            if is_attachment and filename:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append(
                            AttachmentInfo(
                                filename=filename,
                                content_type=content_type,
                                size=len(payload),
                                payload=payload,
                            )
                        )
                except Exception as e:
                    logger.warning(f"Failed to extract attachment: {e}")

            elif content_type == "text/plain" and not is_attachment:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_plain += payload.decode(charset, errors="replace")
                except Exception as e:
                    logger.warning(f"Failed to decode text/plain part: {e}")

            elif content_type == "text/html" and not is_attachment:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html += payload.decode(charset, errors="replace")
                except Exception as e:
                    logger.warning(f"Failed to decode text/html part: {e}")

        return body_plain, body_html, attachments

    @staticmethod
    def _parse_single_part(msg: Message) -> tuple[str, str]:
        """Parse single-part message.

        Args:
            msg: Email message object.

        Returns:
            Tuple of (plain_body, html_body).
        """
        content_type = msg.get_content_type()
        body_plain = ""
        body_html = ""

        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")

                if content_type == "text/html":
                    body_html = decoded
                else:
                    body_plain = decoded
        except Exception as e:
            logger.warning(f"Failed to decode single part message: {e}")

        return body_plain, body_html

    @staticmethod
    def _decode_header(header: Any) -> str:
        """Decode email header with encoding support.

        Args:
            header: Header value.

        Returns:
            Decoded string.
        """
        if header is None:
            return ""

        if isinstance(header, bytes):
            try:
                return header.decode("utf-8", errors="replace")
            except Exception:
                return header.decode("latin-1", errors="replace")

        # Handle encoded words
        decoded_parts = email.header.decode_header(header)
        result_parts = []

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    enc = encoding or "utf-8"
                    result_parts.append(part.decode(enc, errors="replace"))
                except Exception:
                    result_parts.append(part.decode("latin-1", errors="replace"))
            else:
                result_parts.append(str(part))

        return "".join(result_parts)

    @staticmethod
    def html_to_text(html: str) -> str:
        """Convert HTML to plain text.

        Args:
            html: HTML content.

        Returns:
            Plain text content.
        """
        if not html:
            return ""

        parser = HTMLToTextParser()
        try:
            parser.feed(html)
            return parser.get_text()
        except Exception as e:
            logger.warning(f"Failed to convert HTML to text: {e}")
            # Fallback: strip basic tags
            import re

            text = re.sub(r"<[^>]+>", "", html)
            return text.strip()
