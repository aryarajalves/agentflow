import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import FollowupPipelineModal from '../../components/WebhookManager/components/FollowupPipelineModal';
import FollowupActionConfirmModal from '../../components/WebhookManager/components/FollowupPipelineModal/FollowupActionConfirmModal';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn()
    }
}));

describe('FollowupPipelineModal Ações Manuais (Disparar Agora & Pular Passo)', () => {
    const mockLead = {
        id: 10,
        contato_nome: 'Aryaraj Alves',
        telefone: '5585996123586',
        followup_step: 0,
        ultima_mensagem_em: '2026-09-23T10:00:00Z',
        labels: ['robo']
    };

    const mockWebhook = {
        id: 113,
        name: 'WhatsApp Teste',
        followup_enabled: true
    };

    const mockPipelineData = {
        lead: mockLead,
        webhook: mockWebhook,
        overall_status: 'active',
        status_message: 'Aguardando disparo do Passo 1',
        steps: [
            {
                step_index: 0,
                step_number: 1,
                delay_minutes: 60,
                type: 'ai',
                custom_prompt: 'Retome a conversa.',
                fixed_message: '',
                status: 'active',
                started_at: '2026-09-23T10:00:00Z',
                estimated_dispatch_at: '2026-09-23T11:00:00Z'
            },
            {
                step_index: 1,
                step_number: 2,
                delay_minutes: 1440,
                type: 'whatsapp_template',
                status: 'pending',
                template_name: 'cartao_recusado'
            }
        ]
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('deve renderizar os botões Disparar Agora e Pular Passo apenas no passo ativo', async () => {
        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => mockPipelineData
        });

        render(<FollowupPipelineModal lead={mockLead} webhook={mockWebhook} onClose={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('Disparar Agora')).toBeInTheDocument();
            expect(screen.getByText('Pular Passo')).toBeInTheDocument();
        });
    });

    it('deve abrir popup de confirmação centralizado ao clicar em Disparar Agora', async () => {
        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => mockPipelineData
        });

        render(<FollowupPipelineModal lead={mockLead} webhook={mockWebhook} onClose={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('Disparar Agora')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Disparar Agora'));

        expect(screen.getByText('Confirmar Disparo Imediato')).toBeInTheDocument();
        expect(screen.getByText(/Tem certeza que deseja/i)).toBeInTheDocument();
    });

    it('deve abrir popup de confirmação centralizado ao clicar em Pular Passo e executar com sucesso', async () => {
        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => mockPipelineData
        });

        api.post.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => ({
                success: true,
                message: 'Passo 1 pulado com sucesso! Contato avançado para o Passo 2.',
                next_step: 1
            })
        });

        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => ({
                ...mockPipelineData,
                steps: [
                    { ...mockPipelineData.steps[0], status: 'completed' },
                    { ...mockPipelineData.steps[1], status: 'active' }
                ]
            })
        });

        render(<FollowupPipelineModal lead={mockLead} webhook={mockWebhook} onClose={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('Pular Passo')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Pular Passo'));

        expect(screen.getByText('Confirmar Pulo de Passo')).toBeInTheDocument();

        // Clica no botão de ação principal do modal
        const confirmBtn = screen.getByTestId('confirm-action-btn');
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith(
                '/webhooks/113/leads/10/followup/skip-step',
                {}
            );
        });
    });

    it('popup FollowupActionConfirmModal não deve fechar ao clicar no backdrop (regra de UX/Design)', () => {
        const onClose = vi.fn();
        render(
            <FollowupActionConfirmModal
                isOpen={true}
                actionType="trigger_now"
                stepNumber={1}
                leadName="Aryaraj"
                loading={false}
                onConfirm={vi.fn()}
                onClose={onClose}
            />
        );

        const backdrop = screen.getByTestId('followup-confirm-backdrop');
        fireEvent.click(backdrop);

        // Não deve ser chamado
        expect(onClose).not.toHaveBeenCalled();

        // Botão cancelar deve fechar
        const cancelBtn = screen.getByRole('button', { name: 'Cancelar' });
        fireEvent.click(cancelBtn);
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('renderiza corretamente o passo com status skipped como "Dispensado" e ícone "⏭"', async () => {
        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => ({
                ...mockPipelineData,
                lead: { ...mockLead, followup_step: 1 },
                steps: [
                    {
                        step_index: 0,
                        step_number: 1,
                        delay_minutes: 60,
                        type: 'ai',
                        status: 'skipped',
                        dispatched_event: {
                            created_at: '2026-09-23T10:00:00Z',
                            agent_response: '[Passo 1 pulado manualmente]'
                        }
                    },
                    {
                        step_index: 1,
                        step_number: 2,
                        delay_minutes: 1440,
                        type: 'whatsapp_template',
                        status: 'active'
                    }
                ]
            })
        });

        render(<FollowupPipelineModal lead={mockLead} webhook={mockWebhook} onClose={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('⏭️ Dispensado')).toBeInTheDocument();
            expect(screen.getByText('⏭️ Passo Dispensado Manualmente')).toBeInTheDocument();
            expect(screen.getByText('⏭')).toBeInTheDocument();
        });
    });

    it('renderiza corretamente o passo disparado manualmente com badge "⚡ Disparado Manualmente"', async () => {
        api.get.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => ({
                ...mockPipelineData,
                lead: { ...mockLead, followup_step: 1 },
                steps: [
                    {
                        step_index: 0,
                        step_number: 1,
                        delay_minutes: 60,
                        type: 'ai',
                        status: 'completed',
                        is_manual: true,
                        dispatched_event: {
                            created_at: '2026-09-23T10:00:00Z',
                            agent_response: 'Olá Aryaraj! Tudo bem?'
                        }
                    },
                    {
                        step_index: 1,
                        step_number: 2,
                        delay_minutes: 1440,
                        type: 'whatsapp_template',
                        status: 'active'
                    }
                ]
            })
        });

        render(<FollowupPipelineModal lead={mockLead} webhook={mockWebhook} onClose={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('⚡ Disparado Manualmente')).toBeInTheDocument();
            expect(screen.getByText('⚡ Disparado Manualmente com Sucesso')).toBeInTheDocument();
        });
    });
});
