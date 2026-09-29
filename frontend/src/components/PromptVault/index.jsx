import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../api/client';
import PromptVaultCard from './components/PromptVaultCard';
import SavePromptModal from './components/SavePromptModal';
import PromptVaultDetailsModal from './components/PromptVaultDetailsModal';
import RestorePromptModal from './components/RestorePromptModal';
import ConfirmModal from '../ConfirmModal';
import './styles/PromptVault.css';

export default function PromptVault() {
    const [prompts, setPrompts] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'manual', 'pre_deletion'

    // Modais
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [selectedDetailsPrompt, setSelectedDetailsPrompt] = useState(null);
    const [selectedRestorePrompt, setSelectedRestorePrompt] = useState(null);
    const [promptToDelete, setPromptToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const showToast = (message, type = 'success') => {
        window.dispatchEvent(new CustomEvent('app:toast', {
            detail: { message, type }
        }));
    };

    const loadPrompts = useCallback(async (isInitial = false) => {
        if (isInitial) {
            setIsLoading(true);
        }
        try {
            const res = await api.get('/prompt-vault?limit=500');
            if (res.ok) {
                const data = await res.json();
                setPrompts(Array.isArray(data) ? data : []);
            } else {
                showToast('Falha ao carregar prompts do cofre.', 'error');
            }
        } catch (err) {
            console.error("Erro ao carregar cofre de prompts:", err);
            showToast('Erro de conexão ao carregar cofre.', 'error');
        } finally {
            if (isInitial) {
                setIsLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        loadPrompts(true);
    }, [loadPrompts]);

    const counts = useMemo(() => {
        const total = prompts.length;
        const manual = prompts.filter(p => p.backup_type === 'manual').length;
        const preDeletion = prompts.filter(p => p.backup_type === 'pre_deletion').length;
        return { total, manual, preDeletion };
    }, [prompts]);

    const filteredPrompts = useMemo(() => {
        const term = searchTerm.trim().toLowerCase();
        return prompts.filter((p) => {
            if (activeFilter === 'manual' && p.backup_type !== 'manual') return false;
            if (activeFilter === 'pre_deletion' && p.backup_type !== 'pre_deletion') return false;

            if (term) {
                const nameMatch = p.name?.toLowerCase().includes(term);
                const agentMatch = p.source_agent_name?.toLowerCase().includes(term);
                const descMatch = p.description?.toLowerCase().includes(term);
                const promptMatch = p.system_prompt?.toLowerCase().includes(term);
                const preRouterMatch = p.pre_router_prompt?.toLowerCase().includes(term);
                return !!(nameMatch || agentMatch || descMatch || promptMatch || preRouterMatch);
            }
            return true;
        });
    }, [prompts, activeFilter, searchTerm]);

    const handleCopy = (text) => {
        if (!text) {
            showToast('Prompt vazio para copiar.', 'warning');
            return;
        }
        navigator.clipboard.writeText(text);
        showToast('📋 Prompt copiado para a área de transferência!');
    };

    const handleDownload = (prompt) => {
        const exportData = {
            name: prompt.name,
            backup_type: prompt.backup_type,
            source_agent_name: prompt.source_agent_name,
            created_at: prompt.created_at,
            system_prompt: prompt.system_prompt,
            dynamic_prompt: prompt.dynamic_prompt,
            pre_router_prompt: prompt.pre_router_prompt,
            unanswered_question_prompt: prompt.unanswered_question_prompt,
            tool_prompts: prompt.tool_prompts,
            extra_metadata: prompt.extra_metadata,
        };

        const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exportData, null, 2))}`;
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', jsonString);
        downloadAnchor.setAttribute('download', `${prompt.name.replace(/[^a-zA-Z0-9_-]/g, '_')}_vault.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();

        showToast('📥 Pacote de prompt baixado com sucesso!');
    };

    const handleDeleteConfirm = async () => {
        if (!promptToDelete) return;
        setIsDeleting(true);
        try {
            const res = await api.delete(`/prompt-vault/${promptToDelete.id}`);
            if (res.ok) {
                showToast('🗑️ Prompt removido do cofre com sucesso.');
                setPrompts((prev) => prev.filter((p) => p.id !== promptToDelete.id));
                setPromptToDelete(null);
            } else {
                const errData = await res.json();
                showToast(errData.detail || 'Erro ao remover do cofre.', 'error');
            }
        } catch (err) {
            console.error("Erro ao deletar:", err);
            showToast('Erro de conexão ao remover prompt.', 'error');
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="prompt-vault-container">
            {/* Header */}
            <div className="prompt-vault-header">
                <div className="prompt-vault-title-area">
                    <h1>
                        <span>🛡️</span> Cofre de Prompts
                    </h1>
                    <p className="prompt-vault-subtitle">
                        Armazenamento seguro e permanente de prompts desacoplado do ciclo de vida dos agentes. Nunca mais perca um prompt por exclusão acidental.
                    </p>
                </div>

                <div className="prompt-vault-header-actions">
                    <button
                        className="btn-vault-primary"
                        onClick={() => setShowSaveModal(true)}
                    >
                        <span>➕</span> Guardar Prompt no Cofre
                    </button>
                </div>
            </div>

            {/* Barra de Filtros e Busca */}
            <div className="vault-controls-bar">
                <div className="vault-type-tabs">
                    <button
                        className={`vault-tab-btn ${activeFilter === 'all' ? 'active' : ''}`}
                        onClick={() => setActiveFilter('all')}
                    >
                        📁 Todos ({counts.total})
                    </button>
                    <button
                        className={`vault-tab-btn ${activeFilter === 'manual' ? 'active' : ''}`}
                        onClick={() => setActiveFilter('manual')}
                    >
                        💾 Manuais ({counts.manual})
                    </button>
                    <button
                        className={`vault-tab-btn ${activeFilter === 'pre_deletion' ? 'active' : ''}`}
                        onClick={() => setActiveFilter('pre_deletion')}
                    >
                        🛡️ Pré-Exclusão ({counts.preDeletion})
                    </button>
                </div>

                <div className="vault-search-box">
                    <span className="vault-search-icon">🔍</span>
                    <input
                        type="text"
                        className="vault-search-input"
                        placeholder="Buscar por nome, agente ou texto do prompt..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Lista de Prompts ou Empty State */}
            {isLoading ? (
                <div style={{ textAlign: 'center', padding: '60px 0', color: '#94a3b8' }}>
                    <div style={{ fontSize: '32px', marginBottom: '12px' }}>⏳</div>
                    <div>Carregando Cofre de Prompts...</div>
                </div>
            ) : filteredPrompts.length === 0 ? (
                <div className="vault-empty-state">
                    <div className="vault-empty-icon">🛡️</div>
                    <div className="vault-empty-title">
                        {activeFilter === 'pre_deletion'
                            ? 'Nenhum backup de pré-exclusão no cofre'
                            : activeFilter === 'manual'
                            ? 'Nenhum prompt manual no cofre'
                            : 'Nenhum prompt encontrado no cofre'}
                    </div>
                    <p className="vault-empty-desc">
                        {searchTerm.trim()
                            ? `Nenhum resultado corresponde à busca "${searchTerm}". Tente outros termos.`
                            : activeFilter === 'pre_deletion'
                            ? 'Backups de pré-exclusão são criados automaticamente sempre que um agente for excluído do sistema.'
                            : 'Você pode salvar prompts manualmente clicando em "Guardar Prompt no Cofre" ou deixar que o sistema salve backups automáticos ao deletar agentes.'}
                    </p>
                    {activeFilter !== 'pre_deletion' && !searchTerm.trim() && (
                        <button
                            className="btn-vault-primary"
                            onClick={() => setShowSaveModal(true)}
                        >
                            ➕ Guardar Primeiro Prompt
                        </button>
                    )}
                    {searchTerm.trim() && (
                        <button
                            className="btn-vault-action"
                            style={{ margin: '10px auto 0 auto', padding: '8px 16px', display: 'inline-flex' }}
                            onClick={() => setSearchTerm('')}
                        >
                            Limpar Busca
                        </button>
                    )}
                </div>
            ) : (
                <div className="vault-grid">
                    {filteredPrompts.map((prompt) => (
                        <PromptVaultCard
                            key={prompt.id}
                            prompt={prompt}
                            onCopy={handleCopy}
                            onViewDetails={(p) => setSelectedDetailsPrompt(p)}
                            onRestore={(p) => setSelectedRestorePrompt(p)}
                            onDelete={(p) => setPromptToDelete(p)}
                            onDownload={handleDownload}
                        />
                    ))}
                </div>
            )}

            {/* Modais */}
            <SavePromptModal
                isOpen={showSaveModal}
                onClose={() => setShowSaveModal(false)}
                onSuccess={(saved) => {
                    showToast(`🛡️ Prompt "${saved.name}" salvo no cofre com sucesso!`);
                    loadPrompts(false);
                }}
            />

            <PromptVaultDetailsModal
                prompt={selectedDetailsPrompt}
                isOpen={!!selectedDetailsPrompt}
                onClose={() => setSelectedDetailsPrompt(null)}
                onCopy={handleCopy}
                onDownload={handleDownload}
            />

            <RestorePromptModal
                prompt={selectedRestorePrompt}
                isOpen={!!selectedRestorePrompt}
                onClose={() => setSelectedRestorePrompt(null)}
                onSuccess={(agent) => {
                    showToast(`🔄 Prompt aplicado com sucesso no agente "${agent.name}"!`);
                }}
            />

            {/* Modal de Confirmação de Exclusão */}
            <ConfirmModal
                isOpen={!!promptToDelete}
                title="Excluir do Cofre de Prompts"
                message={
                    <>
                        Tem certeza que deseja remover o snapshot <strong>{promptToDelete?.name}</strong> do Cofre? Esta ação não pode ser desfeita.
                    </>
                }
                onConfirm={handleDeleteConfirm}
                onCancel={() => setPromptToDelete(null)}
                confirmText="Sim, Remover do Cofre"
                cancelText="Cancelar"
                type="danger"
                isLoading={isDeleting}
            />
        </div>
    );
}
