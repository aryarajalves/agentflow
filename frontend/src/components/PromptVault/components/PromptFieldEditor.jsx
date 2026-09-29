import React, { useState, useRef, useEffect } from 'react';
import '../styles/PromptFieldEditor.css';

export default function PromptFieldEditor({
    label,
    value = '',
    onChange = () => {},
    placeholder = 'Digite ou cole as diretrizes...',
    required = false,
    minHeight = '140px',
    maxHeight,
    height,
    readOnly = false,
    defaultMasked = false,
}) {
    const isMaskable = Boolean(value && (value.split('\n').length > 3 || value.length > 140));
    const [isMasked, setIsMasked] = useState(defaultMasked && isMaskable);
    const [wordWrap, setWordWrap] = useState(true);
    const [isMaximized, setIsMaximized] = useState(false);
    const [tempValue, setTempValue] = useState(value);

    const normalTextareaRef = useRef(null);
    const normalGutterRef = useRef(null);
    const maxTextareaRef = useRef(null);
    const maxGutterRef = useRef(null);

    // Sincroniza tempValue quando o valor externo mudar
    useEffect(() => {
        setTempValue(value || '');
    }, [value]);

    // Reseta máscara se defaultMasked estiver ativo
    useEffect(() => {
        if (defaultMasked && isMaskable) {
            setIsMasked(true);
        }
    }, [defaultMasked, isMaskable]);

    // Cálculo de estatísticas
    const calculateStats = (text = '') => {
        const charCount = text.length;
        const lineCount = text ? text.split('\n').length : 1;
        // Estimativa padrão de tokens: ~3.8 a 4 caracteres por token em pt-BR
        const tokenCount = charCount > 0 ? Math.ceil(charCount / 3.8) : 0;
        return { charCount, lineCount, tokenCount };
    };

    const stats = calculateStats(value);
    const maxStats = calculateStats(tempValue);

    // Sincroniza scroll proporcionalmente entre textarea e gutter de números de linha
    const handleScroll = (textarea, gutter) => {
        if (textarea && gutter) {
            const textareaMaxScroll = textarea.scrollHeight - textarea.clientHeight;
            const gutterMaxScroll = gutter.scrollHeight - gutter.clientHeight;
            if (textareaMaxScroll > 0 && gutterMaxScroll > 0) {
                const ratio = textarea.scrollTop / textareaMaxScroll;
                gutter.scrollTop = ratio * gutterMaxScroll;
            } else {
                gutter.scrollTop = textarea.scrollTop;
            }
        }
    };

    // Gera array de números de linha
    const renderLineNumbers = (lineCount) => {
        const numbers = [];
        for (let i = 1; i <= Math.max(lineCount, 1); i++) {
            numbers.push(
                <div key={i} className="prompt-editor-line-number">
                    {i}
                </div>
            );
        }
        return numbers;
    };

    const handleOpenMaximized = () => {
        setTempValue(value || '');
        setIsMaximized(true);
    };

    const handleConfirmMaximized = () => {
        onChange({ target: { value: tempValue } });
        setIsMaximized(false);
    };

    const handleCancelMaximized = () => {
        setTempValue(value || '');
        setIsMaximized(false);
    };

    return (
        <div className="prompt-field-editor-container">
            {/* Cabeçalho do Campo com Estatísticas, Toggle de Máscara e Maximizar */}
            <div className="prompt-field-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <label className="prompt-field-label">
                        {label}
                    </label>
                    <div className="prompt-editor-header-stats">
                        <span className="prompt-stat-badge">🔢 {stats.lineCount} {stats.lineCount === 1 ? 'linha' : 'linhas'}</span>
                        <span className="prompt-stat-badge">🔤 {stats.charCount.toLocaleString('pt-BR')} letras</span>
                        <span className="prompt-stat-badge prompt-stat-badge-tokens" title="Estimativa aproximada de consumo de tokens">⚡ ~{stats.tokenCount.toLocaleString('pt-BR')} tokens</span>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                        type="button"
                        className={`btn-toggle-wrap-header ${wordWrap ? 'active' : ''}`}
                        onClick={() => setWordWrap(!wordWrap)}
                        title={wordWrap ? 'Desativar quebra de linhas (Modo IDE)' : 'Ativar quebra automática de linhas'}
                    >
                        {wordWrap ? '↩️ Quebra: Ligada' : '➡️ Quebra: Desligada'}
                    </button>
                    {isMaskable && (
                        <button
                            type="button"
                            className="btn-toggle-mask-header"
                            onClick={() => setIsMasked(!isMasked)}
                            title={isMasked ? 'Revelar prompt completo' : 'Cobrir com máscara'}
                        >
                            {isMasked ? '👁️ Revelar' : '🔒 Mascarar'}
                        </button>
                    )}
                    <button
                        type="button"
                        className="btn-maximize-field"
                        onClick={handleOpenMaximized}
                        title="Maximizar editor em tela grande"
                    >
                        <span>⛶</span> Maximizar
                    </button>
                </div>
            </div>

            {/* Editor Normal com Gutter e Máscara Opcional */}
            <div
                className={`prompt-editor-box ${isMasked && isMaskable ? 'is-masked' : ''}`}
                style={{
                    minHeight: isMasked && isMaskable ? '170px' : minHeight,
                    maxHeight: isMasked && isMaskable ? '170px' : maxHeight,
                    height: isMasked && isMaskable ? '170px' : height,
                }}
            >
                <div
                    ref={normalGutterRef}
                    className="prompt-editor-gutter"
                    aria-hidden="true"
                >
                    {renderLineNumbers(stats.lineCount)}
                </div>
                <textarea
                    ref={normalTextareaRef}
                    className={`prompt-editor-textarea ${!wordWrap ? 'nowrap' : ''}`}
                    placeholder={placeholder}
                    value={value}
                    onChange={readOnly ? undefined : onChange}
                    readOnly={readOnly}
                    required={required}
                    onScroll={() => handleScroll(normalTextareaRef.current, normalGutterRef.current)}
                />

                {isMasked && isMaskable && (
                    <div className="prompt-editor-mask-overlay">
                        <button
                            type="button"
                            className="btn-reveal-prompt"
                            onClick={() => setIsMasked(false)}
                            title="Revelar todo o prompt na tela"
                        >
                            <span>👁️</span> Revelar Prompt Completo ({stats.lineCount} {stats.lineCount === 1 ? 'linha' : 'linhas'})
                        </button>
                        <span className="prompt-mask-hint">
                            Prévia protegida • Clique para expandir ou use <strong>Maximizar ⛶</strong>
                        </span>
                    </div>
                )}
            </div>

            {/* Barra de Estatísticas Inferior */}
            <div className="prompt-editor-footer-stats">
                <span className="prompt-stat-item">
                    🔢 <strong>{stats.lineCount}</strong> {stats.lineCount === 1 ? 'linha' : 'linhas'}
                </span>
                <span className="prompt-stat-separator">•</span>
                <span className="prompt-stat-item">
                    🔤 <strong>{stats.charCount.toLocaleString('pt-BR')}</strong> {stats.charCount === 1 ? 'letra' : 'letras'}
                </span>
                <span className="prompt-stat-separator">•</span>
                <span className="prompt-stat-item prompt-stat-tokens" title="Estimativa aproximada para modelos OpenAI/Anthropic">
                    ⚡ ~<strong>{stats.tokenCount.toLocaleString('pt-BR')}</strong> tokens
                </span>
            </div>

            {/* POPUP GRANDE CENTRALIZADO (MAXIMIZADO) */}
            {isMaximized && (
                <div className="vault-modal-overlay prompt-max-overlay">
                    <div className="vault-modal-panel prompt-max-panel">
                        <div className="vault-modal-header prompt-max-header">
                            <h3>
                                <span>⛶</span> {label.replace('*', '').trim()} (Modo Tela Cheia)
                            </h3>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <button
                                    type="button"
                                    className={`btn-toggle-wrap-header ${wordWrap ? 'active' : ''}`}
                                    onClick={() => setWordWrap(!wordWrap)}
                                    title={wordWrap ? 'Desativar quebra de linhas (Modo IDE)' : 'Ativar quebra automática de linhas'}
                                >
                                    {wordWrap ? '↩️ Quebra: Ligada' : '➡️ Quebra: Desligada'}
                                </button>
                                <button
                                    type="button"
                                    className="vault-modal-close-btn"
                                    onClick={handleCancelMaximized}
                                    title="Fechar modo expandido"
                                >
                                    ✕
                                </button>
                            </div>
                        </div>

                        <div className="prompt-max-body">
                            <div className="prompt-editor-box prompt-editor-box-max">
                                <div
                                    ref={maxGutterRef}
                                    className="prompt-editor-gutter prompt-editor-gutter-max"
                                    aria-hidden="true"
                                >
                                    {renderLineNumbers(maxStats.lineCount)}
                                </div>
                                <textarea
                                    ref={maxTextareaRef}
                                    className={`prompt-editor-textarea prompt-editor-textarea-max ${!wordWrap ? 'nowrap' : ''}`}
                                    placeholder={placeholder}
                                    value={tempValue}
                                    onChange={readOnly ? undefined : (e) => setTempValue(e.target.value)}
                                    readOnly={readOnly}
                                    autoFocus
                                    onScroll={() => handleScroll(maxTextareaRef.current, maxGutterRef.current)}
                                />
                            </div>
                        </div>

                        <div className="vault-modal-footer prompt-max-footer">
                            {/* Estatísticas no Rodapé do Popup Grande */}
                            <div className="prompt-max-footer-stats">
                                <span className="prompt-stat-item">
                                    🔢 <strong>{maxStats.lineCount}</strong> linhas
                                </span>
                                <span className="prompt-stat-separator">•</span>
                                <span className="prompt-stat-item">
                                    🔤 <strong>{maxStats.charCount.toLocaleString('pt-BR')}</strong> letras
                                </span>
                                <span className="prompt-stat-separator">•</span>
                                <span className="prompt-stat-item prompt-stat-tokens">
                                    ⚡ ~<strong>{maxStats.tokenCount.toLocaleString('pt-BR')}</strong> tokens estimados
                                </span>
                            </div>

                            <div className="prompt-max-footer-actions">
                                {readOnly ? (
                                    <button
                                        type="button"
                                        className="btn-vault-primary"
                                        onClick={handleCancelMaximized}
                                    >
                                        Fechar Modo Tela Cheia
                                    </button>
                                ) : (
                                    <>
                                        <button
                                            type="button"
                                            className="btn-vault-action"
                                            onClick={handleCancelMaximized}
                                        >
                                            Cancelar
                                        </button>
                                        <button
                                            type="button"
                                            className="btn-vault-primary"
                                            onClick={handleConfirmMaximized}
                                        >
                                            ✅ Concluir Edição
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
