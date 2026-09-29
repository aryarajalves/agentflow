import React, { useState, useEffect } from 'react';
import { api } from '../../../api/client';
import PromptFieldEditor from './PromptFieldEditor';

export default function SavePromptModal({
    isOpen,
    onClose,
    onSuccess,
}) {
    const [agents, setAgents] = useState([]);
    const [selectedAgentId, setSelectedAgentId] = useState('');
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [systemPrompt, setSystemPrompt] = useState('');
    const [preRouterPrompt, setPreRouterPrompt] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        // Carrega lista de agentes disponíveis
        const loadAgents = async () => {
            try {
                const res = await api.get('/agents');
                if (res.ok) {
                    const data = await res.json();
                    setAgents(Array.isArray(data) ? data : []);
                }
            } catch (err) {
                console.error("Erro ao listar agentes:", err);
            }
        };
        loadAgents();
        // Reseta campos
        setSelectedAgentId('');
        setName('');
        setDescription('');
        setSystemPrompt('');
        setPreRouterPrompt('');
        setErrorMsg('');
    }, [isOpen]);

    const handleSelectAgent = (e) => {
        const agentId = e.target.value;
        setSelectedAgentId(agentId);
        if (!agentId) return;

        const agent = agents.find((a) => String(a.id) === String(agentId));
        if (agent) {
            setName(`Prompt - ${agent.name}`);
            setSystemPrompt(agent.system_prompt || '');
            setPreRouterPrompt(agent.pre_router_prompt || '');
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!name.trim()) {
            setErrorMsg('Por favor, informe um título para o prompt no cofre.');
            return;
        }
        if (!systemPrompt.trim()) {
            setErrorMsg('O prompt principal não pode estar vazio.');
            return;
        }

        setIsSaving(true);
        setErrorMsg('');

        try {
            const payload = {
                name: name.trim(),
                description: description.trim() || null,
                source_agent_id: selectedAgentId ? Number(selectedAgentId) : null,
                backup_type: 'manual',
                system_prompt: systemPrompt,
                pre_router_prompt: preRouterPrompt.trim() ? preRouterPrompt : null,
            };

            const res = await api.post('/prompt-vault', payload);
            if (res.ok) {
                const savedData = await res.json();
                onSuccess(savedData);
                onClose();
            } else {
                const errData = await res.json();
                setErrorMsg(errData.detail || 'Erro ao salvar prompt no cofre.');
            }
        } catch (err) {
            console.error("Erro ao salvar:", err);
            setErrorMsg('Erro de conexão ao salvar prompt.');
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="vault-modal-overlay">
            <div className="vault-modal-panel">
                <div className="vault-modal-header">
                    <h3>🛡️ Guardar Prompt no Cofre</h3>
                    <button className="vault-modal-close-btn" onClick={onClose} title="Fechar">✕</button>
                </div>

                <form onSubmit={handleSave} style={{ display: 'contents' }}>
                    <div className="vault-modal-body">
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
                            <label>Copiar a partir de um Agente Existente (Opcional):</label>
                            <select
                                className="vault-select"
                                value={selectedAgentId}
                                onChange={handleSelectAgent}
                            >
                                <option value="">-- Selecione para preencher automaticamente --</option>
                                {agents.map((ag) => (
                                    <option key={ag.id} value={ag.id}>
                                        🤖 {ag.name} ({ag.model})
                                    </option>
                                ))}
                            </select>
                            <div className="vault-helper-text">
                                Você também pode digitar ou colar um novo prompt livremente abaixo.
                            </div>
                        </div>

                        <div className="vault-form-group">
                            <label>Título do Prompt / Identificador: *</label>
                            <input
                                type="text"
                                className="vault-input"
                                placeholder="Ex: Prompt de Vendas Black Friday 2026"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                            />
                        </div>

                        <div className="vault-form-group">
                            <label>Notas ou Descrição:</label>
                            <input
                                type="text"
                                className="vault-input"
                                placeholder="Ex: Versão otimizada com tom acolhedor e novas regras"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        <PromptFieldEditor
                            label="System Prompt Principal: *"
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            placeholder="Digite ou cole as diretrizes e instruções principais da IA..."
                            required={true}
                            minHeight="140px"
                        />

                        <PromptFieldEditor
                            label="Prompt do Pre-Router (Opcional):"
                            value={preRouterPrompt}
                            onChange={(e) => setPreRouterPrompt(e.target.value)}
                            placeholder="Instruções específicas para a IA de triagem e intenções..."
                            required={false}
                            minHeight="100px"
                        />
                    </div>

                    <div className="vault-modal-footer">
                        <button
                            type="button"
                            className="btn-vault-action"
                            onClick={onClose}
                            disabled={isSaving}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="btn-vault-primary"
                            disabled={isSaving}
                        >
                            {isSaving ? '⏳ Salvando...' : '🛡️ Salvar no Cofre'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
