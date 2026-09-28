import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import LeadsModal from '../../components/WebhookManager/components/LeadsModal';
import { api } from '../../api/client';

// Helper para criar Response mock
const createMockResponse = (data, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(data),
});

vi.mock('../../api/client', () => {
    const mockApi = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    };
    return {
        api: mockApi,
        default: mockApi,
    };
});

describe('LeadsModal Component', () => {
    const mockWebhook = {
        id: 2,
        name: 'Webhook Teste',
    };

    const mockLeads = [
        {
            id: 101,
            telefone: '5511999998888',
            contato_nome: 'Lead Um',
            mensagem: 'Mensagem de teste 1',
            janela_24h_aberta: true,
            is_active: true,
            origem: 'robo',
            canal: 'whatsapp',
            labels: '["lead-quente"]',
            disparos_count: 3,
            created_at: '2026-05-16T12:00:00Z',
        },
        {
            id: 102,
            telefone: '5511999997777',
            contato_nome: 'Lead Dois',
            mensagem: 'Mensagem de teste 2',
            janela_24h_aberta: false,
            is_active: false,
            origem: 'manual',
            canal: 'whatsapp',
            labels: '["lead-frio"]',
            disparos_count: 1,
            created_at: '2026-05-16T12:10:00Z',
        }
    ];

    const defaultProps = {
        leadsModal: {
            webhook: mockWebhook,
            leads: mockLeads,
            total: 2,
            loading: false,
            page: 1,
            pageSize: 20,
            search: '',
            podeEnviar: 'all',
            dateStart: '',
            dateEnd: '',
            janelaAberta: 'all'
        },
        onClose: vi.fn(),
        onSearch: vi.fn(),
        onFilterChange: vi.fn(),
        onPageChange: vi.fn(),
        selectedLeads: new Set(),
        toggleSelectLead: vi.fn(),
        toggleSelectAllLeads: vi.fn(),
        onBulkDelete: vi.fn(),
        onDeleteLead: vi.fn(),
        onSyncAll: vi.fn(),
        isSyncing: false,
        onViewHistory: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        api.get.mockImplementation(() => Promise.resolve(createMockResponse({
            items: [],
            total: 0
        })));
    });

    it('deve renderizar o título do modal e a lista de leads', () => {
        render(<LeadsModal {...defaultProps} />);

        // Verificar o título
        expect(screen.getByText('Contatos Capturados')).toBeInTheDocument();

        // Verificar se os nomes dos leads aparecem
        expect(screen.getByText('Lead Um')).toBeInTheDocument();
        expect(screen.getByText('Lead Dois')).toBeInTheDocument();
        expect(screen.getByText('5511999998888')).toBeInTheDocument();
        expect(screen.getByText('5511999997777')).toBeInTheDocument();
    });

    it('deve chamar toggleSelectLead ao clicar no checkbox de seleção individual do lead', () => {
        const propsComSelecao = {
            ...defaultProps,
            selectedLeads: new Set([101])
        };
        render(<LeadsModal {...propsComSelecao} />);

        // Deve exibir o checkmark '✓' para o Lead 101 selecionado
        const checkmarks = screen.getAllByText('✓');
        expect(checkmarks.length).toBe(1);

        // Ao clicar no checkmark, deve disparar a função toggleSelectLead
        fireEvent.click(checkmarks[0]);
        expect(defaultProps.toggleSelectLead).toHaveBeenCalledWith(101);
    });

    it('deve chamar onViewHistory ao clicar no botão Histórico de um lead', () => {
        render(<LeadsModal {...defaultProps} />);

        const botoesHistorico = screen.getAllByText('Histórico');
        expect(botoesHistorico.length).toBe(2);

        fireEvent.click(botoesHistorico[0]);
        expect(defaultProps.onViewHistory).toHaveBeenCalledWith(mockLeads[0]);
    });

    it('deve chamar onDeleteLead ao clicar no botão de lixeira de um lead', async () => {
        render(<LeadsModal {...defaultProps} />);

        const botoesExcluir = screen.getAllByText('🗑️');
        expect(botoesExcluir.length).toBe(2);

        // Clica no botão de excluir do primeiro lead
        fireEvent.click(botoesExcluir[0]);

        // Deve disparar onDeleteLead com o lead correspondente
        expect(defaultProps.onDeleteLead).toHaveBeenCalledWith(mockLeads[0]);
    });

    it('deve renderizar a busca destacada e abrir filtros avançados ao clicar em Mais Opções', () => {
        render(<LeadsModal {...defaultProps} />);

        // Campo de busca em destaque com placeholder amplo
        expect(screen.getByPlaceholderText('Buscar por nome, número de telefone ou mensagem...')).toBeInTheDocument();
        expect(screen.getByText('🔍 BUSCAR CONTATO')).toBeInTheDocument();
        expect(screen.getByText('🛡️ PERMISSÃO')).toBeInTheDocument();
        expect(screen.getByText('Mais Opções')).toBeInTheDocument();
        expect(screen.getByText('⚡ Filtrar')).toBeInTheDocument();

        // Inicialmente os filtros avançados estão ocultos
        expect(screen.queryByText('⏰ JANELA 24H')).not.toBeInTheDocument();

        // Ao clicar em 'Mais Opções', abre o painel avançado
        fireEvent.click(screen.getByText('Mais Opções'));
        expect(screen.getByText('⏰ JANELA 24H')).toBeInTheDocument();
        expect(screen.getByText('💬 INTERAÇÃO')).toBeInTheDocument();
        expect(screen.getByText('📅 DATA INÍCIO')).toBeInTheDocument();
        expect(screen.getByText('📅 DATA FIM')).toBeInTheDocument();
    });

    it('deve renderizar o botão Excluir Selecionados quando houver contatos selecionados e disparar onBulkDelete', () => {
        const propsComSelecao = {
            ...defaultProps,
            selectedLeads: new Set([1, 2])
        };
        render(<LeadsModal {...propsComSelecao} />);

        expect(screen.getByText('(2 contatos selecionados)')).toBeInTheDocument();
        const btnBulkDelete = screen.getByText('🗑️ Excluir Selecionados');
        expect(btnBulkDelete).toBeInTheDocument();

        fireEvent.click(btnBulkDelete);
        expect(defaultProps.onBulkDelete).toHaveBeenCalledTimes(1);
    });

    it('deve exibir "Sincronizando..." e desabilitar o botão quando isSyncing=true', () => {
        render(<LeadsModal {...defaultProps} isSyncing={true} />);

        const btn = screen.getByText('Sincronizando...');
        expect(btn.closest('button')).toBeDisabled();
    });

    it('deve exibir "Sincronizar Tudo" e habilitar o botão quando isSyncing=false', () => {
        render(<LeadsModal {...defaultProps} isSyncing={false} />);

        const btn = screen.getByText('🔄 Sincronizar Tudo');
        expect(btn.closest('button')).not.toBeDisabled();
    });

    it('deve exibir botão para selecionar todos os contatos quando total for maior que a página atual e chamar onSelectAllTotal ao clicar', () => {
        const onSelectAllTotal = vi.fn();
        const propsComMaisContatos = {
            ...defaultProps,
            leadsModal: {
                ...defaultProps.leadsModal,
                total: 111,
                leads: mockLeads // 2 leads na página
            },
            onSelectAllTotal
        };
        render(<LeadsModal {...propsComMaisContatos} />);

        const btnSelectTotal = screen.getByText(/Selecionar todos os 111 contatos/i);
        expect(btnSelectTotal).toBeInTheDocument();

        fireEvent.click(btnSelectTotal);
        expect(onSelectAllTotal).toHaveBeenCalledTimes(1);
    });

    it('deve exibir aviso de todos selecionados e chamar onClearSelection ao clicar em Desmarcar todos', () => {
        const onClearSelection = vi.fn();
        const fakeIds = Array.from({ length: 111 }, (_, i) => i + 1);
        const propsTodosSelecionados = {
            ...defaultProps,
            leadsModal: {
                ...defaultProps.leadsModal,
                total: 111,
                leads: mockLeads
            },
            selectedLeads: new Set(fakeIds),
            onClearSelection
        };
        render(<LeadsModal {...propsTodosSelecionados} />);

        expect(screen.getByText(/Todos os 111 contatos selecionados/i)).toBeInTheDocument();
        const btnClear = screen.getByText('Desmarcar todos');
        expect(btnClear).toBeInTheDocument();

        fireEvent.click(btnClear);
        expect(onClearSelection).toHaveBeenCalledTimes(1);
    });

    it('deve chamar onSyncAll ao clicar no botão Sincronizar Tudo (quando não estiver sincronizando)', () => {
        const onSyncAll = vi.fn();
        render(<LeadsModal {...defaultProps} onSyncAll={onSyncAll} isSyncing={false} />);

        fireEvent.click(screen.getByText('🔄 Sincronizar Tudo'));
        expect(onSyncAll).toHaveBeenCalledTimes(1);
    });

    it('não deve chamar onClearSelection em re-renderizações após selecionar contatos, chamando apenas ao desmontar o modal', () => {
        const firstClearSelection = vi.fn();
        const secondClearSelection = vi.fn();

        const { rerender, unmount } = render(
            <LeadsModal
                {...defaultProps}
                selectedLeads={new Set()}
                onClearSelection={firstClearSelection}
            />
        );

        // Simula re-render após clicar em "Selecionar Todos" (nova referência de selectedLeads e onClearSelection)
        rerender(
            <LeadsModal
                {...defaultProps}
                selectedLeads={new Set([101, 102])}
                onClearSelection={secondClearSelection}
            />
        );

        // Nenhum dos callbacks de limpeza deve ter sido disparado durante a re-renderização
        expect(firstClearSelection).not.toHaveBeenCalled();
        expect(secondClearSelection).not.toHaveBeenCalled();

        // Ao fechar/desmontar o modal, deve limpar a seleção uma única vez
        unmount();
        expect(secondClearSelection).toHaveBeenCalledTimes(1);
    });
});

