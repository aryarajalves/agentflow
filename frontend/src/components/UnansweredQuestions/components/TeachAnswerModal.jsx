import React, { useState, useEffect, useMemo } from 'react';
import { useQuestions } from '../QuestionsContext';
import { api } from '../../../api/client';
import SearchableQuestionSelect from './SearchableQuestionSelect';
import '../styles/TeachAnswerModal.css';

export default function TeachAnswerModal({ onClose }) {
    const { 
        selectedQuestion, teachMode, setTeachMode, 
        kbList, agents, selectedKbId, setSelectedKbId, 
        selectedAgentId, setSelectedAgentId, saving, setSaving, 
        setQuestions 
    } = useQuestions();

    // Sub-modo do RAG: 'new' (Nova Pergunta) ou 'variation' (Variação de Existente)
    const [ragSubMode, setRagSubMode] = useState('new');
    
    // Estados do Modo 'Nova Pergunta'
    const [questionText, setQuestionText] = useState(selectedQuestion?.question || '');
    const [answerText, setAnswerText] = useState('');

    // Estados do Modo 'Variação'
    const [kbItems, setKbItems] = useState([]);
    const [loadingKbItems, setLoadingKbItems] = useState(false);
    const [selectedItemId, setSelectedItemId] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [variationText, setVariationText] = useState(selectedQuestion?.question || '');

    // Carregar itens da Base de Conhecimento selecionada
    useEffect(() => {
        if (!selectedKbId) return;

        let isMounted = true;
        const fetchItems = async () => {
            setLoadingKbItems(true);
            try {
                const res = await api.get(`/knowledge-bases/${selectedKbId}`);
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        const items = data.items || [];
                        setKbItems(items);
                        if (items.length > 0) {
                            setSelectedItemId(prev => {
                                const exists = items.some(i => String(i.id) === String(prev));
                                return exists ? prev : String(items[0].id);
                            });
                        } else {
                            setSelectedItemId('');
                        }
                    }
                }
            } catch (err) {
                console.error("Erro ao carregar itens da base:", err);
            } finally {
                if (isMounted) setLoadingKbItems(false);
            }
        };

        fetchItems();
        return () => { isMounted = false; };
    }, [selectedKbId]);

    // Filtrar perguntas por busca rápida
    const filteredItems = useMemo(() => {
        if (!searchQuery.trim()) return kbItems;
        const q = searchQuery.toLowerCase();
        return kbItems.filter(item => 
            (item.question && item.question.toLowerCase().includes(q)) ||
            (item.answer && item.answer.toLowerCase().includes(q))
        );
    }, [kbItems, searchQuery]);

    // Item de conhecimento selecionado atualmente
    const currentSelectedItem = useMemo(() => {
        return kbItems.find(i => String(i.id) === String(selectedItemId)) || null;
    }, [kbItems, selectedItemId]);

    // Quantidade de variações do item selecionado
    const currentVariations = currentSelectedItem?.question_variations || [];
    const isMaxVariationsReached = currentVariations.length >= 8;

    // Toast helper
    const showToast = (message, type = 'success') => {
        window.dispatchEvent(new CustomEvent('app:toast', { detail: { message, type } }));
    };

    // Submissão do formulário
    const handleSubmit = async () => {
        if (!selectedQuestion) return;

        setSaving(true);
        try {
            if (teachMode === 'agent') {
                const agentId = parseInt(selectedAgentId);
                if (!agentId || isNaN(agentId)) {
                    showToast("Por favor, selecione um agente válido.", "warning");
                    setSaving(false);
                    return;
                }
                if (!answerText.trim()) {
                    showToast("Por favor, preencha a resposta oficial.", "warning");
                    setSaving(false);
                    return;
                }

                const res = await api.post(`/unanswered-questions/${selectedQuestion.id}/answer-to-prompt`, {
                    agent_id: agentId,
                    question: questionText.trim() || selectedQuestion.question,
                    answer: answerText.trim()
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Instrução adicionada ao Prompt do Agente com sucesso!");
                    setQuestions(prev => prev.filter(q => q.id !== selectedQuestion.id));
                    onClose();
                } else {
                    showToast(data.detail || "Erro ao salvar no prompt.", "error");
                }

            } else if (ragSubMode === 'new') {
                // Modo RAG: Nova Pergunta
                const kbId = parseInt(selectedKbId);
                if (!kbId || isNaN(kbId)) {
                    showToast("Por favor, selecione uma base de conhecimento.", "warning");
                    setSaving(false);
                    return;
                }
                if (!answerText.trim()) {
                    showToast("Por favor, preencha a resposta oficial.", "warning");
                    setSaving(false);
                    return;
                }

                const res = await api.post(`/unanswered-questions/${selectedQuestion.id}/answer`, {
                    knowledge_base_id: kbId,
                    question: questionText.trim() || selectedQuestion.question,
                    answer: answerText.trim()
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Pergunta e resposta adicionadas à Base (RAG)!");
                    setQuestions(prev => prev.filter(q => q.id !== selectedQuestion.id));
                    onClose();
                } else {
                    showToast(data.detail || "Erro ao salvar na base.", "error");
                }

            } else {
                // Modo RAG: Variação de Pergunta Existente
                if (!selectedItemId) {
                    showToast("Selecione uma pergunta existente para vincular a variação.", "warning");
                    setSaving(false);
                    return;
                }
                if (!variationText.trim()) {
                    showToast("Preencha o texto da variação.", "warning");
                    setSaving(false);
                    return;
                }
                if (isMaxVariationsReached) {
                    showToast("Este item já atingiu o limite de 8 variações.", "warning");
                    setSaving(false);
                    return;
                }

                const res = await api.post(`/unanswered-questions/${selectedQuestion.id}/answer-as-variation`, {
                    knowledge_item_id: parseInt(selectedItemId),
                    variation: variationText.trim()
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Nova variação vinculada à pergunta existente com sucesso!");
                    setQuestions(prev => prev.filter(q => q.id !== selectedQuestion.id));
                    onClose();
                } else {
                    showToast(data.detail || "Erro ao salvar variação.", "error");
                }
            }
        } catch (e) {
            console.error("Erro ao salvar:", e);
            showToast("Erro ao conectar ao servidor.", "error");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="uq-modal" onClick={e => e.stopPropagation()}>
            <div className="uq-modal-header">
                <h3>Ensinar Resposta</h3>
            </div>

            {/* Abas Principais: RAG vs Prompt Agente */}
            <div className="teach-mode-tabs">
                <button 
                    className={teachMode === 'rag' ? 'active' : ''} 
                    onClick={() => setTeachMode('rag')}
                >
                    📚 Base (RAG)
                </button>
                <button 
                    className={teachMode === 'agent' ? 'active' : ''} 
                    onClick={() => setTeachMode('agent')}
                >
                    🤖 Prompt Agente
                </button>
            </div>

            <div className="modal-body">
                {teachMode === 'rag' && (
                    <>
                        {/* Sub-abas: Nova Pergunta vs Variação de Existente */}
                        <div className="teach-submode-tabs">
                            <button 
                                type="button"
                                className={`teach-submode-btn ${ragSubMode === 'new' ? 'active' : ''}`}
                                onClick={() => setRagSubMode('new')}
                            >
                                ➕ Criar Nova Pergunta
                            </button>
                            <button 
                                type="button"
                                className={`teach-submode-btn ${ragSubMode === 'variation' ? 'active' : ''}`}
                                onClick={() => setRagSubMode('variation')}
                            >
                                🔗 Variação de Pergunta Existente
                            </button>
                        </div>

                        {/* Seletor de Base de Conhecimento */}
                        <label>Base de Conhecimento:</label>
                        <select 
                            data-testid="select-knowledge-base"
                            className="uq-select" 
                            value={selectedKbId} 
                            onChange={e => setSelectedKbId(e.target.value)}
                        >
                            {kbList.length === 0 && <option value="">Carregando bases...</option>}
                            {kbList.map(kb => (
                                <option key={kb.id} value={kb.id}>{kb.name}</option>
                            ))}
                        </select>

                        {ragSubMode === 'new' ? (
                            /* Modo Nova Pergunta */
                            <>
                                <label>Pergunta:</label>
                                <input 
                                    className="uq-input" 
                                    value={questionText} 
                                    onChange={e => setQuestionText(e.target.value)} 
                                    placeholder="Digite a pergunta..."
                                />

                                <label>Resposta Oficial:</label>
                                <textarea 
                                    className="uq-textarea" 
                                    value={answerText} 
                                    onChange={e => setAnswerText(e.target.value)} 
                                    placeholder="Digite a resposta oficial que a IA usará..." 
                                />
                            </>
                        ) : (
                            /* Modo Variação de Pergunta Existente */
                            <>
                                <label>Escolher Pergunta Existente da Base:</label>

                                {kbItems.length === 0 && !loadingKbItems ? (
                                    <div className="no-questions-notice">
                                        ⚠️ Esta base ainda não possui perguntas cadastradas. Crie uma nova pergunta primeiro.
                                    </div>
                                ) : (
                                    <>
                                        <SearchableQuestionSelect 
                                            items={kbItems}
                                            selectedId={selectedItemId}
                                            onSelect={id => setSelectedItemId(id)}
                                            loading={loadingKbItems}
                                            placeholder="Selecione ou busque uma pergunta..."
                                        />
                                        {/* Select oculto para compatibilidade com testes automatizados */}
                                        <select 
                                            data-testid="select-existing-question"
                                            value={selectedItemId}
                                            onChange={e => setSelectedItemId(e.target.value)}
                                            style={{ display: 'none' }}
                                        >
                                            {kbItems.map(item => (
                                                <option key={item.id} value={item.id}>
                                                    {item.question}
                                                </option>
                                            ))}
                                        </select>
                                    </>
                                )}

                                {/* Preview da Pergunta e Resposta Existente */}
                                {currentSelectedItem && (
                                    <div className="existing-qa-preview">
                                        <div className="existing-qa-header">
                                            <span className="existing-qa-label">Resposta Oficial Cadastrada:</span>
                                            <span className={`existing-qa-count ${isMaxVariationsReached ? 'warning' : ''}`}>
                                                {currentVariations.length}/8 variações
                                            </span>
                                        </div>
                                        <div className="existing-qa-answer-box">
                                            {currentSelectedItem.answer}
                                        </div>

                                        {currentVariations.length > 0 && (
                                            <div className="existing-variations-list">
                                                {currentVariations.map((v, i) => (
                                                    <span key={i} className="variation-chip">📌 {v}</span>
                                                ))}
                                            </div>
                                        )}

                                        {isMaxVariationsReached && (
                                            <div className="variation-limit-alert">
                                                ⚠️ Limite máximo de 8 variações atingido para este item.
                                            </div>
                                        )}
                                    </div>
                                )}

                                <label>Nova Variação a Adicionar:</label>
                                <input 
                                    className="uq-input" 
                                    value={variationText} 
                                    onChange={e => setVariationText(e.target.value)} 
                                    placeholder="Texto da nova variação da pergunta..."
                                />
                            </>
                        )}
                    </>
                )}

                {teachMode === 'agent' && (
                    <>
                        <label>Agente:</label>
                        <select 
                            className="uq-select" 
                            value={selectedAgentId} 
                            onChange={e => setSelectedAgentId(e.target.value)}
                        >
                            {agents.length === 0 && <option value="">Carregando agentes...</option>}
                            {agents.map(a => (
                                <option key={a.id} value={a.id}>{a.name}</option>
                            ))}
                        </select>

                        <label>Pergunta:</label>
                        <input 
                            className="uq-input" 
                            value={questionText} 
                            onChange={e => setQuestionText(e.target.value)} 
                        />

                        <label>Resposta Oficial (Será inserida no System Prompt):</label>
                        <textarea 
                            className="uq-textarea" 
                            value={answerText} 
                            onChange={e => setAnswerText(e.target.value)} 
                            placeholder="Resposta oficial..." 
                        />
                    </>
                )}
            </div>

            <div className="uq-modal-footer">
                <button type="button" onClick={onClose} disabled={saving}>Cancelar</button>
                <button 
                    type="button"
                    onClick={handleSubmit} 
                    disabled={saving || (teachMode === 'rag' && ragSubMode === 'variation' && (isMaxVariationsReached || !selectedItemId))}
                >
                    {saving ? 'Salvando...' : (teachMode === 'rag' && ragSubMode === 'variation' ? 'Adicionar Variação' : 'Salvar e Ensinar')}
                </button>
            </div>
        </div>
    );
}
