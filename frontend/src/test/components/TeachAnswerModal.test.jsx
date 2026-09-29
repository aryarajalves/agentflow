import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TeachAnswerModal from '../../components/UnansweredQuestions/components/TeachAnswerModal';
import { QuestionsProvider } from '../../components/UnansweredQuestions/QuestionsContext';
import * as QuestionsContextModule from '../../components/UnansweredQuestions/QuestionsContext';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn()
    }
}));

describe('TeachAnswerModal', () => {
    const mockQuestion = {
        id: 101,
        question: 'Qual a formação do professor Vinícius?',
        status: 'PENDENTE'
    };

    const mockKbList = [
        { id: 1, name: 'Base Principal' },
        { id: 2, name: 'Base Secundária' }
    ];

    const mockKbDetails = {
        id: 1,
        name: 'Base Principal',
        items: [
            {
                id: 50,
                question: 'Quem é o professor do curso?',
                answer: 'O professor é Vinícius Spinoza, astrólogo renomado.',
                question_variations: ['Quem ministra as aulas?']
            },
            {
                id: 51,
                question: 'Tem certificado?',
                answer: 'Sim, o curso emite certificado oficial.',
                question_variations: Array(8).fill('Var') // Limite atingido
            }
        ]
    };

    const mockContextValue = {
        selectedQuestion: mockQuestion,
        teachMode: 'rag',
        setTeachMode: vi.fn(),
        kbList: mockKbList,
        agents: [{ id: 1, name: 'Agente de Vendas' }],
        selectedKbId: '1',
        setSelectedKbId: vi.fn(),
        selectedAgentId: '1',
        setSelectedAgentId: vi.fn(),
        saving: false,
        setSaving: vi.fn(),
        setQuestions: vi.fn()
    };

    beforeEach(() => {
        vi.clearAllMocks();
        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue(mockContextValue);
        api.get.mockResolvedValue({
            ok: true,
            json: async () => mockKbDetails
        });
    });

    it('deve renderizar o modal com os modos Nova Pergunta e Variação de Existente', async () => {
        render(<TeachAnswerModal onClose={vi.fn()} />);

        expect(screen.getByText('Ensinar Resposta')).toBeInTheDocument();
        expect(screen.getByText('📚 Base (RAG)')).toBeInTheDocument();
        expect(screen.getByText('🤖 Prompt Agente')).toBeInTheDocument();
        expect(screen.getByText('➕ Criar Nova Pergunta')).toBeInTheDocument();
        expect(screen.getByText('🔗 Variação de Pergunta Existente')).toBeInTheDocument();
    });

    it('deve alternar para o modo Variação e exibir preview da pergunta selecionada', async () => {
        render(<TeachAnswerModal onClose={vi.fn()} />);

        // Alterna para Variação de Pergunta Existente
        const variationTab = screen.getByText('🔗 Variação de Pergunta Existente');
        fireEvent.click(variationTab);

        // Deve carregar os itens da base e exibir o preview
        await waitFor(() => {
            expect(screen.getByText(/Resposta Oficial Cadastrada:/i)).toBeInTheDocument();
        });

        expect(screen.getByText('O professor é Vinícius Spinoza, astrólogo renomado.')).toBeInTheDocument();
        expect(screen.getByText(/1\/8 variações/i)).toBeInTheDocument();
        expect(screen.getByDisplayValue('Qual a formação do professor Vinícius?')).toBeInTheDocument();
        expect(screen.getByText('Adicionar Variação')).toBeInTheDocument();
    });

    it('deve submeter a nova variação via POST /answer-as-variation', async () => {
        api.post.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ success: true, message: 'Variação adicionada!' })
        });

        const onClose = vi.fn();
        render(<TeachAnswerModal onClose={onClose} />);

        // Alterna para Variação
        fireEvent.click(screen.getByText('🔗 Variação de Pergunta Existente'));

        await waitFor(() => {
            expect(screen.getByText('Adicionar Variação')).toBeInTheDocument();
        });

        // Clica para adicionar variação
        fireEvent.click(screen.getByText('Adicionar Variação'));

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith(
                '/unanswered-questions/101/answer-as-variation',
                expect.objectContaining({
                    knowledge_item_id: 50,
                    variation: 'Qual a formação do professor Vinícius?'
                })
            );
            expect(onClose).toHaveBeenCalled();
        });
    });

    it('deve desabilitar o botão quando o item já possui 8 variações', async () => {
        render(<TeachAnswerModal onClose={vi.fn()} />);

        fireEvent.click(screen.getByText('🔗 Variação de Pergunta Existente'));

        await waitFor(() => {
            expect(screen.getByText(/Resposta Oficial Cadastrada:/i)).toBeInTheDocument();
        });

        // Seleciona o item 51 (que possui 8 variações)
        const select = screen.getByTestId('select-existing-question');
        fireEvent.change(select, { target: { value: '51' } });

        await waitFor(() => {
            expect(screen.getByText(/8\/8 variações/i)).toBeInTheDocument();
            expect(screen.getByText(/Limite máximo de 8 variações atingido/i)).toBeInTheDocument();
        });

        const submitBtn = screen.getByText('Adicionar Variação');
        expect(submitBtn).toBeDisabled();
    });
});
