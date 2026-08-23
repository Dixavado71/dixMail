"""CLI menu for Gmail Manager."""

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

from src.config.settings import Settings
from src.imap.client import IMAPClient
from src.imap.folders import FolderManager
from src.imap.messages import MessageManager, MessageSummary
from src.imap.search import SearchManager
from src.email_parser.parser import EmailParser, ParsedEmail
from src.attachments.downloader import AttachmentDownloader

logger = logging.getLogger(__name__)


class GmailManagerCLI:
    """Main CLI application for Gmail Manager."""

    def __init__(self, settings: Settings):
        """Initialize CLI.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.console = Console()

        # Initialize IMAP client
        self.imap_client = IMAPClient(
            email=settings.gmail_email,
            password=settings.gmail_app_password,
            server=settings.imap_server,
            port=settings.imap_port,
        )

        # Initialize managers
        self.folder_manager = FolderManager(self.imap_client)
        self.message_manager = MessageManager(self.imap_client)
        self.search_manager = SearchManager(self.imap_client)
        self.downloader = AttachmentDownloader(settings.download_dir)

        # Current state
        self.current_folder = "INBOX"
        self.selected_messages: list[int] = []
        self.is_connected = False

    def run(self) -> None:
        """Run the main application loop."""
        self._show_header()

        # Connect to IMAP
        if not self._connect():
            return

        # Main loop
        while True:
            try:
                choice = self._show_main_menu()

                if choice == "1":
                    self._show_inbox()
                elif choice == "2":
                    self._show_folders()
                elif choice == "3":
                    self._search_emails()
                elif choice == "4":
                    self._open_email()
                elif choice == "5":
                    self._select_messages()
                elif choice == "6":
                    self._download_attachments_menu()
                elif choice == "7":
                    self._manage_emails_menu()
                elif choice == "8":
                    self._refresh()
                elif choice == "0":
                    self._disconnect_and_exit()
                    break
                else:
                    self.console.print("[red]Opção inválida![/red]")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupto pelo usuário[/yellow]")
                break
            except Exception as e:
                logger.exception("Unexpected error")
                self.console.print(f"[red]Erro: {e}[/red]")

    def _connect(self) -> bool:
        """Connect to IMAP server.

        Returns:
            True if connection successful.
        """
        self.console.print("\n[cyan]Conectando ao Gmail...[/cyan]")

        if self.imap_client.connect():
            self.is_connected = True
            self.console.print("[green]✓ Conectado com sucesso![/green]")

            # Select inbox to verify access
            try:
                self.imap_client.select_folder(self.current_folder, readonly=True)
                count = self.message_manager.get_message_count()
                self.console.print(f"[green]✓ Caixa de entrada acessível ({count} mensagens)[/green]")
            except Exception as e:
                self.console.print(f"[red]Erro ao acessar INBOX: {e}[/red]")
                return False

            return True
        else:
            self.console.print("[red]✗ Falha na conexão. Verifique suas credenciais.[/red]")
            self.console.print("\n[dim]Possíveis causas:[/dim]")
            self.console.print("  • Credenciais incorretas no .env")
            self.console.print("  • Senha de app não configurada")
            self.console.print("  • Problemas de rede")
            return False

    def _disconnect_and_exit(self) -> None:
        """Disconnect and exit."""
        if self.imap_client.is_connected:
            self.imap_client.disconnect()
        self.console.print("\n[green]Até logo![/green]")

    def _show_header(self) -> None:
        """Show application header."""
        header = Panel(
            Text("GMAIL MANAGER", style="bold white", justify="center"),
            title="[bold blue]Gmail Manager CLI[/bold blue]",
            subtitle=f"[dim]v1.0.0[/dim]",
        )
        self.console.print(header)

    def _show_status_panel(self) -> Panel:
        """Show connection status panel."""
        status_text = Text()
        status_text.append(f"Conta: {self.settings.gmail_email}\n", style="white")

        if self.is_connected:
            status_text.append("Status: ● Conectado", style="green")
        else:
            status_text.append("Status: ○ Desconectado", style="red")

        status_text.append(f"\nPasta: {self.current_folder}", style="dim")
        status_text.append(f"\nSelecionados: {len(self.selected_messages)}", style="dim")

        return Panel(status_text, title="[bold]Status[/bold]")

    def _show_main_menu(self) -> str:
        """Show main menu and get user choice.

        Returns:
            User's choice.
        """
        self.console.print()
        self.console.print(self._show_status_panel())
        self.console.print()

        menu_items = [
            ("1", "Caixa de entrada"),
            ("2", "Pastas / Marcadores"),
            ("3", "Pesquisar e-mails"),
            ("4", "Abrir e-mail"),
            ("5", "Selecionar e-mails"),
            ("6", "Baixar anexos"),
            ("7", "Gerenciar e-mails"),
            ("8", "Atualizar"),
            ("0", "Sair"),
        ]

        for key, label in menu_items:
            self.console.print(f"  [bold cyan]{key}.[/bold cyan] {label}")

        self.console.print()
        return Prompt.ask("Escolha uma opção", choices=[m[0] for m in menu_items])

    def _show_inbox(self, page: int = 0, page_size: int = 50) -> None:
        """Show inbox messages with pagination.

        Args:
            page: Page number (0-indexed).
            page_size: Number of messages per page.
        """
        self.console.print(f"\n[cyan]Carregando caixa de entrada...[/cyan]")

        try:
            self.imap_client.select_folder(self.current_folder, readonly=True)
            total_count = self.message_manager.get_message_count()
            
            if total_count == 0:
                self.console.print("[yellow]Nenhuma mensagem encontrada.[/yellow]")
                return

            summaries = self.message_manager.get_message_summaries(
                limit=page_size, 
                offset=page * page_size
            )

            if not summaries:
                self.console.print("[yellow]Nenhuma mensagem encontrada nesta página.[/yellow]")
                return

            table = Table(title=f"Caixa de Entrada - {self.current_folder} (Página {page + 1})")
            table.add_column("ID", style="cyan", width=5)
            table.add_column("Sel", width=4, justify="center")
            table.add_column("Data", width=12)
            table.add_column("Remetente", width=30)
            table.add_column("Assunto", width=40)
            table.add_column("Status", width=8)
            table.add_column("Anexos", width=8)

            for msg in summaries:
                # Check if message is selected
                is_selected = msg.id in self.selected_messages
                sel_icon = "[green]✓[/green]" if is_selected else ""
                
                status_style = "bold green" if msg.status == "NOVO" else "dim"
                annex_icon = f"📎 {msg.attachment_count}" if msg.has_attachments else ""

                table.add_row(
                    str(msg.id),
                    sel_icon,
                    msg.date_str,
                    msg.from_[:28] + "..." if len(msg.from_) > 30 else msg.from_,
                    msg.subject[:38] + "..." if len(msg.subject) > 40 else msg.subject,
                    Text(msg.status, style=status_style),
                    annex_icon,
                )

            self.console.print(table)
            self.console.print(f"\n[dim]Mostrando {len(summaries)} de {total_count} mensagens (página {page + 1})[/dim]")
            
            # Pagination controls
            total_pages = (total_count + page_size - 1) // page_size
            if total_pages > 1:
                self.console.print("\n[dim]Navegação: [bold]n[/bold] próxima página, [bold]p[/bold] página anterior, [bold]1[/bold]-[bold]{max_page}[/bold] ir para página[/dim]".format(max_page=total_pages))
                
                nav_choice = Prompt.ask("\nNavegar", choices=["n", "p", "1", "2", "3", "4", "5"], default="")
                
                if nav_choice == "n" and page < total_pages - 1:
                    self._show_inbox(page=page + 1, page_size=page_size)
                elif nav_choice == "p" and page > 0:
                    self._show_inbox(page=page - 1, page_size=page_size)
                elif nav_choice.isdigit():
                    new_page = int(nav_choice) - 1
                    if 0 <= new_page < total_pages:
                        self._show_inbox(page=new_page, page_size=page_size)
                    else:
                        self.console.print("[red]Página inválida[/red]")

        except Exception as e:
            logger.exception("Error loading inbox")
            self.console.print(f"[red]Erro ao carregar inbox: {e}[/red]")

    def _show_folders(self) -> None:
        """Show available folders."""
        self.console.print("\n[cyan]Carregando pastas...[/cyan]")

        try:
            folders = self.folder_manager.list_folders()

            if not folders:
                self.console.print("[yellow]Nenhuma pasta encontrada.[/yellow]")
                return

            table = Table(title="Pastas Disponíveis")
            table.add_column("Nome", width=40)
            table.add_column("Mensagens", width=12)
            table.add_column("Selecionar", width=15)

            special = self.folder_manager.get_special_folders()

            for folder in folders:
                if not folder.is_selectable:
                    continue

                count = self.folder_manager.get_folder_count(folder.name)

                # Mark special folders
                folder_type = ""
                for ftype, fname in special.items():
                    if fname == folder.name:
                        folder_type = f"[bold]{ftype.upper()}[/bold]"
                        break

                can_select = "[green]Sim[/green]" if folder.is_selectable else "[red]Não[/red]"
                table.add_row(
                    f"{folder.name} {folder_type}",
                    str(count),
                    can_select,
                )

            self.console.print(table)

            # Ask if user wants to select a folder
            if Confirm.ask("\nDeseja mudar para outra pasta?"):
                folder_name = Prompt.ask("Nome da pasta")
                if folder_name:
                    self.current_folder = folder_name
                    self.console.print(f"[green]Pasta alterada para: {folder_name}[/green]")

        except Exception as e:
            logger.exception("Error listing folders")
            self.console.print(f"[red]Erro ao listar pastas: {e}[/red]")

    def _search_emails(self) -> None:
        """Search emails with improved feedback."""
        self.console.print("\n[cyan]Pesquisa de e-mails[/cyan]")
        self.console.print("\n[dim]Formatos suportados:[/dim]")
        self.console.print("  from:email@exemplo.com")
        self.console.print("  subject:assunto")
        self.console.print("  to:destinatario")
        self.console.print("  unread (não lidos)")
        self.console.print("  texto livre (busca em assunto e corpo)")

        query = Prompt.ask("\nDigite sua pesquisa")

        if not query:
            return

        self.console.print(f"\n[cyan]Pesquisando por: {query}[/cyan]")

        try:
            message_ids = self.search_manager.search(query)

            if not message_ids:
                self.console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
                return

            result_count = len(message_ids)
            display_limit = 50
            
            self.console.print(f"[green]✓ {result_count} resultados encontrados[/green]")
            
            if result_count > display_limit:
                self.console.print(f"[dim]Exibindo os primeiros {display_limit} resultados[/dim]")

            # Show results
            self.imap_client.select_folder(self.current_folder, readonly=True)
            
            # Get summaries for the found messages (limited for display)
            all_summaries = self.message_manager.get_message_summaries(limit=result_count)
            search_summaries = [s for s in all_summaries if s.id in message_ids][:display_limit]

            if search_summaries:
                table = Table(title=f"Resultados da Pesquisa ({len(search_summaries)} de {result_count})")
                table.add_column("ID", style="cyan", width=5)
                table.add_column("Sel", width=4, justify="center")
                table.add_column("Data", width=12)
                table.add_column("Remetente", width=30)
                table.add_column("Assunto", width=50)

                for msg in search_summaries:
                    is_selected = msg.id in self.selected_messages
                    sel_icon = "[green]✓[/green]" if is_selected else ""
                    
                    table.add_row(
                        str(msg.id),
                        sel_icon,
                        msg.date_str,
                        msg.from_[:28] + "..." if len(msg.from_) > 30 else msg.from_,
                        msg.subject[:48] + "..." if len(msg.subject) > 50 else msg.subject,
                    )

                self.console.print(table)

        except Exception as e:
            logger.exception("Search error")
            self.console.print(f"[red]Erro na pesquisa: {e}[/red]")

    def _open_email(self) -> None:
        """Open and read an email."""
        msg_id_str = Prompt.ask("\nDigite o ID do e-mail para abrir")

        if not msg_id_str:
            return

        try:
            msg_id = int(msg_id_str)
        except ValueError:
            self.console.print("[red]ID inválido[/red]")
            return

        self.console.print(f"\n[cyan]Carregando e-mail {msg_id}...[/cyan]")

        try:
            raw_message = self.imap_client.fetch_full(msg_id)

            if not raw_message:
                self.console.print("[red]Não foi possível carregar o e-mail.[/red]")
                return

            # Parse email
            parsed = EmailParser.parse(raw_message)

            # Display email
            self.console.print()
            self.console.print(Panel(
                f"[bold]De:[/bold] {parsed.from_}\n"
                f"[bold]Para:[/bold] {parsed.to}\n"
                f"[bold]Data:[/bold] {parsed.date}\n"
                f"[bold]Assunto:[/bold] {parsed.subject}",
                title="[bold blue]Cabeçalho[/bold blue]",
            ))

            # Body content
            body = parsed.body
            if not body:
                body = "[Sem conteúdo textual]"

            # Convert HTML to text if needed
            if parsed.body_html and not parsed.body_plain:
                body = EmailParser.html_to_text(parsed.body_html)

            self.console.print()
            self.console.print("[bold]------------------------------------[/bold]")
            self.console.print("[bold]CONTEÚDO[/bold]")
            self.console.print("[bold]------------------------------------[/bold]")
            self.console.print(body)

            # Attachments
            if parsed.attachments:
                self.console.print()
                self.console.print("[bold]Anexos:[/bold]")
                for i, att in enumerate(parsed.attachments, 1):
                    self.console.print(f"  {i}. {att.filename} ({att.size_formatted})")

        except Exception as e:
            logger.exception("Error opening email")
            self.console.print(f"[red]Erro ao abrir e-mail: {e}[/red]")

    def _select_messages(self) -> None:
        """Select multiple messages."""
        self.console.print("\n[cyan]Selecionar e-mails[/cyan]")
        self.console.print("\n[dim]Digite os IDs separados por vírgula ou 'all' para todos.[/dim]")

        input_str = Prompt.ask("\nIDs dos e-mails")

        if input_str.lower() == "all":
            try:
                self.imap_client.select_folder(self.current_folder, readonly=True)
                count = self.message_manager.get_message_count()
                # Get all message IDs
                all_ids = self.imap_client.search("ALL")
                self.selected_messages = all_ids
                self.console.print(f"[green]✓ {len(self.selected_messages)} e-mails selecionados[/green]")
            except Exception as e:
                self.console.print(f"[red]Erro ao selecionar todos: {e}[/red]")
        else:
            try:
                ids = [int(x.strip()) for x in input_str.split(",") if x.strip()]
                self.selected_messages = ids
                self.console.print(f"[green]✓ {len(self.selected_messages)} e-mails selecionados[/green]")
            except ValueError:
                self.console.print("[red]IDs inválidos[/red]")

    def _download_attachments_menu(self) -> None:
        """Menu for downloading attachments."""
        self.console.print("\n[cyan]Baixar Anexos[/cyan]")

        if not self.selected_messages:
            self.console.print("[yellow]Nenhum e-mail selecionado. Selecione e-mails primeiro.[/yellow]")
            return

        self.console.print(f"\nE-mails selecionados: {len(self.selected_messages)}")

        if not Confirm.ask("\nBaixar todos os anexos dos e-mails selecionados?"):
            return

        # Collect all attachments
        all_attachments = []

        with Progress(transient=True) as progress:
            task = progress.add_task("Coletando anexos...", total=len(self.selected_messages))

            for msg_id in self.selected_messages:
                try:
                    raw = self.imap_client.fetch_full(msg_id)
                    if raw:
                        parsed = EmailParser.parse(raw)
                        all_attachments.extend(parsed.attachments)
                except Exception as e:
                    logger.warning(f"Failed to get attachments for message {msg_id}: {e}")

                progress.update(task, advance=1)

        if not all_attachments:
            self.console.print("[yellow]Nenhum anexo encontrado.[/yellow]")
            return

        self.console.print(f"\n[green]✓ {len(all_attachments)} anexos encontrados[/green]")

        # Download
        results = self.downloader.download_multiple(all_attachments, show_progress=True)

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        self.console.print()
        self.console.print(f"[green]Downloads realizados: {success_count}[/green]")
        if fail_count > 0:
            self.console.print(f"[red]Falhas: {fail_count}[/red]")

    def _manage_emails_menu(self) -> None:
        """Menu for managing emails."""
        self.console.print("\n[cyan]Gerenciar E-mails[/cyan]")

        if not self.selected_messages:
            self.console.print("[yellow]Nenhum e-mail selecionado.[/yellow]")
            return

        self.console.print(f"\nE-mails selecionados: {len(self.selected_messages)}")

        options = [
            ("1", "Marcar como lido"),
            ("2", "Marcar como não lido"),
            ("3", "Excluir"),
            ("4", "Mover para pasta"),
        ]

        for key, label in options:
            self.console.print(f"  [bold cyan]{key}.[/bold cyan] {label}")

        choice = Prompt.ask("\nEscolha", choices=[o[0] for o in options])

        if choice == "1":
            self._mark_as_read()
        elif choice == "2":
            self._mark_as_unread()
        elif choice == "3":
            self._delete_emails()
        elif choice == "4":
            self._move_emails()

    def _mark_as_read(self) -> None:
        """Mark selected emails as read."""
        if not Confirm.ask(f"\nMarcar {len(self.selected_messages)} e-mails como lidos?"):
            return

        try:
            success = self.imap_client.mark_read(self.selected_messages)
            if success:
                self.console.print("[green]✓ E-mails marcados como lidos[/green]")
            else:
                self.console.print("[yellow]Alguns e-mails não puderam ser marcados[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Erro: {e}[/red]")

    def _mark_as_unread(self) -> None:
        """Mark selected emails as unread."""
        if not Confirm.ask(f"\nMarcar {len(self.selected_messages)} e-mails como não lidos?"):
            return

        try:
            success = self.imap_client.mark_unread(self.selected_messages)
            if success:
                self.console.print("[green]✓ E-mails marcados como não lidos[/green]")
            else:
                self.console.print("[yellow]Alguns e-mails não puderam ser marcados[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Erro: {e}[/red]")

    def _delete_emails(self) -> None:
        """Delete selected emails with preview."""
        self.console.print(f"\n[red bold]ATENÇÃO: Esta ação excluirá {len(self.selected_messages)} e-mails[/red bold]")
        
        # Show preview of emails to be deleted
        if self.selected_messages:
            self.console.print("\n[yellow]E-mails que serão excluídos:[/yellow]")
            try:
                self.imap_client.select_folder(self.current_folder, readonly=True)
                all_summaries = self.message_manager.get_message_summaries(limit=len(self.selected_messages))
                preview_summaries = [s for s in all_summaries if s.id in self.selected_messages][:10]
                
                for msg in preview_summaries:
                    self.console.print(f"  • ID {msg.id}: {msg.subject[:50]} (de: {msg.from_[:30]})")
                
                if len(self.selected_messages) > 10:
                    self.console.print(f"  ... e mais {len(self.selected_messages) - 10} e-mails")
            except Exception as e:
                self.console.print(f"[dim]Não foi possível mostrar preview: {e}[/dim]")

        if not Confirm.ask("\nTem certeza que deseja continuar?"):
            return

        try:
            success = self.imap_client.delete(self.selected_messages)
            if success:
                self.console.print("[green]✓ E-mails marcados para exclusão[/green]")
                self.console.print("[dim]Nota: No Gmail, os e-mails vão para a Lixeira.[/dim]")
                self.selected_messages.clear()
            else:
                self.console.print("[yellow]Alguns e-mails não puderam ser excluídos[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Erro: {e}[/red]")

    def _move_emails(self) -> None:
        """Move selected emails to another folder."""
        folder_name = Prompt.ask("\nDigite o nome da pasta de destino")

        if not folder_name:
            return

        if not Confirm.ask(f"\nMover {len(self.selected_messages)} e-mails para '{folder_name}'?"):
            return

        try:
            success = self.imap_client.move(self.selected_messages, folder_name)
            if success:
                self.console.print(f"[green]✓ E-mails movidos para {folder_name}[/green]")
                self.selected_messages.clear()
            else:
                self.console.print("[red]Falha ao mover e-mails. Verifique se a pasta existe.[/red]")
        except Exception as e:
            self.console.print(f"[red]Erro: {e}[/red]")

    def _refresh(self) -> None:
        """Refresh connection and data."""
        self.console.print("\n[cyan]Atualizando...[/cyan]")

        try:
            if self.imap_client.reconnect(max_attempts=3):
                self.is_connected = True
                self.console.print("[green]✓ Conexão atualizada[/green]")
            else:
                self.console.print("[red]✗ Falha ao reconectar[/red]")
                self.is_connected = False
        except Exception as e:
            self.console.print(f"[red]Erro ao atualizar: {e}[/red]")
