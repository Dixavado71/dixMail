"""Message management for IMAP."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MessageSummary:
    """Summary information about an email message."""

    id: int
    uid: str | None
    date: datetime | None
    date_str: str
    from_: str
    to: str
    subject: str
    is_seen: bool
    has_attachments: bool
    attachment_count: int

    @property
    def status(self) -> str:
        """Return human-readable status."""
        return "LIDO" if self.is_seen else "NOVO"


class MessageManager:
    """Manages email messages."""

    def __init__(self, imap_client):
        """Initialize message manager.

        Args:
            imap_client: IMAPClient instance.
        """
        self.client = imap_client

    def get_message_summaries(
        self, limit: int = 50, offset: int = 0
    ) -> list[MessageSummary]:
        """Get summaries of messages in current folder.

        Args:
            limit: Maximum number of messages to retrieve.
            offset: Number of messages to skip.

        Returns:
            List of MessageSummary objects.
        """
        if not self.client.is_connected:
            raise ConnectionError("Not connected to IMAP server")

        try:
            # Search for all messages
            typ, data = self.client._connection.search(None, "ALL")
            if typ != "OK":
                return []

            message_ids = data[0].split()
            if not message_ids:
                return []

            # Apply offset and limit (reverse order for newest first)
            message_ids = list(reversed(message_ids))
            if offset:
                message_ids = message_ids[offset:]
            if limit:
                message_ids = message_ids[:limit]

            summaries = []
            for msg_id_bytes in message_ids:
                msg_id = int(msg_id_bytes)
                summary = self._get_message_summary(msg_id)
                if summary:
                    summaries.append(summary)

            return summaries

        except Exception as e:
            logger.error(f"Error getting message summaries: {e}")
            return []

    def _get_message_summary(self, message_id: int) -> MessageSummary | None:
        """Get summary for a single message.

        Args:
            message_id: Message sequence number.

        Returns:
            MessageSummary or None if failed.
        """
        try:
            # Fetch envelope data
            typ, data = self.client._connection.fetch(
                str(message_id), "(ENVELOPE FLAGS BODYSTRUCTURE)"
            )

            if typ != "OK" or not data:
                return None

            # Parse flags
            flags = b""
            has_attachments = False
            attachment_count = 0

            for item in data:
                if isinstance(item, bytes):
                    if b"FLAGS" in item:
                        # Extract flags
                        start = item.find(b"FLAGS")
                        if start != -1:
                            end = item.find(b")", start)
                            if end != -1:
                                flags = item[start:end + 1]

                elif isinstance(item, tuple):
                    for subitem in item:
                        if isinstance(subitem, bytes):
                            if b"BODYSTRUCTURE" in subitem:
                                # Simple attachment detection
                                has_attachments, attachment_count = self._parse_body_structure(
                                    subitem
                                )

            is_seen = b"\\Seen" in flags

            # Parse envelope
            envelope = None
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    # Look for envelope data
                    env_data = item[1] if isinstance(item[1], tuple) else None
                    if env_data:
                        envelope = env_data
                        break

            if not envelope:
                # Fallback: fetch just envelope
                typ, env_data = self.client._connection.fetch(
                    str(message_id), "(ENVELOPE)"
                )
                if typ == "OK" and env_data:
                    for item in env_data:
                        if isinstance(item, tuple):
                            envelope = item
                            break

            # Extract envelope fields
            date_str = ""
            from_str = ""
            to_str = ""
            subject = ""
            date = None

            if envelope and len(envelope) >= 7:
                # ENVELOPE structure: (date subject from sender reply-to to cc bcc in-reply-to message-id)
                date_str = self._decode_header(envelope[0]) if envelope[0] else ""
                subject = self._decode_header(envelope[1]) if envelope[1] else ""

                # Parse from addresses
                if envelope[2]:
                    from_str = self._parse_addresses(envelope[2])

                # Parse to addresses
                if envelope[3]:
                    to_str = self._parse_addresses(envelope[3])

                # Parse date
                if date_str:
                    try:
                        date = self._parse_date(date_str)
                    except Exception:
                        pass

            # Get UID
            uid = self.client.get_uid(message_id)

            # Format date for display
            display_date = ""
            if date:
                display_date = date.strftime("%d/%m/%Y")
            elif date_str:
                display_date = date_str[:10] if len(date_str) >= 10 else date_str

            return MessageSummary(
                id=message_id,
                uid=uid,
                date=date,
                date_str=display_date,
                from_=from_str,
                to=to_str,
                subject=subject,
                is_seen=is_seen,
                has_attachments=has_attachments,
                attachment_count=attachment_count,
            )

        except Exception as e:
            logger.warning(f"Error parsing message {message_id}: {e}")
            return None

    def _parse_body_structure(
        self, body_structure: bytes
    ) -> tuple[bool, int]:
        """Parse body structure to detect attachments.

        Args:
            body_structure: Raw body structure data.

        Returns:
            Tuple of (has_attachments, count).
        """
        has_attachments = False
        count = 0

        try:
            data_str = body_structure.decode("utf-8", errors="ignore").upper()

            # Count occurrences of disposition types indicating attachments
            if b"ATTACHMENT" in body_structure or b"INLINE" in body_structure:
                # Simple heuristic: count FILENAME parameters
                count = data_str.count(b'FILENAME')
                if count > 0:
                    has_attachments = True

            # Also check for common attachment indicators
            if b'"APPLICATION/' in body_structure:
                has_attachments = True
                if count == 0:
                    count = 1

        except Exception:
            pass

        return has_attachments, max(1, count) if has_attachments else 0

    def _decode_header(self, header: Any) -> str:
        """Decode email header.

        Args:
            header: Header value (bytes or string).

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

        if isinstance(header, tuple):
            # Encoded word format
            try:
                charset, encoding, text = header
                if isinstance(text, bytes):
                    return text.decode(charset or "utf-8", errors="replace")
                return str(text)
            except Exception:
                return str(header)

        return str(header)

    def _parse_addresses(self, addresses: list) -> str:
        """Parse address list.

        Args:
            addresses: List of address tuples.

        Returns:
            Formatted address string.
        """
        if not addresses:
            return ""

        parts = []
        for addr in addresses:
            if isinstance(addr, tuple) and len(addr) >= 4:
                # (name, mailbox name, host name, personal name)
                name = self._decode_header(addr[3]) if addr[3] else ""
                mailbox = self._decode_header(addr[1]) if addr[1] else ""
                host = self._decode_header(addr[2]) if addr[2] else ""

                if name:
                    parts.append(name)
                elif mailbox and host:
                    parts.append(f"{mailbox}@{host}")
                elif mailbox:
                    parts.append(mailbox)

        return ", ".join(parts) if parts else ""

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse email date string.

        Args:
            date_str: Date string from email.

        Returns:
            datetime object or None.
        """
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S",
            "%a, %d %b %y %H:%M:%S %z",
        ]

        # Clean up the date string
        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try basic parsing
        try:
            parts = date_str.split()
            if len(parts) >= 3:
                day = int(parts[0].rstrip(","))
                month_str = parts[1]
                year = int(parts[2])

                months = {
                    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                    "may": 5, "jun": 6, "jul": 7, "aug": 8,
                    "sep": 9, "oct": 10, "nov": 11, "dec": 12
                }

                month = months.get(month_str.lower()[:3], 1)

                # Handle 2-digit years
                if year < 100:
                    year += 2000 if year < 50 else 1900

                return datetime(year, month, day)
        except Exception:
            pass

        return None

    def get_message_count(self) -> int:
        """Get total message count in current folder.

        Returns:
            Message count.
        """
        if not self.client.is_connected:
            return 0

        try:
            typ, data = self.client._connection.search(None, "ALL")
            if typ == "OK" and data[0]:
                return len(data[0].split())
        except Exception as e:
            logger.warning(f"Error getting message count: {e}")

        return 0
