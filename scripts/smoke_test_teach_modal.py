import os
import sys
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_test():
    print("[INFO] Iniciando smoke test visual do frontend...")
    screenshot_dir = r"C:\Users\aryar\.gemini\antigravity\brain\d3523ade-dad0-4926-a10a-6ce104cfad8c"
    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(screenshot_dir, "smoke_test_teach_variation.png")
    local_screenshot = os.path.join(os.getcwd(), "smoke_test_teach_variation.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Acessar http://localhost:5300
        print("[1] Acessando http://localhost:5300...")
        page.goto("http://localhost:5300", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # 2. Login se necessário
        email_locator = page.locator("input[type='email']")
        if email_locator.count() > 0 and email_locator.is_visible():
            print("[2] Tela de login detectada. Realizando login...")
            # Limpar qualquer conteúdo previamente
            email_locator.fill("")
            email_locator.type("aryarajmarketing@gmail.com")

            pass_locator = page.locator("input[type='password']")
            pass_locator.fill("")
            pass_locator.type("123456")

            page.locator("button[type='submit']").click()
            page.wait_for_timeout(3000)
            print("   Login efetuado com sucesso.")
        else:
            print("[2] Já autenticado ou na tela principal.")

        # 3. Navegar para Bases de Conhecimento / Inbox
        print("[3] Navegando para http://localhost:5300/knowledge-bases?tab=inbox...")
        page.goto("http://localhost:5300/knowledge-bases?tab=inbox", wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Se houver aba "Inbox de Dúvidas" no topo e não estiver ativa, clicar
        inbox_tab_btn = page.locator("button:has-text('Inbox de Dúvidas')")
        if inbox_tab_btn.count() > 0 and inbox_tab_btn.first.is_visible():
            print("   Confirmando aba Inbox de Dúvidas ativa...")
            inbox_tab_btn.first.click()
            page.wait_for_timeout(2000)

        # 4. Localizar a lista de dúvidas e o botão "Ensinar Resposta"
        print("[4] Procurando botões 'Ensinar Resposta'...")
        teach_buttons = page.locator(".uq-btn-teach, button:has-text('Ensinar Resposta')")
        count = teach_buttons.count()
        print(f"   Encontrados {count} botões 'Ensinar Resposta'.")
        if count == 0:
            print("[ERRO] Nenhum botão 'Ensinar Resposta' encontrado na tela!")
            page.screenshot(path=local_screenshot)
            sys.exit(1)

        print("   Clicando no primeiro botão 'Ensinar Resposta'...")
        teach_buttons.first.click()
        page.wait_for_timeout(2000)

        # 5. Validação no modal
        print("[5] Validando elementos do modal 'Ensinar Resposta'...")
        modal = page.locator(".uq-modal")
        if not modal.is_visible():
            print("[ERRO] Modal .uq-modal não está visível!")
            sys.exit(1)
        print("   [OK] Modal 'Ensinar Resposta' visível.")

        # Abas "📚 Base (RAG)" e "🤖 Prompt Agente"
        tab_rag = page.locator(".teach-mode-tabs button:has-text('Base (RAG)')")
        tab_prompt = page.locator(".teach-mode-tabs button:has-text('Prompt Agente')")
        
        assert tab_rag.is_visible(), "Aba '📚 Base (RAG)' não está visível"
        assert tab_prompt.is_visible(), "Aba '🤖 Prompt Agente' não está visível"
        print("   [OK] Abas 'Base (RAG)' e 'Prompt Agente' estão visíveis.")

        # Sub-abas: "➕ Criar Nova Pergunta" e "🔗 Variação de Pergunta Existente"
        btn_sub_new = page.locator(".teach-submode-btn:has-text('Criar Nova Pergunta')")
        btn_sub_var = page.locator(".teach-submode-btn:has-text('Variação de Pergunta Existente')")

        assert btn_sub_new.is_visible(), "Botão 'Criar Nova Pergunta' não está visível"
        assert btn_sub_var.is_visible(), "Botão 'Variação de Pergunta Existente' não está visível"
        print("   [OK] Botões 'Criar Nova Pergunta' e 'Variação de Pergunta Existente' estão visíveis.")

        # Clicar em "🔗 Variação de Pergunta Existente"
        print("   Clicando em 'Variação de Pergunta Existente'...")
        btn_sub_var.click()
        page.wait_for_timeout(2000)

        # Verificar se os itens/perguntas da base são carregados
        select_item = page.locator("select[data-testid='select-existing-question']")
        if select_item.count() > 0:
            options_count = select_item.locator("option").count()
            print(f"   [OK] Itens/perguntas carregados no select: {options_count} perguntas disponíveis.")

        # Verificar exibição do card com "Resposta Oficial Cadastrada" e variações
        official_label = page.locator(".existing-qa-label:has-text('Resposta Oficial Cadastrada')")
        answer_box = page.locator(".existing-qa-answer-box")

        assert official_label.is_visible(), "Rótulo 'Resposta Oficial Cadastrada' não está visível"
        assert answer_box.is_visible(), "Caixa da resposta oficial não está visível"
        answer_text = answer_box.text_content().strip()
        print(f"   [OK] Card de Resposta Oficial exibido com sucesso!")
        print(f"      Texto da resposta: '{answer_text[:90]}...'")

        # Verificar variações atuais se houver
        variations_chips = page.locator(".variation-chip")
        var_count = variations_chips.count()
        print(f"      Variações existentes exibidas no card: {var_count}")
        for i in range(var_count):
            print(f"       - {variations_chips.nth(i).text_content()}")

        # 6. Capturar screenshot
        print("[6] Capturando screenshot da tela com modal aberto exibindo o modo de variação...")
        page.screenshot(path=screenshot_path)
        page.screenshot(path=local_screenshot)
        print(f"   [OK] Screenshot salvo em: {screenshot_path}")
        print(f"   [OK] Screenshot salvo em: {local_screenshot}")

        browser.close()
        print("\n[SUCESSO] Smoke test visual e funcional concluído com 100% de sucesso!")

if __name__ == "__main__":
    run_test()
