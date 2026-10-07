import React from 'react';

export default function ProfileTab({
    userData,
    setUserData,
    isSuperAdmin
}) {
    return (
        <div className="profile-tab-content">
            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                    Nome Completo
                </label>
                <input 
                    type="text" 
                    value={userData.name}
                    onChange={e => setUserData({ ...userData, name: e.target.value })}
                    placeholder="Seu nome completo"
                    required
                    autoComplete="name"
                    style={{
                        width: '100%',
                        padding: '0.75rem 1rem',
                        borderRadius: '8px',
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#fff',
                        fontSize: '0.9rem',
                        outline: 'none',
                        transition: 'border-color 0.2s'
                    }}
                />
            </div>

            {!isSuperAdmin ? (
                <>
                    <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                            E-mail de Login
                        </label>
                        <input 
                            type="email" 
                            value={userData.email}
                            onChange={e => setUserData({ ...userData, email: e.target.value })}
                            placeholder="seu@email.com"
                            required
                            autoComplete="username"
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
                            Nova Senha <span style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: '400' }}>(deixe em branco para manter)</span>
                        </label>
                        <input 
                            type="password" 
                            value={userData.password}
                            onChange={e => setUserData({ ...userData, password: e.target.value })}
                            placeholder="••••••••••••"
                            autoComplete="new-password"
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
                </>
            ) : (
                <div style={{
                    padding: '0.85rem 1rem',
                    borderRadius: '8px',
                    background: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    marginBottom: '1.25rem'
                }}>
                    <span style={{ fontSize: '1.2rem' }}>🛡️</span>
                    <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#818cf8' }}>Super Administrador</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>E-mail de acesso e credenciais mestras vinculadas ao ambiente.</div>
                    </div>
                </div>
            )}
        </div>
    );
}
