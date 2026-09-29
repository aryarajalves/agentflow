import React from 'react';

export default function PromptVaultCard({
    prompt,
    onCopy,
    onViewDetails,
    onRestore,
    onDelete,
    onDownload,
}) {
    const isPreDeletion = prompt.backup_type === 'pre_deletion';

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className={`vault-card ${isPreDeletion ? 'card-pre-deletion' : ''}`}>
            <div>
                <div className="vault-card-header">
                    <span className={`vault-badge ${isPreDeletion ? 'vault-badge-pre-deletion' : 'vault-badge-manual'}`}>
                        {isPreDeletion ? '🛡️ Pré-Exclusão' : '💾 Manual'}
                    </span>
                    <span className="vault-card-date">{formatDate(prompt.created_at)}</span>
                </div>

                <h3 className="vault-card-title">{prompt.name}</h3>

                {prompt.source_agent_name && (
                    <div className="vault-card-source">
                        <span>🤖 Agente:</span>
                        <span className="vault-card-source-name">{prompt.source_agent_name}</span>
                    </div>
                )}

                {prompt.description && (
                    <p style={{ fontSize: '13px', color: '#94a3b8', margin: '0 0 10px 0', lineHeight: 1.4 }}>
                        {prompt.description}
                    </p>
                )}

                <div className="vault-card-preview" title="Prévia do System Prompt">
                    {prompt.system_prompt || '(Sem prompt principal)'}
                </div>

                <div className="vault-card-tags-container">
                    <span className="vault-tags-label">Incluso no Pacote:</span>
                    <div className="vault-card-tags">
                        {prompt.system_prompt && (
                            <span className="vault-feature-tag vault-tag-principal">📝 Prompt Principal</span>
                        )}
                        {prompt.pre_router_prompt && (
                            <span className="vault-feature-tag">🧭 Pre-Router</span>
                        )}
                        {prompt.unanswered_question_prompt && (
                            <span className="vault-feature-tag">❓ Dúvidas Sem Resposta</span>
                        )}
                        {prompt.tool_prompts && Object.keys(prompt.tool_prompts).length > 0 && (
                            <span className="vault-feature-tag">🛠️ {Object.keys(prompt.tool_prompts).length} Ferramentas</span>
                        )}
                    </div>
                </div>
            </div>

            <div className="vault-card-actions">
                <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                        className="btn-vault-action"
                        title="Copiar prompt principal para a área de transferência"
                        onClick={() => onCopy(prompt.system_prompt)}
                    >
                        📋 Copiar
                    </button>
                    <button
                        className="btn-vault-action"
                        title="Visualizar pacote de prompts completo"
                        onClick={() => onViewDetails(prompt)}
                    >
                        👁️ Ver
                    </button>
                    <button
                        className="btn-vault-action"
                        title="Baixar arquivo (.json / .txt)"
                        onClick={() => onDownload(prompt)}
                    >
                        📥 Baixar
                    </button>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                        className="btn-vault-action btn-restore"
                        title="Restaurar este prompt em um agente"
                        onClick={() => onRestore(prompt)}
                    >
                        🔄 Restaurar
                    </button>
                    <button
                        className="btn-vault-action btn-delete"
                        title="Excluir este snapshot do cofre"
                        onClick={() => onDelete(prompt)}
                    >
                        🗑️
                    </button>
                </div>
            </div>
        </div>
    );
}
