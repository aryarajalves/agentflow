import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

test('Validação Visual do Modal de Configurações com Abas e API Key', async ({ page }) => {
  // 1. Acessar tela de login
  await page.goto('http://localhost:5300/login');
  
  const emailInput = page.locator('input[type="email"]');
  const passwordInput = page.locator('input[type="password"]');
  
  // Limpar campos antes de preencher (regra obrigatória)
  await emailInput.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  
  await passwordInput.focus();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  
  await emailInput.fill('aryarajmarketing@gmail.com');
  await passwordInput.fill('123456');
  
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
  
  // 2. Abrir Configurações de Perfil
  const settingsBtn = page.locator('.settings-sidebar-btn');
  await expect(settingsBtn).toBeVisible({ timeout: 5000 });
  await settingsBtn.click();
  
  const modalContent = page.locator('.modal-content');
  await expect(modalContent).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(600);

  const artifactDir = 'C:/Users/aryar/.gemini/antigravity/brain/42deded3-ef1a-4f3d-8079-169b4dd58728';
  if (!fs.existsSync(artifactDir)) {
    fs.mkdirSync(artifactDir, { recursive: true });
  }

  // 3. Captura 1: Aba Perfil
  await modalContent.screenshot({
    path: path.join(artifactDir, 'profile_settings_tab_profile.png')
  });

  // 4. Captura 2: Aba White-Label
  const whiteLabelTabBtn = page.getByRole('button', { name: /white-label/i });
  await whiteLabelTabBtn.click();
  await page.waitForTimeout(500);
  await modalContent.screenshot({
    path: path.join(artifactDir, 'profile_settings_tab_whitelabel.png')
  });

  // 5. Captura 3: Aba Chave API
  const apiKeyTabBtn = page.getByRole('button', { name: /chave api/i });
  await apiKeyTabBtn.click();
  await page.waitForTimeout(500);

  // Se houver botão de gerar chave, clica para gerar e mostrar o estado ativo
  const generateBtn = page.getByRole('button', { name: /gerar nova chave de api/i });
  if (await generateBtn.isVisible()) {
    await generateBtn.click();
    await page.waitForTimeout(1200);
  }

  await modalContent.screenshot({
    path: path.join(artifactDir, 'profile_settings_tab_api_key.png')
  });
});
