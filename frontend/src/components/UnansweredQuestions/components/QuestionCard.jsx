import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuestionsActions } from '../hooks/useQuestionsActions';
import { useQuestions } from '../QuestionsContext';

const QuestionCard = ({ question, index }) => {
    const navigate = useNavigate();
    const { openModal } = useQuestionsActions();
    const { selectedIds, setSelectedIds } = useQuestions();

    const isChecked = selectedIds.has(question.id);

    const handleCheckboxChange = () => {
        const newSelected = new Set(selectedIds);
        if (isChecked) {
            newSelected.delete(question.id);
        } else {
            newSelected.add(question.id);
        }
        setSelectedIds(newSelected);
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    };

    const cleanPhoneNumber = (phone) => {
        if (!phone) return '';
        return phone.replace('@s.whatsapp.net', '');
    };

    return (
        <div className={`uq-card ${isChecked ? 'selected' : ''}`} style={{ animationDelay: `${index * 0.06}s` }}>
            <div className="uq-card-meta">
                <label className="uq-checkbox-label">
                    <input 
                        type="checkbox" 
                        checked={isChecked} 
                        onChange={handleCheckboxChange} 
                        className="uq-custom-checkbox"
                    />
                </label>
                <span className="uq-badge">⚠️ Pendente</span>
                {question.source && (
                    <span 
                        className="uq-badge" 
                        style={{
                            background: (question.source === 'chatwoot' || question.source === 'zapvoice' || question.source === 'zapjords') ? 'rgba(99, 102, 241, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                            color: (question.source === 'chatwoot' || question.source === 'zapvoice' || question.source === 'zapjords') ? '#818cf8' : '#34d399',
                            border: '1px solid rgba(255, 255, 255, 0.05)'
                        }}
                    >
                        {(question.source === 'chatwoot' || question.source === 'zapvoice' || question.source === 'zapjords') ? '💬 ZapJords' : '💻 Chat'}
                    </span>
                )}
                {question.session_id && (
                    <span className="uq-phone-tag">
                        📞 {cleanPhoneNumber(question.session_id)}
                        {question.session_id_raw && question.session_id_raw !== question.session_id && (
                            <span style={{ opacity: 0.6, fontSize: '0.62rem', marginLeft: '4px' }}>
                                (ID: {question.session_id_raw})
                            </span>
                        )}
                    </span>
                )}
                {question.chat_session_id && (
                    <span 
                        className="uq-session-tag"
                        title={`ID da sessão: ${question.chat_session_id}`}
                        style={{
                            background: 'rgba(251, 191, 36, 0.12)',
                            color: '#fbbf24',
                            border: '1px solid rgba(251, 191, 36, 0.2)',
                            borderRadius: '6px',
                            padding: '2px 8px',
                            fontSize: '0.7rem',
                            fontFamily: 'monospace',
                            letterSpacing: '0.04em',
                            cursor: 'default'
                        }}
                    >
                        🔑 Sessão: {question.chat_session_id}
                    </span>
                )}
                {question.agent_id && (
                    <span className="uq-agent-tag" title={question.agent_name ? `Agente ID #${question.agent_id}` : undefined}>
                        🤖 {question.agent_name || `Agente #${question.agent_id}`}
                    </span>
                )}
                <span className="uq-date">🕐 {formatDate(question.created_at)}</span>
            </div>

            <div className="uq-question-text">💬 {question.question}</div>

            <div className="uq-actions">
                <button className="uq-btn-teach" onClick={() => openModal(question, 'answer')}>Ensinar Resposta</button>
                <button className="uq-btn-discard" onClick={() => openModal(question, 'discard')}>Descartar</button>
            </div>
        </div>
    );
};

export default QuestionCard;
