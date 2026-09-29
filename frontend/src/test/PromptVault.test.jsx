import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PromptVault from '../components/PromptVault';
import PromptVaultCard from '../components/PromptVault/components/PromptVaultCard';
import PromptVaultDetailsModal from '../components/PromptVault/components/PromptVaultDetailsModal';
import RestorePromptModal from '../components/PromptVault/components/RestorePromptModal';
import PromptFieldEditor from '../components/PromptVault/components/PromptFieldEditor';

vi.mock('../api/client', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

import { api } from '../api/client';

describe('PromptVault Components', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.get.mockResolvedValue({
            ok: true,
            json: async () => []
        });
    });

    const mockPromptManual = {
        id: 1,
        name: 'Prompt Suporte Vendas',
        description: 'Instruções de atendimento',
        source_agent_name: 'Robô Comercial',
        backup_type: 'manual',
        system_prompt: 'Você é um vendedor consultivo de alta performance.',
        pre_router_prompt: 'Triagem de interesse em cursos.',
        unanswered_question_prompt: 'Vou checar essa informação.',
        tool_prompts: { buscar_faq: 'prompt' },
        created_at: '2026-09-29T10:00:00Z',
    };

    const mockPromptPreDeletion = {
        id: 2,
        name: '[Backup Pré-Exclusão] Agente Deletado',
        description: 'Snapshot automático pré-exclusão',
        source_agent_name: 'Agente Antigo',
        backup_type: 'pre_deletion',
        system_prompt: 'Você era um agente de testes.',
        pre_router_prompt: null,
        created_at: '2026-09-29T10:30:00Z',
    };

    it('renderiza PromptVaultCard manual com dados e badges corretos', () => {
        const onCopy = vi.fn();
        const onViewDetails = vi.fn();
        const onRestore = vi.fn();
        const onDelete = vi.fn();
        const onDownload = vi.fn();

        render(
            <PromptVaultCard
                prompt={mockPromptManual}
                onCopy={onCopy}
                onViewDetails={onViewDetails}
                onRestore={onRestore}
                onDelete={onDelete}
                onDownload={onDownload}
            />
        );

        expect(screen.getByText('Prompt Suporte Vendas')).toBeDefined();
        expect(screen.getByText('💾 Manual')).toBeDefined();
        expect(screen.getByText('Robô Comercial')).toBeDefined();
        expect(screen.getByText('Incluso no Pacote:')).toBeDefined();
        expect(screen.getByText('📝 Prompt Principal')).toBeDefined();
        expect(screen.getByText('🧭 Pre-Router')).toBeDefined();

        // Clique em copiar
        const copyBtn = screen.getByTitle('Copiar prompt principal para a área de transferência');
        fireEvent.click(copyBtn);
        expect(onCopy).toHaveBeenCalledWith(mockPromptManual.system_prompt);

        // Clique em ver detalhes
        const viewBtn = screen.getByTitle('Visualizar pacote de prompts completo');
        fireEvent.click(viewBtn);
        expect(onViewDetails).toHaveBeenCalledWith(mockPromptManual);
    });

    it('renderiza PromptVaultCard pré-exclusão com badge amarelo/alerta', () => {
        render(
            <PromptVaultCard
                prompt={mockPromptPreDeletion}
                onCopy={vi.fn()}
                onViewDetails={vi.fn()}
                onRestore={vi.fn()}
                onDelete={vi.fn()}
                onDownload={vi.fn()}
            />
        );

        expect(screen.getByText('🛡️ Pré-Exclusão')).toBeDefined();
        expect(screen.getByText('[Backup Pré-Exclusão] Agente Deletado')).toBeDefined();
    });

    it('permite alternar abas no PromptVaultDetailsModal', () => {
        const onClose = vi.fn();
        const onCopy = vi.fn();

        render(
            <PromptVaultDetailsModal
                prompt={mockPromptManual}
                isOpen={true}
                onClose={onClose}
                onCopy={onCopy}
                onDownload={vi.fn()}
            />
        );

        expect(screen.getByDisplayValue('Você é um vendedor consultivo de alta performance.')).toBeDefined();
        expect(screen.getAllByText(/linha/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/letras/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/tokens/i).length).toBeGreaterThanOrEqual(1);

        // Clica na aba Pre-Router
        const preRouterTab = screen.getByText('🧭 Pre-Router');
        fireEvent.click(preRouterTab);
        expect(screen.getByDisplayValue('Triagem de interesse em cursos.')).toBeDefined();

        // Clica na aba Dúvidas Sem Resposta
        const unansweredTab = screen.getByText('❓ Dúvidas Sem Resposta');
        fireEvent.click(unansweredTab);
        expect(screen.getByDisplayValue('Vou checar essa informação.')).toBeDefined();
    });

    it('renderiza RestorePromptModal com opções de restauração', async () => {
        render(
            <BrowserRouter>
                <RestorePromptModal
                    prompt={mockPromptManual}
                    isOpen={true}
                    onClose={vi.fn()}
                    onSuccess={vi.fn()}
                />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('🔄 Restaurar Prompt no Agente')).toBeDefined();
        });
        expect(screen.getByText('System Prompt Principal')).toBeDefined();
        expect(screen.getByText('Prompt do Pre-Router')).toBeDefined();
        const createNewBtn = screen.getByText('➕ Criar Novo Agente com este Prompt');
        expect(createNewBtn).toBeDefined();

        // Clica no botão e valida gravação no sessionStorage
        fireEvent.click(createNewBtn);
        const stored = JSON.parse(sessionStorage.getItem('prefill_agent_prompt') || '{}');
        expect(stored.system_prompt).toBe(mockPromptManual.system_prompt);
        expect(stored.pre_router_prompt).toBe(mockPromptManual.pre_router_prompt);
        expect(stored.name).toContain(mockPromptManual.name);
    });

    it('renderiza PromptFieldEditor com linhas, letras, tokens e botão de maximizar', () => {
        const text = "Linha 1\nLinha 2\nLinha 3";
        const onChange = vi.fn();

        render(
            <PromptFieldEditor
                label="System Prompt Principal: *"
                value={text}
                onChange={onChange}
            />
        );

        // Label e botão maximizar
        expect(screen.getByText('System Prompt Principal: *')).toBeDefined();
        expect(screen.getByText('Maximizar')).toBeDefined();

        // Números de linhas (1, 2, 3) e estatística
        expect(screen.getByText('1')).toBeDefined();
        expect(screen.getByText('2')).toBeDefined();
        expect(screen.getAllByText('3').length).toBeGreaterThanOrEqual(1);

        // Estatísticas: 3 linhas, 23 letras
        expect(screen.getAllByText(/linhas/i).length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('23').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText(/letras/i).length).toBeGreaterThanOrEqual(1);

        // Tokens
        expect(screen.getAllByText(/tokens/i).length).toBeGreaterThanOrEqual(1);
    });

    it('abre modal maximizado no centro da tela ao clicar em Maximizar', () => {
        const text = "Conteúdo para maximizar";
        const onChange = vi.fn();

        render(
            <PromptFieldEditor
                label="Prompt do Pre-Router"
                value={text}
                onChange={onChange}
            />
        );

        // Clica no botão Maximizar
        const maxBtn = screen.getByTitle('Maximizar editor em tela grande');
        fireEvent.click(maxBtn);

        // Verifica que o modal maximizado abriu
        expect(screen.getByText(/Modo Tela Cheia/i)).toBeDefined();
        expect(screen.getByText('✅ Concluir Edição')).toBeDefined();

        // Altera texto dentro do modo maximizado
        const textareas = screen.getAllByPlaceholderText('Digite ou cole as diretrizes...');
        const maxTextarea = textareas[textareas.length - 1];
        fireEvent.change(maxTextarea, { target: { value: 'Texto Editado no Maximizado' } });

        // Clica em Concluir Edição
        const confirmBtn = screen.getByText('✅ Concluir Edição');
        fireEvent.click(confirmBtn);

        // Valida que onChange foi chamado com o novo texto
        expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
            target: expect.objectContaining({ value: 'Texto Editado no Maximizado' })
        }));
    });

    it('filtra em memória sem recarregar ou piscar a tela ao alternar abas', async () => {
        api.get.mockResolvedValue({
            ok: true,
            json: async () => [mockPromptManual, mockPromptPreDeletion]
        });

        render(
            <BrowserRouter>
                <PromptVault />
            </BrowserRouter>
        );

        // Aguarda carregar dados iniciais
        await waitFor(() => {
            expect(screen.getByText('Prompt Suporte Vendas')).toBeDefined();
            expect(screen.getByText('[Backup Pré-Exclusão] Agente Deletado')).toBeDefined();
        });

        // Contagens iniciais
        expect(screen.getByText('📁 Todos (2)')).toBeDefined();
        expect(screen.getByText('💾 Manuais (1)')).toBeDefined();
        expect(screen.getByText('🛡️ Pré-Exclusão (1)')).toBeDefined();

        // Limpa chamadas de api.get para provar que a troca de abas NÃO faz nova requisição de rede
        api.get.mockClear();

        // Clica na aba Manuais
        fireEvent.click(screen.getByText('💾 Manuais (1)'));

        // Verifica que apenas o manual está visível e pré-exclusão sumiu
        expect(screen.getByText('Prompt Suporte Vendas')).toBeDefined();
        expect(screen.queryByText('[Backup Pré-Exclusão] Agente Deletado')).toBeNull();
        // Prova que NÃO houve nova chamada de rede (zero piscada)
        expect(api.get).not.toHaveBeenCalled();

        // Clica na aba Pré-Exclusão
        fireEvent.click(screen.getByText('🛡️ Pré-Exclusão (1)'));

        // Verifica que agora apenas pré-exclusão está visível
        expect(screen.queryByText('Prompt Suporte Vendas')).toBeNull();
        expect(screen.getByText('[Backup Pré-Exclusão] Agente Deletado')).toBeDefined();
        expect(api.get).not.toHaveBeenCalled();

        // Clica de volta em Todos
        fireEvent.click(screen.getByText('📁 Todos (2)'));
        expect(screen.getByText('Prompt Suporte Vendas')).toBeDefined();
        expect(screen.getByText('[Backup Pré-Exclusão] Agente Deletado')).toBeDefined();
        expect(api.get).not.toHaveBeenCalled();
    });

    it('aplica máscara para cobrir boa parte do prompt longo e permite revelar/mascarar', () => {
        const longPrompt = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5\nLinha 6\nLinha 7\nLinha 8";

        render(
            <PromptFieldEditor
                label="Prompt com Máscara"
                value={longPrompt}
                defaultMasked={true}
                readOnly={true}
            />
        );

        // Deve exibir o botão de revelar na máscara
        const revealBtn = screen.getByText(/Revelar Prompt Completo/i);
        expect(revealBtn).toBeDefined();
        expect(screen.getByText(/Prévia protegida/i)).toBeDefined();

        // Clica para revelar o prompt completo
        fireEvent.click(revealBtn);

        // A máscara deve sumir e o botão de Mascarar deve estar disponível no topo
        expect(screen.queryByText(/Revelar Prompt Completo/i)).toBeNull();
        const maskToggleBtn = screen.getByText('🔒 Mascarar');
        expect(maskToggleBtn).toBeDefined();

        // Clica em Mascarar novamente
        fireEvent.click(maskToggleBtn);

        // A máscara volta a cobrir o prompt
        expect(screen.getByText(/Revelar Prompt Completo/i)).toBeDefined();
    });

    it('permite alternar entre quebra de linhas automática e modo linha a linha (IDE)', () => {
        const text = "Linha com texto bem longo que poderia quebrar visualmente";

        render(
            <PromptFieldEditor
                label="Prompt Wrap Test"
                value={text}
            />
        );

        const wrapBtn = screen.getByText('↩️ Quebra: Ligada');
        expect(wrapBtn).toBeDefined();

        // Clica para desligar quebra de linhas
        fireEvent.click(wrapBtn);
        expect(screen.getByText('➡️ Quebra: Desligada')).toBeDefined();

        // Clica para religar quebra de linhas
        fireEvent.click(screen.getByText('➡️ Quebra: Desligada'));
        expect(screen.getByText('↩️ Quebra: Ligada')).toBeDefined();
    });
});

