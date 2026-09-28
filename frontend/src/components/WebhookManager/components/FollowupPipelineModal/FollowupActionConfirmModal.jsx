import React from 'react';

/**
 * FollowupActionConfirmModal
 * Popup centralizado de confirmação para ações de Follow-Up:
 * - Backdrop escuro transparente com blur
 * - Não fecha ao clicar fora (apenas via botões explícitos)
 * - 1 botão Cancelar e 1 botão de Ação Principal
 * - Estado de loading com spinner
 */
export const FollowupActionConfirmModal = ({
    isOpen,
    actionType, // 'trigger_now' | 'skip_step'
    stepNumber,
    leadName,
    loading,
    onConfirm,
    onClose
}) => {
    if (!isOpen) return null;

    const isTrigger = actionType === 'trigger_now';
    const title = isTrigger ? 'Confirmar Disparo Imediato' : 'Confirmar Pulo de Passo';
    const icon = isTrigger ? '🚀' : '⏭️';
    const actionLabel = isTrigger ? 'Disparar Agora' : 'Pular Passo';
    const actionColor = isTrigger 
        ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' 
        : 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
    const actionBorder = isTrigger ? '#10b981' : '#f59e0b';

    return (
        <div 
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 11000,
                backgroundColor: 'rgba(0, 0, 0, 0.78)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '1rem'
            }}
            data-testid="followup-confirm-backdrop"
            // Não fecha ao clicar fora (regra de UX/Design System)
            onClick={(e) => e.stopPropagation()}
        >
            <div 
                style={{
                    width: '100%',
                    maxWidth: '480px',
                    background: '#0d1117',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '16px',
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.85), 0 0 30px rgba(0, 0, 0, 0.5)',
                    overflow: 'hidden',
                    animation: 'fadeIn 0.2s ease-out'
                }}
                data-testid="followup-confirm-modal"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{
                    padding: '1.25rem 1.5rem',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                }}>
                    <span style={{ fontSize: '1.4rem' }}>{icon}</span>
                    <h3 style={{
                        margin: 0,
                        fontSize: '1.1rem',
                        fontWeight: 700,
                        color: '#f8fafc'
                    }}>
                        {title}
                    </h3>
                </div>

                {/* Body */}
                <div style={{ padding: '1.5rem', color: '#cbd5e1', fontSize: '0.9rem', lineHeight: 1.5 }}>
                    {isTrigger ? (
                        <p style={{ margin: 0 }}>
                            Tem certeza que deseja <strong>iniciar o disparo imediato do Passo {stepNumber}</strong> para{' '}
                            <span style={{ color: '#60a5fa', fontWeight: 600 }}>{leadName || 'este contato'}</span>?
                            <br /><br />
                            <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                                A mensagem configurada será enviada agora mesmo via integração e o contato avançará para a próxima etapa da régua.
                            </span>
                        </p>
                    ) : (
                        <p style={{ margin: 0 }}>
                            Tem certeza que deseja <strong>pular o Passo {stepNumber}</strong> para{' '}
                            <span style={{ color: '#60a5fa', fontWeight: 600 }}>{leadName || 'este contato'}</span>?
                            <br /><br />
                            <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                                Nenhuma mensagem deste passo será enviada. O contato avançará diretamente para o Passo {stepNumber + 1} e o temporizador começará a contar a partir de agora.
                            </span>
                        </p>
                    )}
                </div>

                {/* Footer com exatamente 1 botão de Cancelar e 1 botão de Ação Principal */}
                <div style={{
                    padding: '1rem 1.5rem',
                    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                    background: '#070a0f',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '0.75rem'
                }}>
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={loading}
                        style={{
                            padding: '0.6rem 1.25rem',
                            borderRadius: '8px',
                            background: 'rgba(255, 255, 255, 0.06)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            color: '#cbd5e1',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.6 : 1,
                            transition: 'all 0.2s'
                        }}
                    >
                        Cancelar
                    </button>

                    <button
                        type="button"
                        data-testid="confirm-action-btn"
                        onClick={onConfirm}
                        disabled={loading}
                        style={{
                            padding: '0.6rem 1.4rem',
                            borderRadius: '8px',
                            background: actionColor,
                            border: `1px solid ${actionBorder}`,
                            color: '#ffffff',
                            fontSize: '0.85rem',
                            fontWeight: 700,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            boxShadow: isTrigger ? '0 0 15px rgba(16, 185, 129, 0.3)' : '0 0 15px rgba(245, 158, 11, 0.3)',
                            transition: 'all 0.2s'
                        }}
                    >
                        {loading && (
                            <span 
                                className="spinner" 
                                style={{ width: '14px', height: '14px', borderWidth: '2px', display: 'inline-block' }} 
                            />
                        )}
                        <span>{loading ? 'Processando...' : actionLabel}</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FollowupActionConfirmModal;
