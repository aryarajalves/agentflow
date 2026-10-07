import React, { useState } from 'react';
import RegenerateApiKeyConfirmModal from './RegenerateApiKeyConfirmModal';

export default function ApiKeyTab({
    apiKey,
    generatingKey,
    revokingKey,
    onGenerateApiKey,
    onRevokeApiKey
}) {
    const [copied, setCopied] = useState(false);
    const [showKey, setShowKey] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);

    const handleCopy = () => {
        if (!apiKey) return;
        navigator.clipboard.writeText(apiKey);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
    };

    const handleConfirmRegenerate = async () => {
        setShowConfirmModal(false);
        await onGenerateApiKey();
    };

    return (
        <div className="api-key-tab-content">
            {apiKey ? (
                <div>
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '0.75rem'
                    }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1' }}>
                            Sua Chave de API Ativa
                        </span>
                        <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            fontSize: '0.75rem',
                            color: '#10b981',
                            fontWeight: '600',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            border: '1px solid rgba(16, 185, 129, 0.25)',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '12px'
                        }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
                            Ativa
                        </span>
                    </div>

                    <div style={{
                        display: 'flex',
                        gap: '0.5rem',
                        marginBottom: '1rem',
                        position: 'relative'
                    }}>
                        <input
                            type={showKey ? 'text' : 'password'}
                            value={apiKey}
                            readOnly
                            style={{
                                flex: 1,
                                padding: '0.75rem 1rem',
                                paddingRight: '2.5rem',
                                borderRadius: '8px',
                                background: 'rgba(15, 23, 42, 0.7)',
                                border: '1px solid rgba(99, 102, 241, 0.25)',
                                color: '#a5b4fc',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                outline: 'none'
                            }}
                        />
                        <button
                            type="button"
                            onClick={() => setShowKey(!showKey)}
                            title={showKey ? 'Ocultar chave' : 'Mostrar chave'}
                            style={{
                                position: 'absolute',
                                right: '110px',
                                top: '50%',
                                transform: 'translateY(-50%)',
                                background: 'none',
                                border: 'none',
                                color: '#94a3b8',
                                cursor: 'pointer',
                                fontSize: '1rem',
                                padding: '0.25rem'
                            }}
                        >
                            {showKey ? '🙈' : '👁️'}
                        </button>
                        <button
                            type="button"
                            onClick={handleCopy}
                            style={{
                                padding: '0.75rem 1rem',
                                borderRadius: '8px',
                                background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(99, 102, 241, 0.15)',
                                border: copied ? '1px solid #10b981' : '1px solid rgba(99, 102, 241, 0.35)',
                                color: copied ? '#34d399' : '#818cf8',
                                fontSize: '0.85rem',
                                fontWeight: '600',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                transition: 'all 0.2s',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            {copied ? '✅ Copiado!' : '📋 Copiar'}
                        </button>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
                        <button
                            type="button"
                            onClick={() => setShowConfirmModal(true)}
                            disabled={generatingKey || revokingKey}
                            style={{
                                flex: 1,
                                padding: '0.6rem 0.85rem',
                                borderRadius: '8px',
                                background: 'rgba(245, 158, 11, 0.1)',
                                border: '1px solid rgba(245, 158, 11, 0.3)',
                                color: '#fbbf24',
                                fontSize: '0.8rem',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                        >
                            {generatingKey ? 'Regenerando...' : '🔄 Regenerar Chave'}
                        </button>
                        <button
                            type="button"
                            onClick={onRevokeApiKey}
                            disabled={generatingKey || revokingKey}
                            style={{
                                padding: '0.6rem 0.85rem',
                                borderRadius: '8px',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                color: '#f87171',
                                fontSize: '0.8rem',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                        >
                            {revokingKey ? 'Revogando...' : '🗑️ Revogar'}
                        </button>
                    </div>
                </div>
            ) : (
                <div style={{
                    padding: '1.5rem',
                    textAlign: 'center',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '12px',
                    border: '1px dashed rgba(255, 255, 255, 0.15)',
                    marginBottom: '1.25rem'
                }}>
                    <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>🔐</span>
                    <h4 style={{ fontSize: '1rem', fontWeight: '600', color: '#fff', marginBottom: '0.35rem' }}>
                        Nenhuma Chave de API Criada
                    </h4>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: '1.4', marginBottom: '1.25rem' }}>
                        Gere uma chave para autenticar requisições de outras interfaces ou sistemas externos com sua conta.
                    </p>
                    <button
                        type="button"
                        onClick={onGenerateApiKey}
                        disabled={generatingKey}
                        style={{
                            padding: '0.75rem 1.5rem',
                            borderRadius: '8px',
                            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                            border: 'none',
                            color: '#fff',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)',
                            transition: 'all 0.2s'
                        }}
                    >
                        {generatingKey ? 'Gerando Chave...' : '⚡ Gerar Nova Chave de API'}
                    </button>
                </div>
            )}

            <div style={{
                padding: '1rem',
                borderRadius: '8px',
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid rgba(255, 255, 255, 0.08)'
            }}>
                <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span>💡</span> Como Usar em Outra Interface
                </div>
                <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: '1.4', marginBottom: '0.5rem' }}>
                    Envie o header HTTP abaixo em todas as suas requisições:
                </p>
                <div style={{
                    padding: '0.5rem 0.75rem',
                    borderRadius: '6px',
                    background: 'rgba(2, 6, 23, 0.7)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    fontFamily: 'monospace',
                    fontSize: '0.75rem',
                    color: '#818cf8',
                    overflowX: 'auto',
                    whiteSpace: 'nowrap'
                }}>
                    X-API-Key: {apiKey || 'sua_chave_de_api'}
                </div>
            </div>

            <RegenerateApiKeyConfirmModal
                isOpen={showConfirmModal}
                onConfirm={handleConfirmRegenerate}
                onCancel={() => setShowConfirmModal(false)}
                loading={generatingKey}
            />
        </div>
    );
}
