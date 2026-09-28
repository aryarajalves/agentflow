import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MaximizedTextModal from '../../components/WebhookManager/components/LeadHistoryModal/components/MaximizedTextModal';

describe('MaximizedTextModal Component', () => {
    it('não deve renderizar quando text for nulo ou vazio', () => {
        const { container } = render(
            <MaximizedTextModal text={null} onClose={vi.fn()} />
        );
        expect(container.firstChild).toBeNull();

        const { container: containerEmpty } = render(
            <MaximizedTextModal text="" onClose={vi.fn()} />
        );
        expect(containerEmpty.firstChild).toBeNull();
    });

    it('deve renderizar o título, o texto fornecido e os botões de fechar', () => {
        const onClose = vi.fn();
        const testText = 'No documento acima tem a mensagem que você recebeu da porta que está aberta, chegou a ler a mensagem?';

        render(
            <MaximizedTextModal text={testText} onClose={onClose} />
        );

        expect(screen.getByText(/Visualização Completa/i)).toBeInTheDocument();
        expect(screen.getByText(testText)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Fechar' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '✕' })).toBeInTheDocument();
    });

    it('deve conter as classes de compactação e altura adaptativa', () => {
        const testText = 'Texto curto de teste';
        render(
            <MaximizedTextModal text={testText} onClose={vi.fn()} />
        );

        const modalContent = screen.getByText(testText).closest('.premium-modal-content');
        expect(modalContent).toBeInTheDocument();
        expect(modalContent).toHaveClass('compact-text-modal');
        expect(modalContent.style.height).toBe('auto');
    });

    it('deve chamar onClose ao clicar no botão Fechar e no botão ✕', () => {
        const onClose = vi.fn();
        render(
            <MaximizedTextModal text="Teste de fechamento" onClose={onClose} />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Fechar' }));
        expect(onClose).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByRole('button', { name: '✕' }));
        expect(onClose).toHaveBeenCalledTimes(2);
    });

    it('não deve propagar o clique para o overlay ao clicar dentro do card do modal', () => {
        const onClose = vi.fn();
        render(
            <MaximizedTextModal text="Teste de stopPropagation" onClose={onClose} />
        );

        const modalContent = screen.getByText('Teste de stopPropagation').closest('.premium-modal-content');
        const clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
        const spiedStopPropagation = vi.spyOn(clickEvent, 'stopPropagation');

        modalContent.dispatchEvent(clickEvent);
        expect(spiedStopPropagation).toHaveBeenCalled();
    });
});
