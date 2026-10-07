import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import React from 'react';
import TranscriptionHistory from '../../components/TranscriptionHistory';

vi.mock('../../api/client', () => ({
    api: {
        get: vi.fn(() => Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ tasks: [], total: 0 })
        })),
        post: vi.fn(() => Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true })
        })),
        put: vi.fn(() => Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true })
        })),
    }
}));

describe('TrainingModal - Modo Ambos (P&R + Chunks)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it('deve gerar simultaneamente Perguntas & Respostas e Chunks no modo Ambos', async () => {
        const { api } = await import('../../api/client');

        api.get.mockImplementation((url) => {
            if (url.includes('/transcription-folders')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
            }
            if (url.includes('/knowledge-bases')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([
                        { id: 10, name: 'Base Principal', kb_type: 'qa' }
                    ])
                });
            }
            if (url.includes('/transcription-tasks')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        tasks: [
                            {
                                id: 1,
                                filename: 'aula_completa.mp4',
                                status: 'SUCCESS',
                                duration: 120,
                                tokens: 500,
                                cost_usd: 0.01,
                                created_at: '2026-03-01T12:00:00Z',
                                result_text: 'Esta é uma aula completa com conteúdo rico e didático para teste.'
                            }
                        ],
                        total: 1
                    })
                });
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        });

        await act(async () => {
            render(<TranscriptionHistory />);
        });

        // Clicar no botão Treinamento com IA
        const trainButton = screen.getByTitle('Treinamento com IA');
        expect(trainButton).toBeInTheDocument();

        await act(async () => {
            fireEvent.click(trainButton);
        });

        // Verificar se a aba Ambos está presente e clicar nela
        const bothTab = screen.getByText(/Ambos \(P&R \+ Chunks\)/i);
        expect(bothTab).toBeInTheDocument();

        fireEvent.click(bothTab);

        // Selecionar base com id 10
        const kbSelect = screen.getByDisplayValue('Selecione uma base...');
        fireEvent.change(kbSelect, { target: { value: '10' } });

        // Mock dos endpoints de geração
        api.post.mockImplementation((url) => {
            if (url.includes('/generate-qa-from-transcription')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([
                        { pergunta: 'Qual é o foco da aula?', resposta: 'O foco é automação inteligente.', categoria: 'Treinamento' }
                    ])
                });
            }
            if (url.includes('/generate-chunks-from-transcription')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([
                        { question: 'Trecho da Aula #1', answer: 'Esta é uma aula completa com conteúdo rico.', category: 'Transcrição' }
                    ])
                });
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        });

        const generateBtn = screen.getByText(/Gerar Ambos \(P&R \+ Chunks\)/i);
        await act(async () => {
            fireEvent.click(generateBtn);
        });

        // Valida que ambos os endpoints foram chamados
        expect(api.post).toHaveBeenCalledWith(
            expect.stringContaining('/generate-qa-from-transcription'),
            expect.anything()
        );
        expect(api.post).toHaveBeenCalledWith(
            expect.stringContaining('/generate-chunks-from-transcription'),
            expect.anything()
        );

        // Valida que tanto a pergunta quanto o chunk aparecem na lista de cards gerados
        expect(screen.getByDisplayValue('Qual é o foco da aula?')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Trecho da Aula #1')).toBeInTheDocument();
        expect(screen.getByDisplayValue('O foco é automação inteligente.')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Esta é uma aula completa com conteúdo rico.')).toBeInTheDocument();
    });
});
