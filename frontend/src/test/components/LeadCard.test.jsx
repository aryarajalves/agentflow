import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import LeadCard from '../../components/WebhookManager/components/LeadCard';

describe('LeadCard Component', () => {
    const mockLead = {
        id: 101,
        contato_nome: 'Cliente_5511919351515',
        telefone: '5511919351515',
        labels: '["lead_bussola", "robo"]',
        janela_24h_aberta: true,
        total_disparos: 2,
        ultima_mensagem_em: '2026-09-28T10:00:00',
        mensagem: 'Arquivo (unsupported)...',
        created_at: '2026-09-28T09:00:00'
    };

    const defaultProps = {
        lead: mockLead,
        isExpanded: false,
        isSelected: false,
        onToggleExpand: vi.fn(),
        onToggleSelect: vi.fn(),
        onViewHistory: vi.fn(),
        onViewFollowupPipeline: vi.fn(),
        onViewVariables: vi.fn(),
        onDeleteLead: vi.fn(),
        getRemainingTime: () => '20h 39m 23s'
    };

    it('deve renderizar os dados do lead, avatar e botões de ação', () => {
        render(<LeadCard {...defaultProps} />);

        expect(screen.getByText('Cliente_5511919351515')).toBeInTheDocument();
        expect(screen.getByText('5511919351515')).toBeInTheDocument();
        expect(screen.getByText('● Ativa')).toBeInTheDocument();
        expect(screen.getByText(/2 disparos/i)).toBeInTheDocument();
        expect(screen.getByText('🏷️ lead_bussola')).toBeInTheDocument();
        expect(screen.getByText('🏷️ robo')).toBeInTheDocument();

        // Botões de ação
        expect(screen.getByRole('button', { name: /Follow-up/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Variáveis/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Histórico/i })).toBeInTheDocument();
    });

    it('deve posicionar o checkbox de seleção à esquerda e acionar onToggleSelect', () => {
        const onToggleSelect = vi.fn();
        const onToggleExpand = vi.fn();

        render(
            <LeadCard 
                {...defaultProps} 
                onToggleSelect={onToggleSelect} 
                onToggleExpand={onToggleExpand} 
            />
        );

        const checkbox = screen.getByTestId('lead-select-checkbox-101');
        expect(checkbox).toBeInTheDocument();

        fireEvent.click(checkbox);
        expect(onToggleSelect).toHaveBeenCalledWith(101);
        // Não deve propagar para expandir o card
        expect(onToggleExpand).not.toHaveBeenCalled();
    });

    it('deve renderizar checkmark ✓ quando isSelected for true', () => {
        render(<LeadCard {...defaultProps} isSelected={true} />);

        const checkbox = screen.getByTestId('lead-select-checkbox-101');
        expect(checkbox).toHaveTextContent('✓');
    });

    it('deve acionar callbacks dos botões de ação', () => {
        const onViewHistory = vi.fn();
        const onViewFollowupPipeline = vi.fn();
        const onViewVariables = vi.fn();
        const onDeleteLead = vi.fn();

        render(
            <LeadCard 
                {...defaultProps}
                onViewHistory={onViewHistory}
                onViewFollowupPipeline={onViewFollowupPipeline}
                onViewVariables={onViewVariables}
                onDeleteLead={onDeleteLead}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: /Follow-up/i }));
        expect(onViewFollowupPipeline).toHaveBeenCalledWith(mockLead);

        fireEvent.click(screen.getByRole('button', { name: /Variáveis/i }));
        expect(onViewVariables).toHaveBeenCalledWith(mockLead);

        fireEvent.click(screen.getByRole('button', { name: /Histórico/i }));
        expect(onViewHistory).toHaveBeenCalledWith(mockLead);

        const deleteBtn = screen.getByRole('button', { name: '🗑️' });
        fireEvent.click(deleteBtn);
        expect(onDeleteLead).toHaveBeenCalledWith(mockLead);
    });
});
