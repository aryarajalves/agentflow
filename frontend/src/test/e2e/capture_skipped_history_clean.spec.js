import { test, expect } from '@playwright/test';

test('Validação de que passos de follow-up pulados não aparecem no histórico de conversas do contato', async ({ page }) => {
  test.setTimeout(60000);

  // 1. Ir para a página de login
  await page.goto('http://localhost:5300/login');
  
  // 2. Limpar os campos obrigatoriamente antes de preencher
  const emailInput = page.locator('input[type="email"]');
  const passwordInput = page.locator('input[type="password"]');
  
  await emailInput.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  
  await passwordInput.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  
  // 3. Preencher credenciais corretas
  await emailInput.fill('aryarajmarketing@gmail.com');
  await passwordInput.fill('123456');
  
  // 4. Logar
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('http://localhost:5300/');
  
  // 5. Ir para /integrations
  await page.goto('http://localhost:5300/integrations');
  await page.waitForTimeout(1500);

  // Clicar em "Configurar Webhooks"
  const configBtn = page.locator('button:has-text("Configurar Webhooks")');
  await expect(configBtn).toBeVisible({ timeout: 10000 });
  await configBtn.click();
  await page.waitForTimeout(1500);

  // 6. Clicar no botão "Contatos" do webhook
  const contatosBtn = page.locator('button:has-text("Contatos")').first();
  await expect(contatosBtn).toBeVisible({ timeout: 10000 });
  await contatosBtn.click();
  await page.waitForTimeout(2000);

  // 7. Localizar o card do lead e clicar no botão "Histórico"
  const leadCard = page.locator('.lead-card-premium').first();
  await expect(leadCard).toBeVisible({ timeout: 10000 });
  
  // Clica no botão "Histórico" (ou ícone de histórico) dentro do card
  const historyBtn = leadCard.locator('button:has-text("Histórico"), button[title*="Histórico"]').first();
  if (await historyBtn.isVisible()) {
    await historyBtn.click();
  } else {
    // Tenta clicar pelo texto ou no próprio card para expandir
    await leadCard.click();
    await page.waitForTimeout(500);
    const subHistoryBtn = page.locator('button:has-text("Histórico")').first();
    await subHistoryBtn.click();
  }

  // 8. Aguardar o modal "Histórico" carregar
  await page.waitForTimeout(3000);
  
  // Valida que o modal de Histórico está visível
  const historyModal = page.locator('text=Histórico').first();
  await expect(historyModal).toBeVisible();

  // Garante que o texto de passo pulado NÃO está na tela
  const skippedText = page.locator('text=pulado manualmente');
  await expect(skippedText).toHaveCount(0);

  // 9. Tirar screenshot e salvar nos artefatos
  const screenshotPath = 'C:/Users/aryar/.gemini/antigravity/brain/a0464bf1-893c-4a12-a477-72e6ed1b04b3/historico_contato_limpo_sem_skipped.png';
  await page.screenshot({ 
    path: screenshotPath,
    fullPage: true 
  });
  
  console.log(`✅ Prova visual capturada em: ${screenshotPath}`);
});
