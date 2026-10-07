import React from 'react';
import TrainingMetadataSection from './TrainingMetadataSection';

export default function TrainingSetupForm({
    method,
    setMethod,
    showMetadata,
    setShowMetadata,
    metaVideoName,
    setMetaVideoName,
    metaModule,
    setMetaModule,
    metaChapter,
    setMetaChapter,
    metadataVal,
    knowledgeBases,
    selectedKbId,
    setSelectedKbId,
    numQuestions,
    setNumQuestions,
    selectedModel,
    setSelectedModel,
    models,
    chunkSize,
    setChunkSize,
    overlapSize,
    setOverlapSize,
    isGenerating,
    onGenerate
}) {
    const isQaMode = method === 'qa';
    const isChunksMode = method === 'chunks';
    const isBothMode = method === 'both';

    return (
        <div className="training-setup-wrapper">
            {/* Abas de Método */}
            <div className="training-method-tabs" role="tablist">
                <button 
                    role="tab" 
                    aria-selected={isQaMode}
                    className={`training-method-tab${isQaMode ? ' active' : ''}`}
                    onClick={() => setMethod('qa')}
                >
                    <span className="training-tab-icon">🧠</span>
                    <div>
                        <div className="training-tab-title">Perguntas &amp; Respostas</div>
                        <div className="training-tab-desc">Geração com IA</div>
                    </div>
                    {isQaMode && (
                        <span style={{ marginLeft: 'auto', fontSize: '0.7rem', background: 'rgba(168,85,247,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '20px', fontWeight: 700 }}>
                            ATIVO
                        </span>
                    )}
                </button>
                <button 
                    role="tab" 
                    aria-selected={isChunksMode}
                    className={`training-method-tab${isChunksMode ? ' active' : ''}`}
                    onClick={() => setMethod('chunks')}
                >
                    <span className="training-tab-icon">📑</span>
                    <div>
                        <div className="training-tab-title">Trechos (Chunks)</div>
                        <div className="training-tab-desc">Fatiar transcrição</div>
                    </div>
                    {isChunksMode && (
                        <span style={{ marginLeft: 'auto', fontSize: '0.7rem', background: 'rgba(168,85,247,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '20px', fontWeight: 700 }}>
                            ATIVO
                        </span>
                    )}
                </button>
                <button 
                    role="tab" 
                    aria-selected={isBothMode}
                    className={`training-method-tab${isBothMode ? ' active' : ''}`}
                    onClick={() => setMethod('both')}
                >
                    <span className="training-tab-icon">⚡</span>
                    <div>
                        <div className="training-tab-title">Ambos (P&amp;R + Chunks)</div>
                        <div className="training-tab-desc">5 P&amp;R + Chunks da aula</div>
                    </div>
                    {isBothMode && (
                        <span style={{ marginLeft: 'auto', fontSize: '0.7rem', background: 'rgba(168,85,247,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '20px', fontWeight: 700 }}>
                            ATIVO
                        </span>
                    )}
                </button>
            </div>

            {/* Info contextual */}
            <div className="training-info-block">
                {isBothMode ? (
                    <p>O sistema formula <strong style={{ color: '#c084fc' }}>perguntas e respostas didáticas via IA</strong> e simultaneamente fatia o texto em <strong style={{ color: '#60a5fa' }}>trechos (chunks) contínuos</strong>, unindo o melhor dos dois mundos.</p>
                ) : isQaMode ? (
                    <p>A IA lê o texto completo e formula <strong style={{ color: '#c084fc' }}>perguntas e respostas didáticas estruturadas</strong> para treinar o agente com precisão.</p>
                ) : (
                    <p>O texto é dividido em <strong style={{ color: '#60a5fa' }}>trechos sequenciais</strong> e inserido diretamente na base, preservando o conteúdo bruto da transcrição.</p>
                )}
            </div>

            {/* Metadados do Vídeo */}
            <TrainingMetadataSection
                showMetadata={showMetadata}
                setShowMetadata={setShowMetadata}
                metaVideoName={metaVideoName}
                setMetaVideoName={setMetaVideoName}
                metaModule={metaModule}
                setMetaModule={setMetaModule}
                metaChapter={metaChapter}
                setMetaChapter={setMetaChapter}
                metadataVal={metadataVal}
            />

            {/* Base de Conhecimento */}
            <div className="training-form-group">
                <label>Base de Conhecimento de Destino <span>*</span></label>
                <select 
                    value={selectedKbId} 
                    onChange={e => setSelectedKbId(e.target.value)} 
                    className="training-select"
                >
                    <option value="">Selecione uma base...</option>
                    {knowledgeBases.map(kb => (
                        <option key={kb.id} value={kb.id}>{kb.name} ({kb.kb_type === 'qa' ? 'P&R' : 'Texto'})</option>
                    ))}
                </select>
            </div>

            {/* Opções por método */}
            {(isQaMode || isBothMode) && (
                <div className="training-meta-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    <div className="training-form-group">
                        <label>Quantidade de Perguntas</label>
                        <select 
                            value={numQuestions} 
                            onChange={e => setNumQuestions(Number(e.target.value))} 
                            className="training-select" 
                            id="num-questions-select"
                        >
                            <option value={3}>3 Perguntas — Resumido</option>
                            <option value={5}>5 Perguntas — Recomendado</option>
                            <option value={10}>10 Perguntas — Detalhado</option>
                            <option value={15}>15 Perguntas — Máximo</option>
                        </select>
                    </div>
                    <div className="training-form-group">
                        <label>Modelo de IA (Extrator)</label>
                        <select 
                            value={selectedModel} 
                            onChange={e => setSelectedModel(e.target.value)} 
                            className="training-select" 
                            id="model-select"
                        >
                            {models.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.id === 'gpt-5-mini' && 'gpt-5-mini (Recomendado - Rápido e Ultra Moderno 🚀)'}
                                    {m.id === 'gpt-5.2' && 'gpt-5.2 (Alta Qualidade / Próxima Geração 🧠)'}
                                    {m.id === 'gpt-5.4' && 'gpt-5.4 (Fronteira Avançado 👑)'}
                                    {m.id === 'gpt-4o-mini' && 'gpt-4o-mini (Rápido e Econômico ⚡)'}
                                    {m.id === 'gpt-4o' && 'gpt-4o (Alta Qualidade Estável 💎)'}
                                    {m.id === 'gemini-3.1-flash' && 'gemini-3.1-flash (Econômico / Super Rápido ⚡)'}
                                    {m.id === 'gemini-3.1-pro' && 'gemini-3.1-pro (Avançado / Contexto Gigante 🌌)'}
                                    {m.id === 'gemini-1.5-flash' && 'gemini-1.5-flash (Econômico Estável 🟩)'}
                                    {m.id === 'gemini-1.5-pro' && 'gemini-1.5-pro (Avançado Estável 🟪)'}
                                    {m.id === 'claude-4.5-haiku' && 'claude-4.5-haiku (Preciso e Super Rápido ⚡)'}
                                    {m.id === 'claude-4.6-sonnet' && 'claude-4.6-sonnet (Super Equilibrado / Inteligente 💎)'}
                                    {m.id === 'claude-4.6-opus' && 'claude-4.6-opus (Raciocínio Profundo / Frontier 👑)'}
                                    {!['gpt-5-mini', 'gpt-5.2', 'gpt-5.4', 'gpt-4o-mini', 'gpt-4o', 'gemini-3.1-flash', 'gemini-3.1-pro', 'gemini-1.5-flash', 'gemini-1.5-pro', 'claude-4.5-haiku', 'claude-4.6-sonnet', 'claude-4.6-opus'].includes(m.id) && `${m.id} (${m.provider === 'openai' ? 'OpenAI' : m.provider === 'gemini' ? 'Gemini' : 'Claude'})`}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            )}

            {(isChunksMode || isBothMode) && (
                <div className="training-meta-grid" style={{ marginTop: isBothMode ? '1rem' : 0 }}>
                    <div className="training-form-group">
                        <label>Tamanho de Cada Trecho</label>
                        <select 
                            value={chunkSize} 
                            onChange={e => setChunkSize(Number(e.target.value))} 
                            className="training-select" 
                            id="chunk-size-select"
                        >
                            <option value={600}>600 caracteres — Trechos Curtos</option>
                            <option value={1200}>1200 caracteres — Recomendado</option>
                            <option value={2000}>2000 caracteres — Trechos Longos</option>
                            <option value={3000}>3000 caracteres — Máximo</option>
                        </select>
                    </div>
                    <div className="training-form-group">
                        <label>Tamanho da Sobreposição (Overlay)</label>
                        <select 
                            value={overlapSize} 
                            onChange={e => setOverlapSize(Number(e.target.value))} 
                            className="training-select" 
                            id="overlap-size-select"
                        >
                            <option value={50}>50 caracteres — Mínimo</option>
                            <option value={150}>150 caracteres — Recomendado</option>
                            <option value={300}>300 caracteres — Alto</option>
                            <option value={500}>500 caracteres — Máximo</option>
                        </select>
                    </div>
                </div>
            )}

            {/* Botão de Geração */}
            <div className="training-btn-wrapper">
                <button 
                    onClick={onGenerate} 
                    disabled={isGenerating} 
                    className="training-btn-generate" 
                    id="btn-generate-training"
                >
                    {isGenerating ? (
                        <><span className="training-spinner" />{isBothMode ? 'Processando P&R e Chunks...' : isQaMode ? 'Analisando com IA...' : 'Quebrando em Trechos...'}</>
                    ) : (
                        isBothMode ? 'Gerar Ambos (P&R + Chunks) ⚡' : isQaMode ? 'Gerar Perguntas & Respostas com IA 🤖' : 'Gerar Trechos da Transcrição 📑'
                    )}
                </button>
            </div>
        </div>
    );
}
