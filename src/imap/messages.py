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
            # Fetch ENVELOPE and FLAGS in a single request
            typ, data = self.client._connection.fetch(
                str(message_id), "(ENVELOPE FLAGS)"
            )
            
            is_seen = False
            envelope_tuple = None
            
            if typ == "OK" and data and len(data) > 0:
                # Response format: b'ID (FLAGS (...) ENVELOPE (...))'
                response = data[0]
                
                if isinstance(response, bytes):
                    response_str = response.decode("utf-8", errors="replace")
                    
                    # Check for \\Seen flag
                    if "\\Seen" in response_str:
                        is_seen = True
                    
                    # Extract ENVELOPE content using string parsing
                    env_start = response_str.find("ENVELOPE (")
                    if env_start != -1:
                        # Find matching closing parenthesis
                        start_pos = env_start + len("ENVELOPE (")
                        depth = 1
                        end_pos = start_pos
                        while depth > 0 and end_pos < len(response_str):
                            if response_str[end_pos] == "(":
                                depth += 1
                            elif response_str[end_pos] == ")":
                                depth -= 1
                            end_pos += 1
                        
                        envelope_content = response_str[start_pos:end_pos-1]
                        
                        # Parse the envelope tuple from the string
                        # Format: \"date\" \"subject\" ((\"name\" NIL \"user\" \"host\")) ...
                        envelope_tuple = self._parse_envelope_string(envelope_content)

            # If we couldn't parse from combined fetch, try separate ENVELOPE fetch
            if envelope_tuple is None:
                typ, env_data = self.client._connection.fetch(str(message_id), "ENVELOPE")
                if typ == "OK" and env_data:
                    for item in env_data:
                        if isinstance(item, bytes):
                            item_str = item.decode("utf-8", errors="replace")
                            env_start = item_str.find("ENVELOPE (")
                            if env_start != -1:
                                start_pos = env_start + len("ENVELOPE (")
                                depth = 1
                                end_pos = start_pos
                                while depth > 0 and end_pos < len(item_str):
                                    if item_str[end_pos] == "(":
                                        depth += 1
                                    elif item_str[end_pos] == ")":
                                        depth -= 1
                                    end_pos += 1
                                envelope_content = item_str[start_pos:end_pos-1]
                                envelope_tuple = self._parse_envelope_string(envelope_content)
                                break
                        elif isinstance(item, tuple):
                            for subitem in item:
                                if isinstance(subitem, tuple) and len(subitem) >= 7:
                                    envelope_tuple = subitem
                                    break
            
            # Extract envelope fields
            date_str = ""
            from_str = ""
            to_str = ""
            subject = ""
            date = None

            if envelope_tuple and len(envelope_tuple) >= 7:
                # ENVELOPE structure: 
                # [0]=date, [1]=subject, [2]=from, [3]=to, [4]=cc, [5]=bcc, [6]=in_reply_to, [7]=message_id
                date_str = self._decode_header(envelope_tuple[0]) if envelope_tuple[0] else ""
                subject = self._decode_header(envelope_tuple[1]) if envelope_tuple[1] else ""

                # Parse from addresses
                if envelope_tuple[2]:
                    from_str = self._parse_addresses(envelope_tuple[2])

                # Parse to addresses
                if envelope_tuple[3]:
                    to_str = self._parse_addresses(envelope_tuple[3])

                # Parse date
                if date_str:
                    try:
                        date = self._parse_date(date_str)
                    except Exception as e:
                        logger.debug(f"Error parsing date '{date_str}': {e}")
                        pass

            # Get UID
            uid = self.client.get_uid(message_id)

            # Format date for display
            display_date = ""
            if date:
                display_date = date.strftime("%d/%m/%Y")
            elif date_str:
                display_date = date_str[:10] if len(date_str) >= 10 else date_str

            # Detect attachments by fetching body structure
            has_attachments = False
            attachment_count = 0
            typ, body_data = self.client._connection.fetch(
                str(message_id), "BODYSTRUCTURE"
            )
            if typ == "OK" and body_data:
                for item in body_data:
                    if isinstance(item, tuple):
                        for subitem in item:
                            if isinstance(subitem, bytes) and b"BODYSTRUCTURE" in subitem:
                                has_attachments, attachment_count = self._parse_body_structure(subitem)
                                break

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
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _parse_envelope_string(self, envelope_str: str) -> tuple | None:
        """Parse envelope string into a tuple.
        
        Args:
            envelope_str: String representation of envelope content.
            
        Returns:
            Tuple with envelope fields or None if parsing fails.
        """
        try:
            # This is a simplified parser for IMAP ENVELOPE format
            # Format: \"date\" \"subject\" ((\"name\" NIL \"user\" \"host\")) ...
            import re
            
            result = []
            pos = 0
            current_depth = 0
            current_token = ""
            in_string = False
            i = 0
            
            while i < len(envelope_str):
                char = envelope_str[i]
                
                if char == '"' and (i == 0 or envelope_str[i-1] != '\\\\'):
                    in_string = not in_string
                    current_token += char
                elif in_string:
                    current_token += char
                elif char == '(':
                    if current_depth == 0 and current_token.strip():
                        # Save any pending token
                        result.append(self._convert_token(current_token.strip()))
                        current_token = ""
                    current_depth += 1
                    if current_depth == 1:
                        # Start of a new list
                        current_token = "("
                    else:
                        current_token += char
                elif char == ')':
                    current_depth -= 1
                    if current_depth == 0:
                        # End of list
                        current_token += ")"
                        # Parse nested list
                        nested = self._parse_nested_list(current_token)
                        result.append(nested)
                        current_token = ""
                    else:
                        current_token += char
                elif char == ' ' and current_depth == 0:
                    if current_token.strip():
                        result.append(self._convert_token(current_token.strip()))
                        current_token = ""
                else:
                    current_token += char
                
                i += 1
            
            # Handle any remaining token
            if current_token.strip():
                result.append(self._convert_token(current_token.strip()))
            
            return tuple(result) if result else None
            
        except Exception as e:
            logger.debug(f"Error parsing envelope string: {e}")
            return None
    
    def _convert_token(self, token: str):
        """Convert a token to appropriate type."""
        if token.startswith('"') and token.endswith('"'):
            # Remove quotes and handle escaped characters
            return token[1:-1].replace('\\\\', '\\').replace('\\"', '"')
        elif token == "NIL":
            return None
        else:
            return token
    
    def _parse_nested_list(self, list_str: str) -> list:
        """Parse a nested list string like ((\"name\" NIL \"user\" \"host\"))."""
        if not list_str.startswith('(') or not list_str.endswith(')'):
            return list_str
        
        # Remove outer parentheses
        inner = list_str[1:-1].strip()
        
        if not inner:
            return []
        
        result = []
        current_token = ""
        depth = 0
        in_string = False
        
        for i, char in enumerate(inner):
            if char == '"' and (i == 0 or inner[i-1] != '\\\\'):
                in_string = not in_string
                current_token += char
            elif in_string:
                current_token += char
            elif char == '(':
                depth += 1
                current_token += char
            elif char == ')':
                depth -= 1
                current_token += char
            elif char == ' ' and depth == 0:
                if current_token.strip():
                    result.append(self._convert_token(current_token.strip()))
                    current_token = ""
            else:
                current_token += char
        
        if current_token.strip():
            result.append(self._convert_token(current_token.strip()))
        
        return result

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
            # Check for attachment dispositions more accurately
            # Look for disposition "attachment" specifically (not inline)
            attachment_parts = []
            
            # Parse the body structure to find parts with attachment disposition
            # BODYSTRUCTURE format is complex, we look for patterns like:
            # ("APPLICATION/PDF" NIL ("NAME" "file.pdf") NIL NIL "BASE64" 12345 NIL NIL NIL NIL)
            # followed by disposition info
            
            data_str = body_structure.decode("utf-8", errors="ignore")
            data_upper = data_str.upper()
            
            # Count FILENAME parameters that are in ATTACHMENT disposition
            # Pattern: NIL NIL NIL NIL ("ATTACHMENT" ("FILENAME" "name.ext"))
            # We need to be careful not to count inline images
            
            # Simple but effective approach: count FILENAME only if near ATTACHMENT
            lines_or_parts = data_str.split(')')
            for part in lines_or_parts:
                part_upper = part.upper()
                # Only count if this part has ATTACHMENT disposition
                if 'ATTACHMENT' in part_upper and 'FILENAME' in part_upper:
                    count += 1
            
            # Fallback: if we found ATTACHMENT but no FILENAME counted, estimate
            if count == 0 and b'ATTACHMENT' in body_structure:
                # At least one attachment exists
                count = 1
                
            has_attachments = count > 0

        except Exception as e:
            logger.warning(f"Error parsing body structure: {e}")
            pass

        return has_attachments, count

    def _decode_header(self, header) -> str:
        """Decode email header.

        Args:
            header: Header value (bytes, string, or encoded word format).

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

        # Handle encoded words in string format (=?UTF-8?Q?...?=)
        if isinstance(header, str):
            from email.header import decode_header as email_decode_header
            
            try:
                decoded_parts = email_decode_header(header)
                decoded = ""
                for part, encoding in decoded_parts:
                    if isinstance(part, bytes):
                        decoded += part.decode(encoding or "utf-8", errors="replace")
                    else:
                        decoded += str(part)
                return decoded
            except Exception:
                pass
            
            return header

        return str(header)

    def _parse_addresses(self, addresses) -> str:
        """Parse address list.

        Args:
            addresses: List of address tuples or string representation.

        Returns:
            Formatted address string.
        """
        if not addresses:
            return ""
        
        # Handle case where addresses is a list containing a single string like '("SHEIN" NIL "shein" "edm.shein.com")'
        if isinstance(addresses, list) and len(addresses) == 1 and isinstance(addresses[0], str):
            addr_str = addresses[0]
            # Parse the string format: ("name" NIL "user" "host")
            import re
            match = re.match(r'\(("([^"]*)"|NIL)\s+(NIL|"([^"]*)")\s+(NIL|"([^"]*)")\s+(NIL|"([^"]*)")\)', addr_str)
            if match:
                name = match.group(2) or ""
                mailbox = match.group(4) or ""
                host = match.group(6) or ""
                
                if name:
                    return name
                elif mailbox and host:
                    return f"{mailbox}@{host}"
                elif mailbox:
                    return mailbox
        
        if not isinstance(addresses, (list, tuple)):
            return str(addresses)

        parts = []
        for addr in addresses:
            if isinstance(addr, (list, tuple)) and len(addr) >= 4:
                # (name, mailbox name, host name, personal name)
                # IMAP envelope format: (personal name, mailbox name, host name, full name)
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
