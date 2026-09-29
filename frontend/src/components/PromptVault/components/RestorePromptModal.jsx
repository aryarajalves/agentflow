import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../../api/client';

export default function RestorePromptModal({
    prompt,
    isOpen,
    onClose,
    onSuccess,
}) {
    const navigate = useNavigate();
    const [agents, setAgents] = useState([]);
    const [targetAgentId, setTargetAgentId] = useState('');
    const [restoreSystemPrompt, setRestoreSystemPrompt] = useState(true);
    const [restorePreRouter, setRestorePreRouter] = useState(true);
    const [restoreUnanswered, setRestoreUnanswered] = useState(true);
    const [isRestoring, setIsRestoring] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        const loadAgents = async () => {
            try {
                const res = await api.get('/agents');
                if (res.ok) {
                    const data = await res.json();
                    setAgents(Array.isArray(data) ? data : []);
                }
            } catch (err) {
                console.error("Erro ao carregar agentes:", err);
            }
        };
        loadAgents();
        setTargetAgentId('');
        setErrorMsg('');
        setRestoreSystemPrompt(true);
        setRestorePreRouter(true);
        setRestoreUnanswered(true);
    }, [isOpen]);

    if (!isOpen || !prompt) return null;

    const handleRestore = async (e) => {
        e.preventDefault();
        if (!targetAgentId) {
            setErrorMsg('Selecione o agente onde você deseja aplicar este prompt.');
            return;
        }

        setIsRestoring(true);
        setErrorMsg('');

        try {
            const payload = {
                target_agent_id: Number(targetAgentId),
                restore_system_prompt: restoreSystemPrompt,
                restore_pre_router: restorePreRouter,
                restore_dynamic: true,
                restore_unanswered: restoreUnanswered,
                restore_tool_prompts: true,
            };

            const res = await api.post(`/prompt-vault/${prompt.id}/restore/${targetAgentId}`, payload);
            if (res.ok) {
                const updatedAgent = await res.json();
                onSuccess(updatedAgent);
                onClose();
            } else {
                const errData = await res.json();
                setErrorMsg(errData.detail || 'Erro ao restaurar prompt no agente.');
            }
        } catch (err) {
            console.error("Erro na restauração:", err);
            setErrorMsg('Erro de rede ao restaurar prompt.');
        } finally {
            setIsRestoring(false);
        }
    };

    const handleCreateNewAgentWithPrompt = () => {
        const baseName = (prompt.name || '')
            .replace('[Backup Pré-Exclusão] ', '')
            .replace(/^Prompt\s*-\s*/i, '')
            .replace(/^Agente\s*-\s*/i, '')
            .trim();
        const suggestedName = baseName ? `Agente - ${baseName}` : 'Novo Agente';

        // Armazena no sessionStorage para o ConfigPanel pré-carregar
        sessionStorage.setItem('prefill_agent_prompt', JSON.stringify({
            name: suggestedName,
            system_prompt: prompt.system_prompt || '',
            pre_router_prompt: prompt.pre_router_prompt || '',
            unanswered_question_prompt: prompt.unanswered_question_prompt || '',
            tool_prompts: prompt.tool_prompts || {},
        }));
        onClose();
        navigate('/agent/new');
    };

    return (
        <div className="vault-modal-overlay">
            <div className="vault-modal-panel">
                <div className="vault-modal-header">
                    <h3>🔄 Restaurar Prompt no Agente</h3>
                    <button className="vault-modal-close-btn" onClick={onClose} title="Fechar">✕</button>
                </div>

                <form onSubmit={handleRestore} style={{ display: 'contents' }}>
                    <div className="vault-modal-body">
                        <div style={{
                            background: 'rgba(56, 189, 248, 0.1)',
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                            padding: '12px 14px',
                            borderRadius: '10px',
                            marginBottom: '18px',
                            fontSize: '13px',
                            color: '#bae6fd',
                            lineHeight: 1.4
                        }}>
                            Você está prestes a restaurar as instruções de <strong>{prompt.name}</strong>.
                        </div>

                        {errorMsg && (
                            <div style={{
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                color: '#fca5a5',
                                padding: '10px 14px',
                                borderRadius: '8px',
                                marginBottom: '16px',
                                fontSize: '13px'
                            }}>
                                ⚠️ {errorMsg}
                            </div>
                        )}

                        <div className="vault-form-group">
                            <label>Escolha o Agente de Destino: *</label>
                            <select
                                className="vault-select"
                                value={targetAgentId}
                                onChange={(e) => setTargetAgentId(e.target.value)}
                                required
                            >
                                <option value="">-- Selecione o agente que receberá este prompt --</option>
                                {agents.map((ag) => (
                                    <option key={ag.id} value={ag.id}>
                                        🤖 {ag.name} ({ag.model})
                                    </option>
                                ))}
                            </select>
                            <div className="vault-helper-text">
                                Atenção: As instruções do agente selecionado serão atualizadas com o conteúdo do cofre.
                            </div>
                        </div>

                        <div className="vault-form-group" style={{ marginTop: '16px' }}>
                            <label style={{ marginBottom: '10px' }}>O que você deseja restaurar?</label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
                                    <input
                                        type="checkbox"
                                        checked={restoreSystemPrompt}
                                        onChange={(e) => setRestoreSystemPrompt(e.target.checked)}
                                    />
                                    <span>System Prompt Principal</span>
                                </label>

                                {prompt.pre_router_prompt && (
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
                                        <input
                                            type="checkbox"
                                            checked={restorePreRouter}
                                            onChange={(e) => setRestorePreRouter(e.target.checked)}
                                        />
                                        <span>Prompt do Pre-Router</span>
                                    </label>
                                )}

                                {prompt.unanswered_question_prompt && (
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
                                        <input
                                            type="checkbox"
                                            checked={restoreUnanswered}
                                            onChange={(e) => setRestoreUnanswered(e.target.checked)}
                                        />
                                        <span>Diretriz de Dúvidas Sem Resposta</span>
                                    </label>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="vault-modal-footer" style={{ justifyContent: 'space-between' }}>
                        <button
                            type="button"
                            className="btn-vault-action"
                            onClick={handleCreateNewAgentWithPrompt}
                            title="Criar um agente do zero já com esse prompt preenchido"
                        >
                            ➕ Criar Novo Agente com este Prompt
                        </button>

                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button
                                type="button"
                                className="btn-vault-action"
                                onClick={onClose}
                                disabled={isRestoring}
                            >
                                Cancelar
                            </button>
                            <button
                                type="submit"
                                className="btn-vault-primary"
                                disabled={isRestoring}
                            >
                                {isRestoring ? '⏳ Restaurando...' : '🚀 Aplicar neste Agente'}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}
