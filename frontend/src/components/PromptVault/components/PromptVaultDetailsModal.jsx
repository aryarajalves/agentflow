import React, { useState } from 'react';
import PromptFieldEditor from './PromptFieldEditor';

export default function PromptVaultDetailsModal({
    prompt,
    isOpen,
    onClose,
    onCopy,
    onDownload,
}) {
    const [activeTab, setActiveTab] = useState('system');

    if (!isOpen || !prompt) return null;

    const getCurrentContent = () => {
        if (activeTab === 'system') return prompt.system_prompt || '(Sem prompt principal)';
        if (activeTab === 'prerouter') return prompt.pre_router_prompt || '(Sem pre-router prompt)';
        if (activeTab === 'unanswered') return prompt.unanswered_question_prompt || '(Sem diretriz de dúvidas sem resposta)';
        if (activeTab === 'metadata') {
            return JSON.stringify({
                id: prompt.id,
                name: prompt.name,
                source_agent_id: prompt.source_agent_id,
                source_agent_name: prompt.source_agent_name,
                backup_type: prompt.backup_type,
                created_at: prompt.created_at,
                extra_metadata: prompt.extra_metadata || {},
            }, null, 2);
        }
        return '';
    };

    const getTabLabel = () => {
        if (activeTab === 'system') return 'System Prompt Principal';
        if (activeTab === 'prerouter') return 'Prompt do Pre-Router';
        if (activeTab === 'unanswered') return 'Diretrizes de Dúvidas Sem Resposta';
        if (activeTab === 'metadata') return 'Metadados do Backup (JSON)';
        return 'Visualização do Prompt';
    };

    return (
        <div className="vault-modal-overlay">
            <div className="vault-modal-panel" style={{ maxWidth: '820px' }}>
                <div className="vault-modal-header">
                    <h3>
                        <span>📜</span> {prompt.name}
                    </h3>
                    <button className="vault-modal-close-btn" onClick={onClose} title="Fechar">✕</button>
                </div>

                <div className="vault-modal-body">
                    {prompt.description && (
                        <p style={{ margin: '0 0 14px 0', fontSize: '13px', color: '#94a3b8' }}>
                            {prompt.description}
                        </p>
                    )}

                    <div className="vault-detail-tabs">
                        <button
                            className={`vault-detail-tab ${activeTab === 'system' ? 'active' : ''}`}
                            onClick={() => setActiveTab('system')}
                        >
                            🤖 System Prompt
                        </button>
                        <button
                            className={`vault-detail-tab ${activeTab === 'prerouter' ? 'active' : ''}`}
                            onClick={() => setActiveTab('prerouter')}
                        >
                            🧭 Pre-Router
                        </button>
                        <button
                            className={`vault-detail-tab ${activeTab === 'unanswered' ? 'active' : ''}`}
                            onClick={() => setActiveTab('unanswered')}
                        >
                            ❓ Dúvidas Sem Resposta
                        </button>
                        <button
                            className={`vault-detail-tab ${activeTab === 'metadata' ? 'active' : ''}`}
                            onClick={() => setActiveTab('metadata')}
                        >
                            ⚙️ Metadados
                        </button>
                    </div>

                    <div style={{ marginTop: '12px' }}>
                        <PromptFieldEditor
                            key={activeTab}
                            label={getTabLabel()}
                            value={getCurrentContent()}
                            readOnly={true}
                            defaultMasked={true}
                            height="320px"
                        />
                    </div>
                </div>

                <div className="vault-modal-footer">
                    <button
                        className="btn-vault-action"
                        onClick={() => onCopy(getCurrentContent())}
                    >
                        📋 Copiar Conteúdo Desta Aba
                    </button>
                    <button
                        className="btn-vault-action"
                        onClick={() => onDownload(prompt)}
                    >
                        📥 Baixar Pacote Completo
                    </button>
                    <button
                        className="btn-vault-primary"
                        onClick={onClose}
                    >
                        Fechar
                    </button>
                </div>
            </div>
        </div>
    );
}
