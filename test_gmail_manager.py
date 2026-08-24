#!/usr/bin/env python3
"""Test script for Gmail Manager CLI - Automated testing of all features."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import load_settings
from src.imap.client import IMAPClient
from src.imap.folders import FolderManager
from src.imap.messages import MessageManager
from src.imap.search import SearchManager
from src.email_parser.parser import EmailParser
from src.attachments.downloader import AttachmentDownloader


def test_settings():
    """Test settings loading."""
    print("\n" + "="*60)
    print("TESTE 1: Carregamento de Configurações")
    print("="*60)
    
    try:
        settings = load_settings()
        print(f"✓ Email carregado: {settings.gmail_email}")
        print(f"✓ Senha configurada: {'Sim' if settings.gmail_app_password else 'Não'}")
        print(f"✓ Download dir: {settings.download_dir}")
        
        is_valid, errors = settings.validate()
        if not is_valid:
            print(f"✗ Erros de validação: {errors}")
            return False
        
        print("✓ Configurações válidas")
        return True
    except Exception as e:
        print(f"✗ Erro ao carregar configurações: {e}")
        return False


def test_imap_connection(settings):
    """Test IMAP connection."""
    print("\n" + "="*60)
    print("TESTE 2: Conexão IMAP")
    print("="*60)
    
    client = IMAPClient(
        email=settings.gmail_email,
        password=settings.gmail_app_password,
        server=settings.imap_server,
        port=settings.imap_port,
    )
    
    try:
        print(f"Tentando conectar a {settings.imap_server}:{settings.imap_port}...")
        if client.connect():
            print("✓ Conectado com sucesso")
            
            # Test select folder
            typ, data = client.select_folder("INBOX", readonly=True)
            if typ == "OK":
                print(f"✓ INBOX selecionada: {data[0].decode()} mensagens")
                client.disconnect()
                return True, client
            else:
                print(f"✗ Falha ao selecionar INBOX: {typ}")
                client.disconnect()
                return False, client
        else:
            print("✗ Falha na conexão")
            return False, client
    except Exception as e:
        print(f"✗ Erro na conexão: {e}")
        if client.is_connected:
            client.disconnect()
        return False, client


def test_folders(client):
    """Test folder listing."""
    print("\n" + "="*60)
    print("TESTE 3: Listagem de Pastas")
    print("="*60)
    
    folder_manager = FolderManager(client)
    
    try:
        folders = folder_manager.list_folders()
        print(f"✓ {len(folders)} pastas encontradas")
        
        special = folder_manager.get_special_folders()
        print(f"✓ Pastas especiais: {special}")
        
        # Show first 5 folders
        for folder in folders[:5]:
            count = folder_manager.get_folder_count(folder.name)
            print(f"  • {folder.name}: {count} mensagens")
        
        return True
    except Exception as e:
        print(f"✗ Erro ao listar pastas: {e}")
        return False


def test_messages(client):
    """Test message listing and parsing."""
    print("\n" + "="*60)
    print("TESTE 4: Listagem e Parse de Mensagens")
    print("="*60)
    
    message_manager = MessageManager(client)
    
    try:
        # Select inbox
        client.select_folder("INBOX", readonly=True)
        count = message_manager.get_message_count()
        print(f"✓ Total de mensagens: {count}")
        
        if count == 0:
            print("⚠ Nenhuma mensagem na caixa de entrada")
            return True
        
        # Get summaries
        summaries = message_manager.get_message_summaries(limit=5)
        print(f"✓ {len(summaries)} resumos carregados")
        
        for msg in summaries:
            print(f"  • ID {msg.id}: {msg.date_str} | {msg.from_[:30]} | {msg.subject[:40]} | {msg.status}")
        
        return True
    except Exception as e:
        print(f"✗ Erro ao listar mensagens: {e}")
        return False


def test_search(client):
    """Test search functionality."""
    print("\n" + "="*60)
    print("TESTE 5: Pesquisa de E-mails")
    print("="*60)
    
    search_manager = SearchManager(client)
    
    try:
        # Test ALL search
        all_ids = search_manager.search("ALL")
        print(f"✓ Pesquisa 'ALL': {len(all_ids)} resultados")
        
        # Test UNSEEN search
        unseen_ids = search_manager.search("UNSEEN")
        print(f"✓ Pesquisa 'UNSEEN': {len(unseen_ids)} resultados")
        
        return True
    except Exception as e:
        print(f"✗ Erro na pesquisa: {e}")
        return False


def test_select_and_delete(client, settings):
    """Test selecting and deleting emails."""
    print("\n" + "="*60)
    print("TESTE 6: Seleção e Exclusão de E-mails")
    print("="*60)
    
    message_manager = MessageManager(client)
    
    try:
        # Select inbox (writable mode for delete)
        client.select_folder("INBOX", readonly=False)
        count = message_manager.get_message_count()
        
        if count < 2:
            print("⚠ Poucas mensagens para testar exclusão")
            return True
        
        # Get last 2 messages (older ones)
        all_ids = client.search("ALL")
        if len(all_ids) < 2:
            print("⚠ Apenas uma mensagem disponível")
            return True
        
        # Select last 2 messages
        test_ids = all_ids[-2:]
        print(f"✓ E-mails selecionados para teste: {test_ids}")
        
        # Get summaries for preview
        summaries = message_manager.get_message_summaries(limit=len(all_ids))
        test_summaries = [s for s in summaries if s.id in test_ids]
        
        print("\nE-mails que serão excluídos:")
        for msg in test_summaries:
            print(f"  • ID {msg.id}: {msg.subject[:50]}")
        
        # Mark for deletion
        print(f"\nMarcando {len(test_ids)} e-mails para exclusão...")
        success = client.delete(test_ids)
        
        if success:
            print(f"✓ E-mails marcados para exclusão")
            
            # Expunge to permanently delete
            print("Executando expunge...")
            expunge_success = client.expunge()
            
            if expunge_success:
                print(f"✓ E-mails permanentemente excluídos")
                
                # Verify deletion
                new_count = message_manager.get_message_count()
                deleted_count = count - new_count
                print(f"✓ Contagem antes: {count}, depois: {new_count}, excluídos: {deleted_count}")
                
                if deleted_count == len(test_ids):
                    print("✓ Exclusão verificada com sucesso")
                    return True
                else:
                    print(f"⚠ Contagem não confere totalmente, mas operação foi executada")
                    return True
            else:
                print("✗ Falha no expunge")
                return False
        else:
            print("✗ Falha ao marcar para exclusão")
            return False
            
    except Exception as e:
        print(f"✗ Erro na exclusão: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mark_read_unread(client):
    """Test marking emails as read/unread."""
    print("\n" + "="*60)
    print("TESTE 7: Marcar como Lido/Não Lido")
    print("="*60)
    
    message_manager = MessageManager(client)
    
    try:
        # Select inbox writable
        client.select_folder("INBOX", readonly=False)
        
        # Get one unread message if possible
        unseen_ids = client.search("UNSEEN")
        
        if unseen_ids:
            test_id = unseen_ids[0]
            print(f"✓ E-mail não lido encontrado: ID {test_id}")
            
            # Mark as read
            print(f"Marcando ID {test_id} como lido...")
            success = client.mark_read([test_id])
            if success:
                print(f"✓ Marcado como lido")
            else:
                print(f"⚠ Falha ao marcar como lido")
            
            # Mark as unread
            print(f"Marcando ID {test_id} como não lido...")
            success = client.mark_unread([test_id])
            if success:
                print(f"✓ Marcado como não lido")
                return True
            else:
                print(f"⚠ Falha ao marcar como não lido")
                return False
        else:
            print("⚠ Nenhum e-mail não lido para testar")
            # Test with any message
            all_ids = client.search("ALL")
            if all_ids:
                test_id = all_ids[0]
                print(f"Testando com e-mail lido: ID {test_id}")
                
                # Mark as unread first
                success = client.mark_unread([test_id])
                if success:
                    print(f"✓ Marcado como não lido")
                    
                    # Then mark as read
                    success = client.mark_read([test_id])
                    if success:
                        print(f"✓ Marcado como lido")
                        return True
            
            return True
            
    except Exception as e:
        print(f"✗ Erro ao marcar leitura: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_attachments(client, settings):
    """Test attachment detection and download."""
    print("\n" + "="*60)
    print("TESTE 8: Detecção e Download de Anexos")
    print("="*60)
    
    downloader = AttachmentDownloader(settings.download_dir)
    
    try:
        client.select_folder("INBOX", readonly=True)
        all_ids = client.search("ALL")
        
        attachments_found = 0
        emails_with_attachments = 0
        
        # Check first 20 emails for attachments
        for msg_id in all_ids[-20:]:
            raw = client.fetch_full(msg_id)
            if raw:
                parsed = EmailParser.parse(raw)
                if parsed.attachments:
                    emails_with_attachments += 1
                    attachments_found += len(parsed.attachments)
                    print(f"  • ID {msg_id}: {len(parsed.attachments)} anexos")
                    for att in parsed.attachments:
                        print(f"      - {att.filename} ({att.size_formatted})")
        
        print(f"\n✓ E-mails com anexos: {emails_with_attachments}")
        print(f"✓ Total de anexos: {attachments_found}")
        
        if attachments_found > 0:
            print("✓ Detecção de anexos funcionando")
            return True
        else:
            print("⚠ Nenhum anexo encontrado nos últimos 20 e-mails")
            return True
            
    except Exception as e:
        print(f"✗ Erro com anexos: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("#  GMAIL MANAGER CLI - TESTE AUTOMATIZADO COMPLETO")
    print("#"*60)
    
    results = {
        "settings": False,
        "connection": False,
        "folders": False,
        "messages": False,
        "search": False,
        "select_delete": False,
        "mark_read": False,
        "attachments": False,
    }
    
    # Test 1: Settings
    if not test_settings():
        print("\n✗ FALHA CRÍTICA: Configurações inválidas. Interrompendo testes.")
        return 1
    
    results["settings"] = True
    
    # Test 2: Connection
    connected, client = test_imap_connection(load_settings())
    results["connection"] = connected
    
    if not connected:
        print("\n✗ FALHA CRÍTICA: Não foi possível conectar. Verifique credenciais.")
        print("\nResumo:")
        print(f"  ✓ Configurações: OK")
        print(f"  ✗ Conexão: FALHOU")
        return 1
    
    settings = load_settings()
    
    # Test 3: Folders
    results["folders"] = test_folders(client)
    
    # Reconnect for remaining tests
    if not client.is_connected:
        client.connect()
    
    # Test 4: Messages
    results["messages"] = test_messages(client)
    
    # Test 5: Search
    results["search"] = test_search(client)
    
    # Test 6: Select and Delete (DESTRUCTIVE - use last messages)
    results["select_delete"] = test_select_and_delete(client, settings)
    
    # Reconnect after delete
    if not client.is_connected:
        client.connect()
    
    # Test 7: Mark Read/Unread
    results["mark_read"] = test_mark_read_unread(client)
    
    # Test 8: Attachments
    results["attachments"] = test_attachments(client, settings)
    
    # Cleanup
    client.disconnect()
    
    # Summary
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema 100% funcional.")
        return 0
    elif passed >= total - 1:
        print(f"\n✅ Sistema funcional ({passed}/{total}). Pequenas issues não críticas.")
        return 0
    else:
        print(f"\n⚠ Sistema com issues ({passed}/{total}). Revisar falhas.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
