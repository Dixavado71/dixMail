#!/usr/bin/env python3
"""Gmail Manager CLI - Main Application Entry Point."""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

console = Console()


def main():
    """Main entry point for Gmail Manager CLI."""
    console.print("\n[bold blue]Iniciando Gmail Manager...[/bold blue]\n")

    # Load settings
    try:
        from src.config.settings import load_settings

        console.print("[cyan]Carregando configurações...[/cyan]")
        settings = load_settings()
        console.print("[green]✓ Configurações carregadas[/green]")

    except FileNotFoundError:
        console.print("[red]✗ Arquivo .env não encontrado![/red]")
        console.print("\n[dim]Crie um arquivo .env na raiz do projeto com:[/dim]")
        console.print("  GMAIL_EMAIL=seuemail@gmail.com")
        console.print("  GMAIL_APP_PASSWORD=sua_senha_de_app")
        console.print("  DOWNLOAD_DIR=downloads")
        console.print("\n[dim]Ou copie .env.example e edite.[/dim]")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[red]✗ Erro de configuração: {e}[/red]")
        sys.exit(1)

    # Validate download directory
    settings.download_dir.mkdir(parents=True, exist_ok=True)

    # Start CLI
    try:
        from src.cli.menu import GmailManagerCLI

        cli = GmailManagerCLI(settings)
        cli.run()

    except KeyboardInterrupt:
        console.print("\n[yellow]Aplicação encerrada pelo usuário.[/yellow]")
        sys.exit(0)

    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"\n[red]Erro inesperado: {e}[/red]")
        console.print("[dim]Verifique o log para mais detalhes.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
