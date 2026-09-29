import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SearchableQuestionSelect from '../../components/UnansweredQuestions/components/SearchableQuestionSelect';

describe('SearchableQuestionSelect', () => {
    const mockItems = [
        { id: 1, question: 'Aceita boleto?', answer: 'Não aceitamos boleto.' },
        { id: 2, question: 'Como funciona o curso?', answer: 'O curso é 100% online.' },
        { id: 3, question: 'Qual a formação do professor?', answer: 'O professor é formado em Astrologia.' }
    ];

    it('deve renderizar o gatilho com a pergunta selecionada ou placeholder', () => {
        const { rerender } = render(
            <SearchableQuestionSelect 
                items={mockItems} 
                selectedId="1" 
                onSelect={vi.fn()} 
            />
        );
        expect(screen.getByText('Aceita boleto?')).toBeInTheDocument();

        rerender(
            <SearchableQuestionSelect 
                items={mockItems} 
                selectedId="" 
                placeholder="Selecione uma pergunta..." 
                onSelect={vi.fn()} 
            />
        );
        expect(screen.getByText('Selecione uma pergunta...')).toBeInTheDocument();
    });

    it('deve abrir o menu suspenso para baixo ao clicar e permitir filtrar perguntas', () => {
        render(
            <SearchableQuestionSelect 
                items={mockItems} 
                selectedId="1" 
                onSelect={vi.fn()} 
            />
        );

        // Clica para abrir
        fireEvent.click(screen.getByText('Aceita boleto?'));

        // Campo de busca interno deve aparecer
        const searchInput = screen.getByPlaceholderText('Digite para filtrar perguntas...');
        expect(searchInput).toBeInTheDocument();

        // Digita "formação" no filtro
        fireEvent.change(searchInput, { target: { value: 'formação' } });

        // Apenas o item correspondente deve permanecer visível na lista suspensa
        expect(screen.getByText('Qual a formação do professor?')).toBeInTheDocument();
        expect(screen.queryByText('Como funciona o curso?')).not.toBeInTheDocument();
    });

    it('deve selecionar o item clicado e fechar o menu', () => {
        const onSelect = vi.fn();
        render(
            <SearchableQuestionSelect 
                items={mockItems} 
                selectedId="1" 
                onSelect={onSelect} 
            />
        );

        fireEvent.click(screen.getByText('Aceita boleto?'));

        const itemToClick = screen.getByText('Como funciona o curso?');
        fireEvent.click(itemToClick);

        expect(onSelect).toHaveBeenCalledWith('2');
        // Dropdown deve ter fechado
        expect(screen.queryByPlaceholderText('Digite para filtrar perguntas...')).not.toBeInTheDocument();
    });

    it('deve fechar o dropdown ao pressionar ESC', () => {
        render(
            <SearchableQuestionSelect 
                items={mockItems} 
                selectedId="1" 
                onSelect={vi.fn()} 
            />
        );

        fireEvent.click(screen.getByText('Aceita boleto?'));
        expect(screen.getByPlaceholderText('Digite para filtrar perguntas...')).toBeInTheDocument();

        fireEvent.keyDown(window, { key: 'Escape' });
        expect(screen.queryByPlaceholderText('Digite para filtrar perguntas...')).not.toBeInTheDocument();
    });
});
