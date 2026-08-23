"""IMAP client for Gmail connections."""

import imaplib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class IMAPClient:
    """Manages IMAP connection to Gmail."""

    def __init__(self, email: str, password: str, server: str = "imap.gmail.com", port: int = 993):
        """Initialize IMAP client.

        Args:
            email: Gmail email address.
            password: Gmail app password.
            server: IMAP server hostname.
            port: IMAP server port.
        """
        self.email = email
        self.password = password
        self.server = server
        self.port = port
        self._connection: imaplib.IMAP4_SSL | None = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to IMAP server."""
        return self._connection is not None

    def connect(self) -> bool:
        """Establish connection to IMAP server.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            logger.info(f"Connecting to {self.server}:{self.port}")
            self._connection = imaplib.IMAP4_SSL(self.server, self.port)
            self._connection.login(self.email, self.password)
            logger.info("Successfully connected and authenticated")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection error: {e}")
            self._connection = None
            return False
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            self._connection = None
            return False

    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self._connection:
            try:
                self._connection.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connection = None

    def reconnect(self) -> bool:
        """Reconnect to IMAP server.

        Returns:
            True if reconnection successful, False otherwise.
        """
        self.disconnect()
        return self.connect()

    def _ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if needed.

        Returns:
            True if connection is active, False otherwise.
        """
        if not self.is_connected:
            return self.connect()

        # Test connection with noop
        try:
            self._connection.noop()
            return True
        except Exception:
            logger.warning("Connection lost, attempting reconnect")
            return self.reconnect()

    def select_folder(self, folder: str = "INBOX", readonly: bool = False) -> tuple[str, list[bytes]]:
        """Select a folder/mailbox.

        Args:
            folder: Folder name to select.
            readonly: If True, select in read-only mode.

        Returns:
            Tuple of (response_type, data).
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            # Encode folder name for IMAP
            encoded_folder = folder.encode("utf-8")
            if readonly:
                return self._connection.select(encoded_folder, readonly=True)
            else:
                return self._connection.select(encoded_folder)
        except imaplib.IMAP4.error as e:
            raise ConnectionError(f"Failed to select folder '{folder}': {e}")

    def search(self, criteria: str) -> list[int]:
        """Search for messages matching criteria.

        Args:
            criteria: IMAP search criteria (e.g., 'UNSEEN', 'FROM example@gmail.com').

        Returns:
            List of message IDs.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            typ, data = self._connection.search(None, criteria)
            if typ != "OK":
                return []

            message_ids = data[0].split()
            return [int(msg_id) for msg_id in message_ids]
        except imaplib.IMAP4.error as e:
            logger.error(f"Search error: {e}")
            return []

    def fetch(self, message_ids: list[int], parts: str = "(RFC822.HEADER)") -> dict[int, bytes]:
        """Fetch message data.

        Args:
            message_ids: List of message IDs to fetch.
            parts: Parts to fetch (default: headers only).

        Returns:
            Dictionary mapping message ID to raw message data.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        results = {}
        for msg_id in message_ids:
            try:
                typ, data = self._connection.fetch(str(msg_id), parts)
                if typ == "OK" and data:
                    # Find the actual message data in the response
                    for item in data:
                        if isinstance(item, tuple) and len(item) >= 2:
                            results[msg_id] = item[1]
                            break
                        elif isinstance(item, bytes):
                            results[msg_id] = item
                            break
            except imaplib.IMAP4.error as e:
                logger.warning(f"Failed to fetch message {msg_id}: {e}")

        return results

    def fetch_full(self, message_id: int) -> bytes | None:
        """Fetch complete message including body.

        Args:
            message_id: Message ID to fetch.

        Returns:
            Raw message data or None if failed.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            typ, data = self._connection.fetch(str(message_id), "(RFC822)")
            if typ == "OK" and data:
                for item in data:
                    if isinstance(item, tuple) and len(item) >= 2:
                        return item[1]
                    elif isinstance(item, bytes):
                        return item
        except imaplib.IMAP4.error as e:
            logger.error(f"Failed to fetch full message {message_id}: {e}")

        return None

    def delete(self, message_ids: list[int]) -> bool:
        """Mark messages for deletion.

        Args:
            message_ids: List of message IDs to delete.

        Returns:
            True if all deletions successful, False otherwise.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        success = True
        for msg_id in message_ids:
            try:
                typ, _ = self._connection.store(str(msg_id), "+FLAGS", "\\Deleted")
                if typ != "OK":
                    success = False
                    logger.warning(f"Failed to mark message {msg_id} for deletion")
            except imaplib.IMAP4.error as e:
                logger.error(f"Delete error for message {msg_id}: {e}")
                success = False

        return success

    def expunge(self) -> bool:
        """Permanently remove messages marked for deletion.

        Returns:
            True if expunge successful, False otherwise.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            typ, _ = self._connection.expunge()
            return typ == "OK"
        except imaplib.IMAP4.error as e:
            logger.error(f"Expunge error: {e}")
            return False

    def move(self, message_ids: list[int], destination_folder: str) -> bool:
        """Move messages to another folder.

        Args:
            message_ids: List of message IDs to move.
            destination_folder: Target folder name.

        Returns:
            True if move successful, False otherwise.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            # Gmail uses COPY + DELETE for moving
            encoded_dest = destination_folder.encode("utf-8")

            for msg_id in message_ids:
                typ, _ = self._connection.copy(str(msg_id), encoded_dest)
                if typ != "OK":
                    logger.warning(f"Failed to copy message {msg_id} to {destination_folder}")
                    return False

            # Mark originals for deletion
            return self.delete(message_ids)

        except imaplib.IMAP4.error as e:
            logger.error(f"Move error: {e}")
            return False

    def mark_read(self, message_ids: list[int]) -> bool:
        """Mark messages as read.

        Args:
            message_ids: List of message IDs to mark as read.

        Returns:
            True if all marked successfully, False otherwise.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        success = True
        for msg_id in message_ids:
            try:
                typ, _ = self._connection.store(
                    str(msg_id), "-FLAGS", "\\Seen"
                )
                if typ != "OK":
                    success = False
            except imaplib.IMAP4.error as e:
                logger.error(f"Mark read error for message {msg_id}: {e}")
                success = False

        return success

    def mark_unread(self, message_ids: list[int]) -> bool:
        """Mark messages as unread.

        Args:
            message_ids: List of message IDs to mark as unread.

        Returns:
            True if all marked successfully, False otherwise.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        success = True
        for msg_id in message_ids:
            try:
                typ, _ = self._connection.store(
                    str(msg_id), "+FLAGS", "\\Seen"
                )
                if typ != "OK":
                    success = False
            except imaplib.IMAP4.error as e:
                logger.error(f"Mark unread error for message {msg_id}: {e}")
                success = False

        return success

    def get_uid(self, message_id: int) -> str | None:
        """Get UID for a message.

        Args:
            message_id: Message sequence number.

        Returns:
            UID string or None if not found.
        """
        if not self._ensure_connected():
            raise ConnectionError("Not connected to IMAP server")

        try:
            typ, data = self._connection.fetch(
                str(message_id), "(UID)"
            )
            if typ == "OK" and data:
                # Parse UID from response like b'1 (UID 12345)'
                response = data[0]
                if isinstance(response, bytes):
                    response = response.decode("utf-8")
                # Extract UID
                if "UID" in response:
                    parts = response.split("UID")
                    if len(parts) > 1:
                        uid = parts[1].strip().rstrip(")").strip()
                        return uid
        except Exception as e:
            logger.warning(f"Failed to get UID for message {message_id}: {e}")

        return None
