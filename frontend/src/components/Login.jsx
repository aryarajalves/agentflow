import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

const Login = ({ onLogin }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    useEffect(() => {
        const expiredMsg = sessionStorage.getItem('session_expired_msg');
        if (expiredMsg) {
            setError(expiredMsg);
            sessionStorage.removeItem('session_expired_msg');
        }
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const res = await api.post('/login', { email, password });
            const data = await res.json();
            const token = data.token || data.access_token;
            if (res.ok && token) {
                localStorage.setItem('admin_token', token);
                if (data.user) {
                    localStorage.setItem('user_name', data.user.name || data.user.nome || 'Admin');
                    localStorage.setItem('user_role', data.user.role || data.user.cargo || 'SUPER_ADMIN');
                }
                onLogin();
            } else {
                setError(data.detail || 'Email ou senha inválidos');
            }
        } catch (err) {
            setError('Erro de conexão com o servidor');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-box fade-in">
                <div className="login-header">
                    <div className="brand-logo">🤖</div>
                    <h1>Agent Flow</h1>
                    <p>Acesse seu painel de automação inteligente</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label>E-mail</label>
                        <div className="input-wrapper">
                            <span className="input-icon">✉️</span>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="seu@email.com"
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Senha</label>
                        <div className="input-wrapper">
                            <span className="input-icon">🔑</span>
                            <input
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                            />
                            <button
                                type="button"
                                className="toggle-password"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? '👁️' : '👁️‍🗨️'}
                            </button>
                        </div>
                    </div>

                    {error && <div className="login-error-msg">{error}</div>}

                    <button type="submit" className="login-btn-primary" disabled={loading}>
                        {loading ? 'Entrando...' : 'Acessar Painel'}
                    </button>
                </form>

                <div className="login-footer">
                    &copy; 2024 Agent Flow &bull; Automação Sem Limites
                </div>
            </div>

            <style>{`
                .login-page {
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: radial-gradient(circle at top left, #1e293b, #0f172a);
                    color: white;
                    overflow: hidden;
                }

                .login-box {
                    width: 100%;
                    max-width: 420px;
                    padding: 2.5rem;
                    background: rgba(30, 41, 59, 0.4);
                    backdrop-filter: blur(20px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 30px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    text-align: center;
                }

                .login-header { margin-bottom: 2.5rem; }
                
                .brand-logo {
                    font-size: 3.5rem;
                    margin-bottom: 1rem;
                    display: inline-block;
                    background: rgba(99, 102, 241, 0.1);
                    width: 80px;
                    height: 80px;
                    line-height: 80px;
                    border-radius: 20px;
                    border: 1px solid rgba(99, 102, 241, 0.2);
                    box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
                }

                .login-header h1 {
                    font-size: 2rem;
                    font-weight: 800;
                    margin: 0;
                    background: linear-gradient(135deg, #fff, #94a3b8);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .login-header p {
                    color: #94a3b8;
                    font-size: 0.95rem;
                    margin-top: 8px;
                }

                .login-form { text-align: left; }

                .form-group { margin-bottom: 1.5rem; }
                
                .form-group label {
                    display: block;
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: #e2e8f0;
                    margin-bottom: 8px;
                    margin-left: 12px;
                }

                .input-wrapper {
                    position: relative;
                    width: 100%;
                }

                .input-icon {
                    position: absolute;
                    left: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    z-index: 2;
                    opacity: 0.8;
                    color: #6366f1;
                    pointer-events: none;
                }

                .input-wrapper input {
                    width: 100%;
                    padding: 14px 16px 14px 48px !important; /* Espaço para o ícone */
                    background: rgba(15, 23, 42, 0.7) !important;
                    border: 2px solid rgba(255, 255, 255, 0.2) !important;
                    border-radius: 16px;
                    color: white !important;
                    font-size: 1rem;
                    outline: none;
                    transition: all 0.3s;
                    caret-color: #6366f1;
                }

                .input-wrapper input:focus {
                    border-color: #6366f1 !important;
                    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2) !important;
                    background: rgba(30, 41, 59, 0.8) !important;
                }

                .toggle-password {
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    z-index: 2;
                    background: transparent;
                    border: none;
                    color: #94a3b8;
                    cursor: pointer;
                    padding: 8px;
                    font-size: 1.2rem;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                /* Garante que ícones do navegador (como a chavinha ou o 'x') fiquem visíveis */
                .input-wrapper input::-webkit-calendar-picker-indicator,
                .input-wrapper input::-webkit-credentials-auto-fill-button {
                    filter: invert(1) brightness(2);
                    cursor: pointer;
                    margin-right: 35px; /* Evita sobrepor o botão de olho */
                }

                /* Limpa estilos chatos de preenchimento automático do Chrome/Edge */
                .input-wrapper input:-webkit-autofill,
                .input-wrapper input:-webkit-autofill:hover, 
                .input-wrapper input:-webkit-autofill:focus {
                    -webkit-text-fill-color: white !important;
                    -webkit-box-shadow: 0 0 0px 1000px #1e293b inset !important;
                    transition: background-color 5000s ease-in-out 0s !important;
                    border-radius: 16px;
                }

                .login-error-msg {
                    background: rgba(239, 68, 68, 0.1);
                    color: #f87171;
                    padding: 12px;
                    border-radius: 12px;
                    font-size: 0.85rem;
                    margin-bottom: 1.5rem;
                    border: 1px solid rgba(239, 68, 68, 0.2);
                    text-align: center;
                }

                .login-btn-primary {
                    width: 100%;
                    padding: 14px;
                    background: linear-gradient(135deg, #6366f1, #4f46e5);
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-weight: 700;
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.3s;
                    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
                    margin-top: 1rem;
                }

                .login-btn-primary:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5);
                }

                .login-btn-primary:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                .login-footer {
                    margin-top: 2rem;
                    font-size: 0.75rem;
                    color: #64748b;
                    letter-spacing: 0.05em;
                }

                .fade-in {
                    animation: fadeIn 0.8s ease-out;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default Login;
