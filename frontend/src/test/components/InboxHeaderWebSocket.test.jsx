import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import InboxHeader from '../../components/UnansweredQuestions/components/InboxHeader';
import * as QuestionsContextModule from '../../components/UnansweredQuestions/QuestionsContext';

vi.mock('../../components/UnansweredQuestions/QuestionsContext', () => ({
    useQuestions: vi.fn()
}));

describe('InboxHeader Component', () => {
    it('deve exibir o badge "Ao vivo" quando o WebSocket estiver conectado', () => {
        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue({
            questions: [{ id: 1, question: 'Teste?' }],
            loading: false,
            selectedIds: new Set(),
            setSelectedIds: vi.fn(),
            setActiveModal: vi.fn(),
            isLiveConnected: true
        });

        render(<InboxHeader onRefresh={vi.fn()} />);

        expect(screen.getByText('Ao vivo')).toBeInTheDocument();
        expect(screen.getByText('1 pendentes')).toBeInTheDocument();
    });

    it('deve exibir "Conectando" quando isLiveConnected for false', () => {
        vi.spyOn(QuestionsContextModule, 'useQuestions').mockReturnValue({
            questions: [],
            loading: false,
            selectedIds: new Set(),
            setSelectedIds: vi.fn(),
            setActiveModal: vi.fn(),
            isLiveConnected: false
        });

        render(<InboxHeader onRefresh={vi.fn()} />);

        expect(screen.getByText('Conectando')).toBeInTheDocument();
    });
});
