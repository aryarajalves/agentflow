import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def main():
    artifacts_dir = r"C:\Users\aryar\.gemini\antigravity\brain\1a047bb3-eb1b-4c47-9518-e6c0c86aafc7"
    os.makedirs(artifacts_dir, exist_ok=True)
    before_path = os.path.join(artifacts_dir, "inbox_modal_new_question_before.png")
    after_path = os.path.join(artifacts_dir, "inbox_modal_variation_after.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("1. Acessando http://localhost:5300...")
        await page.goto("http://localhost:5300", wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(2000)

        # Verifica se caiu no login
        if "login" in page.url or await page.locator("input[type='email']").count() > 0:
            print("2. Fazendo login com credenciais fornecidas...")
            email_input = page.locator("input[type='email']")
            if await email_input.count() == 0:
                email_input = page.locator("input[name='email']")
            if await email_input.count() == 0:
                email_input = page.locator("input").first

            await email_input.fill("")
            await email_input.fill("aryarajmarketing@gmail.com")

            password_input = page.locator("input[type='password']")
            await password_input.fill("")
            await password_input.fill("123456")

            # Clicar em Entrar / Login
            login_btn = page.locator("button[type='submit']")
            if await login_btn.count() == 0:
                login_btn = page.locator("button:has-text('Entrar')")
            await login_btn.click()
            await page.wait_for_timeout(3000)

        print("3. Navegando para http://localhost:5300/knowledge-bases?tab=inbox...")
        await page.goto("http://localhost:5300/knowledge-bases?tab=inbox", wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3000)

        # Se não houver perguntas pendentes, verifica
        teach_btn = page.locator(".uq-btn-teach, button:has-text('Ensinar Resposta')").first
        if await teach_btn.count() == 0:
            print("⚠️ Nenhuma dúvida visível na tela. Inserindo uma dúvida teste via API...")
            # Chamada para garantir que exista pelo menos uma dúvida
            await page.evaluate('''async () => {
                try {
                    await fetch('/api/unanswered-questions', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            agent_id: 1,
                            question: 'Qual é a formação do Vinícius Spinoza? Qual é a experiência profissional dele?'
                        })
                    });
                } catch(e) {}
            }''')
            await page.reload()
            await page.wait_for_timeout(3000)
            teach_btn = page.locator(".uq-btn-teach, button:has-text('Ensinar Resposta')").first

        if await teach_btn.count() > 0:
            print("4. Abrindo modal Ensinar Resposta...")
            await teach_btn.click()
            await page.wait_for_timeout(1500)

            # Foto Antes (Modo Nova Pergunta)
            print("5. Capturando Snapshot Antes (Criar Nova Pergunta)...")
            await page.screenshot(path=before_path)
            print(f"Salvo: {before_path}")

            # Alterna para Variacao de Pergunta Existente
            print("6. Clicando em Variacao de Pergunta Existente...")
            variation_btn = page.locator("button:has-text('Variação de Pergunta Existente')")
            if await variation_btn.count() > 0:
                await variation_btn.click()
                await page.wait_for_timeout(2000)

                # Clica no gatilho do SearchableQuestionSelect para abrir para baixo
                trigger = page.locator(".searchable-select-trigger")
                if await trigger.count() > 0:
                    print("6.1. Abrindo dropdown customizado para baixo...")
                    await trigger.click()
                    await page.wait_for_timeout(500)

                    # Digita no campo de busca interno do dropdown para demonstrar o filtro
                    search_input = page.locator(".dropdown-search-input")
                    if await search_input.count() > 0:
                        print("6.2. Digitando filtro 'curso' no dropdown...")
                        await search_input.fill("curso")
                        await page.wait_for_timeout(500)

                # Foto Depois (Modo Variacao com dropdown aberto para baixo)
                print("7. Capturando Snapshot Depois (Modo Variacao com dropdown aberto)...")
                await page.screenshot(path=after_path)
                print(f"Salvo: {after_path}")
            else:
                print("Botao de variacao nao encontrado!")
        else:
            print("Não foi possível encontrar o botão Ensinar Resposta!")
            await page.screenshot(path=after_path)

        await browser.close()
        print("Finalizado com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())
