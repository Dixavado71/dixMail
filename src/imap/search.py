"""Search functionality for IMAP."""

import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


class SearchManager:
    """Manages email search operations."""

    def __init__(self, imap_client):
        """Initialize search manager.

        Args:
            imap_client: IMAPClient instance.
        """
        self.client = imap_client

    def search(self, query: str) -> list[int]:
        """Search emails using IMAP search.

        Args:
            query: Search query (supports from:, subject:, to:, etc.).

        Returns:
            List of message IDs matching the query.
        """
        if not self.client.is_connected:
            raise ConnectionError("Not connected to IMAP server")

        # Parse query for special prefixes
        criteria = self._parse_query(query)

        try:
            return self.client.search(criteria)
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def _parse_query(self, query: str) -> str:
        """Parse user query into IMAP search criteria.

        Args:
            query: User's search query.

        Returns:
            IMAP search criteria string.
        """
        query = query.strip()

        # Check for special prefixes
        query_lower = query.lower()

        if query_lower.startswith("from:"):
            email = query[5:].strip()
            return f'FROM "{email}"'

        elif query_lower.startswith("to:"):
            email = query[3:].strip()
            return f'TO "{email}"'

        elif query_lower.startswith("subject:"):
            subject = query[8:].strip()
            return f'SUBJECT "{subject}"'

        elif query_lower.startswith("before:"):
            date_str = query[7:].strip()
            date_obj = self._parse_date(date_str)
            if date_obj:
                return f'BEFORE "{date_obj.strftime("%d-%b-%Y")}"'

        elif query_lower.startswith("after:"):
            date_str = query[6:].strip()
            date_obj = self._parse_date(date_str)
            if date_obj:
                return f'SINCE "{date_obj.strftime("%d-%b-%Y")}"'

        elif query_lower.startswith("on:"):
            date_str = query[3:].strip()
            date_obj = self._parse_date(date_str)
            if date_obj:
                return f'ON "{date_obj.strftime("%d-%b-%Y")}"'

        elif query_lower == "unread" or query_lower == "unseen":
            return "UNSEEN"

        elif query_lower == "read" or query_lower == "seen":
            return "SEEN"

        elif query_lower == "flagged" or query_lower == "starred":
            return "FLAGGED"

        elif query_lower == "answered":
            return "ANSWERED"

        # Default: search in subject and body
        return f'(SUBJECT "{query}" OR BODY "{query}")'

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string.

        Args:
            date_str: Date string in various formats.

        Returns:
            date object or None.
        """
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def search_by_sender(self, sender: str) -> list[int]:
        """Search by sender.

        Args:
            sender: Sender email or name.

        Returns:
            List of message IDs.
        """
        return self.search(f"from:{sender}")

    def search_by_subject(self, subject: str) -> list[int]:
        """Search by subject.

        Args:
            subject: Subject text.

        Returns:
            List of message IDs.
        """
        return self.search(f"subject:{subject}")

    def search_by_recipient(self, recipient: str) -> list[int]:
        """Search by recipient.

        Args:
            recipient: Recipient email.

        Returns:
            List of message IDs.
        """
        return self.search(f"to:{recipient}")

    def search_unread(self) -> list[int]:
        """Search for unread messages.

        Returns:
            List of message IDs.
        """
        return self.search("UNSEEN")

    def search_flagged(self) -> list[int]:
        """Search for flagged/starred messages.

        Returns:
            List of message IDs.
        """
        return self.search("FLAGGED")

    def search_since(self, since_date: date) -> list[int]:
        """Search messages since a date.

        Args:
            since_date: Start date.

        Returns:
            List of message IDs.
        """
        criteria = f'SINCE "{since_date.strftime("%d-%b-%Y")}"'
        try:
            return self.client.search(criteria)
        except Exception as e:
            logger.error(f"Date search error: {e}")
            return []

    def search_before(self, before_date: date) -> list[int]:
        """Search messages before a date.

        Args:
            before_date: End date.

        Returns:
            List of message IDs.
        """
        criteria = f'BEFORE "{before_date.strftime("%d-%b-%Y")}"'
        try:
            return self.client.search(criteria)
        except Exception as e:
            logger.error(f"Date search error: {e}")
            return []

    def combine_searches(
        self, searches: list[list[int]], operator: str = "AND"
    ) -> list[int]:
        """Combine multiple search results.

        Args:
            searches: List of search result lists.
            operator: "AND" for intersection, "OR" for union.

        Returns:
            Combined list of message IDs.
        """
        if not searches:
            return []

        if len(searches) == 1:
            return searches[0]

        if operator == "OR":
            # Union
            result = set()
            for search_result in searches:
                result.update(search_result)
            return sorted(result)
        else:
            # AND - intersection
            result = set(searches[0])
            for search_result in searches[1:]:
                result.intersection_update(search_result)
            return sorted(result)

