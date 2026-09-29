import React from 'react';
import { QuestionsProvider, useQuestions } from './QuestionsContext';
import { useQuestionsData } from './hooks/useQuestionsData';
import { useQuestionsActions } from './hooks/useQuestionsActions';
import InboxHeader from './components/InboxHeader';
import InboxFilters from './components/InboxFilters';
import QuestionCard from './components/QuestionCard';
import TeachAnswerModal from './components/TeachAnswerModal';
import './styles/UnansweredQuestions.css';
import './styles/UnansweredQuestionsFilters.css';

import { createPortal } from 'react-dom';

const InboxContent = () => {
    const { 
        questions, loading, activeModal, setActiveModal, 
        saving, limit, setLimit, page, setPage, totalCount, selectedIds 
    } = useQuestions();
    const { fetchQuestions } = useQuestionsData();
    const { handleDiscard, handleBulkDiscard } = useQuestionsActions();

    if (loading && questions.length === 0) return <div className="loading-state">Carregando Inbox...</div>;

    const totalPages = Math.ceil(totalCount / limit) || 1;

    const handleOverlayClick = (e) => {
        // NÃO fechar se for modal de deleção (discard / bulk_discard) ao clicar fora
        if (activeModal === 'discard' || activeModal === 'bulk_discard') {
            return;
        }
        setActiveModal(null);
    };

    const renderModals = () => {
        if (!activeModal) return null;

        return createPortal(
            <div className="uq-modal-overlay" onClick={handleOverlayClick}>
                {activeModal === 'answer' && (
                    <TeachAnswerModal onClose={() => setActiveModal(null)} />
                )}

                {activeModal === 'discard' && (
                    <div className="uq-modal" onClick={e => e.stopPropagation()}>
                        <h3>Descartar Dúvida?</h3>
                        <p>Esta ação não pode ser desfeita.</p>
                        <div className="uq-modal-footer">
                            <button onClick={() => setActiveModal(null)}>Cancelar</button>
                            <button onClick={handleDiscard} className="danger" disabled={saving}>
                                {saving ? 'Descartando...' : 'Sim, Descartar'}
                            </button>
                        </div>
                    </div>
                )}

                {activeModal === 'bulk_discard' && (
                    <div className="uq-modal" onClick={e => e.stopPropagation()}>
                        <h3>Descartar dúvidas selecionadas?</h3>
                        <p>Você tem certeza que deseja descartar as {selectedIds.size} dúvidas selecionadas? Esta ação não pode ser desfeita.</p>
                        <div className="uq-modal-footer">
                            <button onClick={() => setActiveModal(null)}>Cancelar</button>
                            <button onClick={handleBulkDiscard} className="danger" disabled={saving}>
                                {saving ? 'Descartando...' : 'Sim, Descartar Todas'}
                            </button>
                        </div>
                    </div>
                )}
            </div>,
            document.body
        );
    };

    return (
        <div className="unanswered-questions-page fade-in">
            <InboxHeader onRefresh={fetchQuestions} />
            <InboxFilters />

            {questions.length === 0 ? (
                <div className="empty-inbox">🎉 Nenhuma dúvida encontrada com os filtros selecionados.</div>
            ) : (
                <>
                    <div className="questions-list">
                        {questions.map((q, idx) => (
                            <QuestionCard key={q.id} question={q} index={idx} />
                        ))}
                    </div>

                    <div className="uq-pagination-container">
                        <div className="uq-pagination-limit">
                            <span className="limit-label">Mostrar:</span>
                            <select 
                                value={limit} 
                                onChange={e => {
                                    setLimit(parseInt(e.target.value));
                                    setPage(1);
                                }}
                                className="uq-pagination-select"
                            >
                                <option value={20}>20 dúvidas</option>
                                <option value={50}>50 dúvidas</option>
                                <option value={100}>100 dúvidas</option>
                            </select>
                        </div>

                        <div className="uq-pagination-navigation">
                            <button 
                                onClick={() => setPage(prev => Math.max(prev - 1, 1))} 
                                disabled={page === 1}
                                className="uq-page-btn"
                            >
                                ◀ Anterior
                            </button>
                            <span className="uq-page-info">
                                Página {page} de {totalPages}
                            </span>
                            <button 
                                onClick={() => setPage(prev => Math.min(prev + 1, totalPages))} 
                                disabled={page === totalPages || questions.length < limit}
                                className="uq-page-btn"
                            >
                                Próxima ▶
                            </button>
                        </div>
                    </div>
                </>
            )}

            {renderModals()}
        </div>
    );
};

const UnansweredQuestions = () => (
    <QuestionsProvider>
        <InboxContent />
    </QuestionsProvider>
);

export default UnansweredQuestions;
