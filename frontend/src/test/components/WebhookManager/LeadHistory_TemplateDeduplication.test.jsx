import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useLeadHistoryEvents } from '../../../components/WebhookManager/components/LeadHistoryModal/hooks/useLeadHistoryEvents';
import { api } from '../../../api/client';

vi.mock('../../../api/client', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn()
    }
}));

describe('useLeadHistoryEvents - Deduplicação de Templates', () => {
    it('deve consolidar e ocultar templates duplicados que ocorreram com 7 segundos de diferença', async () => {
        const lead = { telefone: '5585998259497' };
        const webhook = { id: 113 };

        const mockEvents = [
            {
                id: 11729,
                webhook_config_id: 113,
                telefone: '5585998259497',
                dono: 'agente',
                event_type: 'memory',
                message_type: 'template',
                status: 'completed',
                mensagem: 'Olá, Adriana! Tudo bem?\n\nQuis apenas checar se você conseguiu baixar o documento que te enviei mais cedo.',
                agent_response: 'Modo Silencioso (Disparo de Template)',
                created_at: '2026-09-29T13:25:02Z'
            },
            {
                id: 11728,
                webhook_config_id: 113,
                telefone: '5585998259497',
                dono: 'agente',
                event_type: 'message',
                message_type: 'template',
                status: 'completed',
                mensagem: null,
                agent_response: 'Olá, Adriana! Tudo bem?\n\nQuis apenas checar se você conseguiu baixar o documento que te enviei mais cedo.',
                created_at: '2026-09-29T13:24:55Z'
            }
        ];

        api.get.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ items: mockEvents, total: 2 })
        });

        const { result } = renderHook(() => useLeadHistoryEvents(lead, webhook));

        await waitFor(() => {
            expect(result.current.loading).toBe(false);
        });

        // result.current.events contém os 2 registros brutos vindos da API
        expect(result.current.events).toHaveLength(2);

        // result.current.displayEvents deve conter apenas 1 evento consolidado, ocultando o duplicado de 7 segundos
        expect(result.current.displayEvents).toHaveLength(1);
        expect(result.current.displayEvents[0].id).toBe(11729);
    });
});
