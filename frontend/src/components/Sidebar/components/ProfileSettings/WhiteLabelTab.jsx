import React from 'react';

export default function WhiteLabelTab({
    userData,
    setUserData
}) {
    return (
        <div className="whitelabel-tab-content">
            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                    Nome da Empresa (White-label)
                </label>
                <input 
                    type="text" 
                    value={userData.company_name || ''}
                    onChange={e => setUserData({ ...userData, company_name: e.target.value })}
                    placeholder="Ex: Minha Empresa / Agência"
                    style={{
                        width: '100%',
                        padding: '0.75rem 1rem',
                        borderRadius: '8px',
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#fff',
                        fontSize: '0.9rem',
                        outline: 'none'
                    }}
                />
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                    Logo da Empresa (Upload)
                </label>
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    border: '2px dashed rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    padding: '1.25rem',
                    textAlign: 'center',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    position: 'relative',
                    transition: 'border-color 0.2s ease, background-color 0.2s ease'
                }}>
                    {userData.company_logo ? (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem', zIndex: 2 }}>
                            <img 
                                src={userData.company_logo} 
                                alt="Preview da Logo" 
                                style={{ maxHeight: '70px', maxWidth: '100%', objectFit: 'contain', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }} 
                            />
                            <button 
                                type="button" 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setUserData({ ...userData, company_logo: '' });
                                }}
                                style={{
                                    background: 'rgba(239, 68, 68, 0.2)',
                                    color: '#f87171',
                                    border: '1px solid rgba(239, 68, 68, 0.4)',
                                    padding: '0.35rem 0.75rem',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                    transition: 'all 0.2s'
                                }}
                            >
                                🗑️ Remover Logo
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
                            <span style={{ fontSize: '1.6rem' }}>📤</span>
                            <span style={{ fontSize: '0.85rem', color: '#cbd5e1', fontWeight: '500' }}>Clique ou arraste uma imagem aqui</span>
                            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>PNG, JPG ou SVG (Máx. 2MB)</span>
                        </div>
                    )}
                    <input 
                        type="file" 
                        accept="image/*"
                        onChange={async (e) => {
                            const file = e.target.files[0];
                            if (file) {
                                const reader = new FileReader();
                                reader.onloadend = () => {
                                    setUserData({ ...userData, company_logo: reader.result });
                                };
                                reader.readAsDataURL(file);
                            }
                        }}
                        style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: '100%',
                            opacity: 0,
                            cursor: 'pointer',
                            zIndex: 1
                        }}
                    />
                </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                    Tamanho da Logo na Barra Lateral
                </label>
                <select 
                    value={userData.company_logo_size || 'medium'}
                    onChange={e => setUserData({ ...userData, company_logo_size: e.target.value })}
                    style={{
                        width: '100%',
                        padding: '0.75rem 1rem',
                        borderRadius: '8px',
                        backgroundColor: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#fff',
                        fontSize: '0.9rem',
                        outline: 'none'
                    }}
                >
                    <option value="small" style={{ backgroundColor: '#0f172a' }}>Pequeno (24px)</option>
                    <option value="medium" style={{ backgroundColor: '#0f172a' }}>Médio (32px)</option>
                    <option value="large" style={{ backgroundColor: '#0f172a' }}>Grande (40px)</option>
                </select>
            </div>
        </div>
    );
}
