import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import InboxFilters from '../../components/UnansweredQuestions/components/InboxFilters';
import * as QuestionsContextModule from '../../components/UnansweredQuestions/QuestionsContext';

vi.mock('../../components/UnansweredQuestions/QuestionsContext', () => ({
    useQuestions: vi.fn()
}));

describe('InboxFilters Component', () => {
    it('deve renderizar campos de filtro por agente, telefone/contato, origem e datas', () => {
        const mockSetFilterAgentId = vi.fn();
        const mockSetFilterPhone = vi.fn();
        const mockSetFilterSource = vi.fn();
        const mockSetFilterDateStart = vi.fn();
        const mockSetFilterDateEnd = vi.fn();
        const mockSetPage = vi.fn();

        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue({
            agents: [
                { id: 1, name: 'Agente Suporte' },
                { id: 5, name: 'Agente Vendas 7Ps' }
            ],
            filterAgentId: '',
            setFilterAgentId: mockSetFilterAgentId,
            filterPhone: '',
            setFilterPhone: mockSetFilterPhone,
            filterDateStart: '',
            setFilterDateStart: mockSetFilterDateStart,
            filterDateEnd: '',
            setFilterDateEnd: mockSetFilterDateEnd,
            filterSource: '',
            setFilterSource: mockSetFilterSource,
            setPage: mockSetPage
        });

        render(<InboxFilters />);

        expect(screen.getByText('🤖 Agente:')).toBeInTheDocument();
        expect(screen.getByText('📞 Contato / Telefone:')).toBeInTheDocument();
        expect(screen.getByText('💬 Origem:')).toBeInTheDocument();
        expect(screen.getByText('Todos os Agentes')).toBeInTheDocument();
        expect(screen.getByText('Agente Vendas 7Ps')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Ex: 5511999999999')).toBeInTheDocument();
        expect(screen.getByText('Todas as Origens')).toBeInTheDocument();
        expect(screen.getByText('💻 Chat Direto')).toBeInTheDocument();
        expect(screen.getByText('💬 Integração ZapJords')).toBeInTheDocument();
    });

    it('deve permitir alterar filtros e resetar página', () => {
        const mockSetFilterPhone = vi.fn();
        const mockSetPage = vi.fn();

        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue({
            agents: [],
            filterAgentId: '',
            setFilterAgentId: vi.fn(),
            filterPhone: '',
            setFilterPhone: mockSetFilterPhone,
            filterDateStart: '',
            setFilterDateStart: vi.fn(),
            filterDateEnd: '',
            setFilterDateEnd: vi.fn(),
            filterSource: '',
            setFilterSource: vi.fn(),
            setPage: mockSetPage
        });

        render(<InboxFilters />);

        const phoneInput = screen.getByPlaceholderText('Ex: 5511999999999');
        fireEvent.change(phoneInput, { target: { value: '5511888888888' } });

        expect(mockSetFilterPhone).toHaveBeenCalledWith('5511888888888');
        expect(mockSetPage).toHaveBeenCalledWith(1);
    });

    it('deve exibir botão de limpar filtros quando houver filtro ativo e limpá-los ao clicar', () => {
        const mockSetFilterAgentId = vi.fn();
        const mockSetFilterPhone = vi.fn();
        const mockSetFilterSource = vi.fn();
        const mockSetFilterDateStart = vi.fn();
        const mockSetFilterDateEnd = vi.fn();
        const mockSetPage = vi.fn();

        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue({
            agents: [],
            filterAgentId: '5',
            setFilterAgentId: mockSetFilterAgentId,
            filterPhone: '5511999999999',
            setFilterPhone: mockSetFilterPhone,
            filterDateStart: '2026-09-01',
            setFilterDateStart: mockSetFilterDateStart,
            filterDateEnd: '2026-09-30',
            setFilterDateEnd: mockSetFilterDateEnd,
            filterSource: 'zapvoice',
            setFilterSource: mockSetFilterSource,
            setPage: mockSetPage
        });

        render(<InboxFilters />);

        const clearBtn = screen.getByText('🧹 Limpar Filtros');
        expect(clearBtn).toBeInTheDocument();

        fireEvent.click(clearBtn);

        expect(mockSetFilterAgentId).toHaveBeenCalledWith('');
        expect(mockSetFilterPhone).toHaveBeenCalledWith('');
        expect(mockSetFilterSource).toHaveBeenCalledWith('');
        expect(mockSetFilterDateStart).toHaveBeenCalledWith('');
        expect(mockSetFilterDateEnd).toHaveBeenCalledWith('');
        expect(mockSetPage).toHaveBeenCalledWith(1);
    });
});
