import React from 'react';
import ProfileTab from './ProfileSettings/ProfileTab';
import WhiteLabelTab from './ProfileSettings/WhiteLabelTab';
import ApiKeyTab from './ProfileSettings/ApiKeyTab';

export default function ProfileSettingsModal({
    isOpen,
    userData,
    setUserData,
    isSuperAdmin,
    loading,
    status,
    onSubmit,
    onClose,
    activeTab = 'profile',
    setActiveTab,
    apiKey,
    generatingKey,
    revokingKey,
    onGenerateApiKey,
    onRevokeApiKey
}) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div 
                className="modal-content" 
                onClick={e => e.stopPropagation()} 
                style={{ 
                    maxWidth: '480px', 
                    maxHeight: '90vh', 
                    overflowY: 'auto',
                    padding: '2rem'
                }}
            >
                <div style={{ textAlign: 'center', marginBottom: '1.25rem' }}>
                    <span className="modal-icon" style={{ margin: '0 auto 0.75rem auto' }}>⚙️</span>
                    <h2 className="modal-title" style={{ fontSize: '1.4rem', marginBottom: '0.25rem' }}>Configurações</h2>
                    <p className="modal-message" style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                        Gerencie seus dados de acesso, personalizações e integrações.
                    </p>
                </div>

                {/* Abas de Navegação */}
                <div style={{
                    display: 'flex',
                    background: 'rgba(15, 23, 42, 0.7)',
                    borderRadius: '10px',
                    padding: '0.3rem',
                    gap: '0.25rem',
                    marginBottom: '1.5rem',
                    border: '1px solid rgba(255, 255, 255, 0.08)'
                }}>
                    <button
                        type="button"
                        onClick={() => setActiveTab && setActiveTab('profile')}
                        style={{
                            flex: 1,
                            padding: '0.6rem 0.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            transition: 'all 0.2s',
                            background: activeTab === 'profile' 
                                ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.15) 100%)' 
                                : 'transparent',
                            color: activeTab === 'profile' ? '#818cf8' : '#94a3b8',
                            boxShadow: activeTab === 'profile' ? '0 2px 8px rgba(0, 0, 0, 0.2)' : 'none'
                        }}
                    >
                        <span>👤</span> Perfil
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab && setActiveTab('whitelabel')}
                        style={{
                            flex: 1,
                            padding: '0.6rem 0.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            transition: 'all 0.2s',
                            background: activeTab === 'whitelabel' 
                                ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.15) 100%)' 
                                : 'transparent',
                            color: activeTab === 'whitelabel' ? '#818cf8' : '#94a3b8',
                            boxShadow: activeTab === 'whitelabel' ? '0 2px 8px rgba(0, 0, 0, 0.2)' : 'none'
                        }}
                    >
                        <span>🏢</span> White-Label
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab && setActiveTab('api_key')}
                        style={{
                            flex: 1,
                            padding: '0.6rem 0.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            transition: 'all 0.2s',
                            background: activeTab === 'api_key' 
                                ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.15) 100%)' 
                                : 'transparent',
                            color: activeTab === 'api_key' ? '#818cf8' : '#94a3b8',
                            boxShadow: activeTab === 'api_key' ? '0 2px 8px rgba(0, 0, 0, 0.2)' : 'none'
                        }}
                    >
                        <span>🔑</span> Chave API
                    </button>
                </div>
                
                <form onSubmit={onSubmit} className="settings-form" style={{ textAlign: 'left' }}>
                    {activeTab === 'profile' && (
                        <ProfileTab 
                            userData={userData}
                            setUserData={setUserData}
                            isSuperAdmin={isSuperAdmin}
                        />
                    )}

                    {activeTab === 'whitelabel' && (
                        <WhiteLabelTab 
                            userData={userData}
                            setUserData={setUserData}
                        />
                    )}

                    {activeTab === 'api_key' && (
                        <ApiKeyTab 
                            apiKey={apiKey}
                            generatingKey={generatingKey}
                            revokingKey={revokingKey}
                            onGenerateApiKey={onGenerateApiKey}
                            onRevokeApiKey={onRevokeApiKey}
                        />
                    )}

                    {status?.message && (
                        <div className={`status-message ${status.type}`} style={{ margin: '1rem 0' }}>
                            {status.message}
                        </div>
                    )}

                    <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
                        <button
                            type="button"
                            className="modal-btn modal-btn-cancel"
                            onClick={onClose}
                            disabled={loading || generatingKey || revokingKey}
                        >
                            {activeTab === 'api_key' ? 'Fechar' : 'Cancelar'}
                        </button>
                        {activeTab !== 'api_key' && (
                            <button
                                type="submit"
                                className="modal-btn modal-btn-confirm"
                                style={{ background: 'var(--primary-color)', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)' }}
                                disabled={loading}
                            >
                                {loading ? 'Salvando...' : 'Salvar Alterações'}
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
