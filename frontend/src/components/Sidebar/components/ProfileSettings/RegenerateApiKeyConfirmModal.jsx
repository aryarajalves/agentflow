import React from 'react';

export default function RegenerateApiKeyConfirmModal({
    isOpen,
    onConfirm,
    onCancel,
    loading
}) {
    if (!isOpen) return null;

    return (
        <div 
            className="modal-overlay" 
            style={{ 
                zIndex: 10000000, 
                backgroundColor: 'rgba(2, 6, 23, 0.85)', 
                backdropFilter: 'blur(8px)' 
            }}
        >
            <div 
                className="modal-content" 
                onClick={e => e.stopPropagation()} 
                style={{ 
                    maxWidth: '400px', 
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(245, 158, 11, 0.15)',
                    textAlign: 'center',
                    padding: '2rem 1.75rem'
                }}
            >
                <div style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '16px',
                    background: 'rgba(245, 158, 11, 0.12)',
                    border: '1px solid rgba(245, 158, 11, 0.25)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.75rem',
                    margin: '0 auto 1.25rem auto'
                }}>
                    ⚠️
                </div>

                <h3 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#fff', marginBottom: '0.5rem' }}>
                    Regenerar Chave de API?
                </h3>

                <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: '1.5', marginBottom: '1.5rem' }}>
                    A chave atual deixará de funcionar imediatamente. Quaisquer outras interfaces ou sistemas integrados precisarão ser atualizados com a nova chave.
                </p>

                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                    <button
                        type="button"
                        onClick={onCancel}
                        disabled={loading}
                        style={{
                            flex: 1,
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            background: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            color: '#94a3b8',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        disabled={loading}
                        style={{
                            flex: 1,
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                            border: 'none',
                            color: '#fff',
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            boxShadow: '0 4px 14px rgba(245, 158, 11, 0.35)',
                            transition: 'all 0.2s'
                        }}
                    >
                        {loading ? 'Gerando...' : 'Sim, Regenerar'}
                    </button>
                </div>
            </div>
        </div>
    );
}
