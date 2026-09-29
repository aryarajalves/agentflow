import React, { useState } from 'react';
import { useQuestions } from '../QuestionsContext';

const InboxHeader = ({ onRefresh }) => {
    const { questions, loading, selectedIds, setSelectedIds, setActiveModal, isLiveConnected } = useQuestions();

    const isAllSelected = questions.length > 0 && questions.every(q => selectedIds.has(q.id));

    const handleSelectAllChange = () => {
        if (isAllSelected) {
            setSelectedIds(new Set());
        } else {
            const newSelected = new Set(selectedIds);
            questions.forEach(q => newSelected.add(q.id));
            setSelectedIds(newSelected);
        }
    };

    return (
        <div className="inbox-header">
            <div className="header-left">
                <div className="header-icon">📥</div>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h3>Inbox de Dúvidas</h3>
                        <span 
                            title={isLiveConnected ? "Conectado ao vivo via WebSocket" : "Conectando ao vivo..."}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.72rem',
                                padding: '2px 8px',
                                borderRadius: '12px',
                                background: isLiveConnected ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                                color: isLiveConnected ? '#4ade80' : '#facc15',
                                border: `1px solid ${isLiveConnected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(234, 179, 8, 0.3)'}`,
                                fontWeight: 500
                            }}
                        >
                            <span style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                backgroundColor: isLiveConnected ? '#22c55e' : '#eab308',
                                boxShadow: isLiveConnected ? '0 0 6px #22c55e' : 'none'
                            }}></span>
                            {isLiveConnected ? 'Ao vivo' : 'Conectando'}
                        </span>
                    </div>
                    <p>{loading ? 'Carregando...' : `${questions.length} pendentes`}</p>
                </div>
            </div>
            
            {questions.length > 0 && (
                <div className="header-select-all">
                    <label className="uq-checkbox-label select-all-label">
                        <input 
                            type="checkbox" 
                            checked={isAllSelected} 
                            onChange={handleSelectAllChange} 
                            className="uq-custom-checkbox"
                        />
                        <span className="checkbox-text">Selecionar Todas</span>
                    </label>
                    {selectedIds.size > 0 && (
                        <span className="selected-count-badge">
                            {selectedIds.size} selecionada{selectedIds.size > 1 ? 's' : ''}
                        </span>
                    )}
                </div>
            )}

            <div className="header-actions">
                {selectedIds.size > 0 && (
                    <button onClick={() => setActiveModal('bulk_discard')} className="btn-bulk-discard">
                        🗑️ Descartar Selecionadas
                    </button>
                )}
                <button onClick={onRefresh} className="btn-refresh-new">
                    <span className="icon">🔄</span> Atualizar
                </button>
            </div>
        </div>
    );
};

export default InboxHeader;
