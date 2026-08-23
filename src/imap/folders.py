"""Folder management for IMAP."""

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class FolderInfo(NamedTuple):
    """Information about a folder/mailbox."""

    name: str
    delimiter: str
    attributes: tuple[str, ...]
    is_selectable: bool


class FolderManager:
    """Manages IMAP folders/mailboxes."""

    def __init__(self, imap_client):
        """Initialize folder manager.

        Args:
            imap_client: IMAPClient instance.
        """
        self.client = imap_client

    def list_folders(self) -> list[FolderInfo]:
        """List all available folders.

        Returns:
            List of FolderInfo objects.
        """
        if not self.client.is_connected:
            raise ConnectionError("Not connected to IMAP server")

        try:
            typ, data = self.client._connection.list()
            if typ != "OK":
                return []

            folders = []
            for item in data:
                if isinstance(item, bytes):
                    item = item.decode("utf-8")

                # Parse folder response: (attributes) delimiter "name"
                # Example: (\HasNoChildren) "/" "INBOX"
                parts = item.split(' "')
                if len(parts) >= 2:
                    # Extract attributes
                    attr_part = parts[0].strip().lstrip("(").rstrip(")")
                    attributes = tuple(attr_part.split()) if attr_part else ()

                    # Extract delimiter and name
                    remaining = ' "'.join(parts[1:])
                    if remaining.startswith('"'):
                        remaining = remaining[1:]

                    # Find delimiter
                    delim_parts = remaining.split('" ')
                    if len(delim_parts) >= 2:
                        delimiter = delim_parts[0].strip()
                        name = delim_parts[1].strip().rstrip('"')
                    else:
                        delimiter = "/"
                        name = remaining.strip('"')

                    # Check if selectable (doesn't have \Noselect)
                    is_selectable = "\\Noselect" not in [a.lower() for a in attributes]

                    folders.append(FolderInfo(
                        name=name,
                        delimiter=delimiter,
                        attributes=attributes,
                        is_selectable=is_selectable
                    ))

            return folders

        except Exception as e:
            logger.error(f"Error listing folders: {e}")
            return []

    def get_folder_count(self, folder: str) -> int:
        """Get message count in a folder.

        Args:
            folder: Folder name.

        Returns:
            Message count or 0 if error.
        """
        if not self.client.is_connected:
            return 0

        try:
            typ, data = self.client.select_folder(folder, readonly=True)
            if typ == "OK" and data:
                return int(data[0])
        except Exception as e:
            logger.warning(f"Error getting folder count for {folder}: {e}")

        return 0

    def get_special_folders(self) -> dict[str, str]:
        """Get special folders like INBOX, Sent, etc.

        Returns:
            Dictionary mapping special folder type to actual folder name.
        """
        folders = self.list_folders()
        special = {}

        # Common Gmail folder mappings
        gmail_mappings = {
            "inbox": ["INBOX", "Caixa de entrada"],
            "sent": ["[Gmail]/Sent Mail", "[Gmail]/Enviados", "Sent", "Sent Items", "Enviados"],
            "drafts": ["[Gmail]/Drafts", "[Gmail]/Rascunhos", "Drafts", "Rascunhos"],
            "spam": ["[Gmail]/Spam", "Spam", "Lixo Eletrônico", "Junk"],
            "trash": ["[Gmail]/Trash", "[Gmail]/Lixeira", "Trash", "Lixeira", "Deleted Items"],
            "all": ["[Gmail]/All Mail", "[Gmail]/Todos os e-mails", "All Mail"],
            "starred": ["[Gmail]/Starred", "[Gmail]/Com estrela", "Starred"],
            "important": ["[Gmail]/Important", "[Gmail]/Importantes", "Important"],
        }

        for folder in folders:
            if not folder.is_selectable:
                continue

            folder_upper = folder.name.upper()

            for folder_type, possible_names in gmail_mappings.items():
                for name in possible_names:
                    if name.upper() in folder_upper or folder_upper in name.upper():
                        if folder_type not in special:
                            special[folder_type] = folder.name
                        break

        # Ensure INBOX is always present
        if "inbox" not in special:
            for folder in folders:
                if folder.name.upper() == "INBOX":
                    special["inbox"] = folder.name
                    break

        return special
