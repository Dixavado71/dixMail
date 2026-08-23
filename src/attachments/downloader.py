"""Attachment downloader."""

import logging
from pathlib import Path
from dataclasses import dataclass

from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

from src.email_parser.parser import AttachmentInfo

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation."""

    filename: str
    path: Path
    success: bool
    error: str | None = None


class AttachmentDownloader:
    """Downloads email attachments."""

    def __init__(self, download_dir: Path):
        """Initialize downloader.

        Args:
            download_dir: Base directory for downloads.
        """
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(
        self, attachment: AttachmentInfo, subfolder: str | None = None
    ) -> DownloadResult:
        """Download a single attachment.

        Args:
            attachment: Attachment info with payload.
            subfolder: Optional subfolder within downloads.

        Returns:
            DownloadResult object.
        """
        try:
            # Determine target directory
            if subfolder:
                target_dir = self.download_dir / subfolder
            else:
                target_dir = self.download_dir

            target_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            filename = self._get_unique_filename(target_dir, attachment.filename)
            filepath = target_dir / filename

            # Write file
            with open(filepath, "wb") as f:
                f.write(attachment.payload)

            logger.info(f"Downloaded {attachment.filename} to {filepath}")

            return DownloadResult(
                filename=filename,
                path=filepath,
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to download {attachment.filename}: {e}")
            return DownloadResult(
                filename=attachment.filename,
                path=Path(),
                success=False,
                error=str(e),
            )

    def download_multiple(
        self,
        attachments: list[AttachmentInfo],
        subfolder: str | None = None,
        show_progress: bool = True,
    ) -> list[DownloadResult]:
        """Download multiple attachments.

        Args:
            attachments: List of attachments to download.
            subfolder: Optional subfolder within downloads.
            show_progress: Whether to show progress bar.

        Returns:
            List of DownloadResult objects.
        """
        results = []

        if not attachments:
            return results

        if show_progress:
            with Progress(
                TextColumn("[bold blue]Downloading"),
                BarColumn(),
                TaskProgressColumn(),
                transient=True,
            ) as progress:
                task = progress.add_task("attachments", total=len(attachments))

                for attachment in attachments:
                    result = self.download(attachment, subfolder)
                    results.append(result)
                    progress.update(task, advance=1)
        else:
            for attachment in attachments:
                result = self.download(attachment, subfolder)
                results.append(result)

        return results

    def _get_unique_filename(self, directory: Path, filename: str) -> str:
        """Generate unique filename to avoid overwrites.

        Args:
            directory: Target directory.
            filename: Original filename.

        Returns:
            Unique filename.
        """
        filepath = directory / filename

        if not filepath.exists():
            return filename

        # File exists, generate unique name
        stem = filepath.stem
        suffix = filepath.suffix

        counter = 1
        while True:
            new_filename = f"{stem}_{counter}{suffix}"
            new_filepath = directory / new_filename

            if not new_filepath.exists():
                return new_filename

            counter += 1

        return f"{stem}_{counter}{suffix}"

    def create_subfolder(
        self, sender: str | None = None, subject: str | None = None, date_str: str | None = None
    ) -> str:
        """Create organized subfolder name.

        Args:
            sender: Email sender.
            subject: Email subject.
            date_str: Date string.

        Returns:
            Subfolder path string.
        """
        parts = []

        if date_str:
            parts.append(date_str[:10])  # YYYY-MM-DD

        if sender:
            # Extract just the email address or name
            if "@" in sender:
                sender = sender.split("@")[0]
            # Sanitize
            sender = "".join(c for c in sender if c.isalnum() or c in " -_")
            parts.append(sender[:50])

        if subject:
            # Sanitize subject
            subject = "".join(c for c in subject if c.isalnum() or c in " -_")
            parts.append(subject[:50])

        return "/".join(parts) if parts else ""
