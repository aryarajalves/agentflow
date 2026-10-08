import { useState, useEffect } from 'react';
import { api } from '../../../api/client';

export function useSidebarProfile() {
    const [showLogoutModal, setShowLogoutModal] = useState(false);
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [userData, setUserData] = useState({ 
        name: '', 
        email: '', 
        password: '',
        company_name: '',
        company_logo: '',
        company_logo_size: 'medium'
    });
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState({ type: '', message: '' });

    const [companyName, setCompanyName] = useState(localStorage.getItem('company_name') || '');
    const [companyLogo, setCompanyLogo] = useState(localStorage.getItem('company_logo') || '');
    const [companyLogoSize, setCompanyLogoSize] = useState(localStorage.getItem('company_logo_size') || 'medium');

    useEffect(() => {
        document.title = companyName ? companyName : 'Agente de IA';
    }, [companyName]);

    const userRole = localStorage.getItem('user_role') || 'Usuário';
    const isSuperAdmin = userRole === 'Super Admin';
    const isAdmin = userRole === 'Admin';
    const isUser = userRole === 'Usuário';

    const [activeTab, setActiveTab] = useState('profile');
    const [apiKey, setApiKey] = useState('');
    const [generatingKey, setGeneratingKey] = useState(false);
    const [revokingKey, setRevokingKey] = useState(false);

    const fetchUserData = async () => {
        try {
            const response = await api.get('/users/me');
            if (response.ok) {
                const data = await response.json();
                setUserData({ 
                    name: data.name || '', 
                    email: data.email || '', 
                    password: '',
                    company_name: data.company_name || '',
                    company_logo: data.company_logo || '',
                    company_logo_size: data.company_logo_size || 'medium'
                });
                setApiKey(data.api_key || '');
                
                if (data.company_name !== undefined) {
                    localStorage.setItem('company_name', data.company_name || '');
                    setCompanyName(data.company_name || '');
                }
                if (data.company_logo !== undefined) {
                    localStorage.setItem('company_logo', data.company_logo || '');
                    setCompanyLogo(data.company_logo || '');
                }
                if (data.company_logo_size !== undefined) {
                    localStorage.setItem('company_logo_size', data.company_logo_size || 'medium');
                    setCompanyLogoSize(data.company_logo_size || 'medium');
                }
            } else if (response.status === 401) {
                setStatus({ type: 'error', message: 'Sua sessão expirou. Por favor, faça login novamente.' });
            }
        } catch (error) {
            console.error("Erro ao carregar dados do usuário:", error);
        }
    };

    const handleGenerateApiKey = async () => {
        setGeneratingKey(true);
        setStatus({ type: '', message: '' });
        try {
            const response = await api.post('/users/me/generate-api-key');
            if (response.ok) {
                const data = await response.json();
                setApiKey(data.api_key);
                setStatus({ type: 'success', message: 'Nova Chave de API gerada com sucesso!' });
                return data.api_key;
            } else {
                const err = await response.json().catch(() => ({}));
                if (response.status === 401) {
                    setStatus({ type: 'error', message: 'Sua sessão expirou. Faça login novamente para gerar chaves.' });
                } else {
                    setStatus({ type: 'error', message: err.detail || 'Erro ao gerar chave de API.' });
                }
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Falha de conexão ao gerar chave de API.' });
        } finally {
            setGeneratingKey(false);
        }
    };

    const handleRevokeApiKey = async () => {
        setRevokingKey(true);
        setStatus({ type: '', message: '' });
        try {
            const response = await api.delete('/users/me/revoke-api-key');
            if (response.ok) {
                setApiKey('');
                setStatus({ type: 'success', message: 'Chave de API revogada com sucesso!' });
            } else {
                const err = await response.json().catch(() => ({}));
                if (response.status === 401) {
                    setStatus({ type: 'error', message: 'Sua sessão expirou. Faça login novamente.' });
                } else {
                    setStatus({ type: 'error', message: err.detail || 'Erro ao revogar chave.' });
                }
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Falha de conexão ao revogar chave.' });
        } finally {
            setRevokingKey(false);
        }
    };

    const handleUpdateUser = async (e) => {
        e.preventDefault();
        setLoading(true);
        setStatus({ type: '', message: '' });
        try {
            const response = await api.put('/users/me', {
                name: userData.name,
                email: userData.email,
                password: userData.password || undefined,
                company_name: userData.company_name,
                company_logo: userData.company_logo,
                company_logo_size: userData.company_logo_size
            });
            if (response.ok) {
                const updated = await response.json();
                if (updated && updated.name) {
                    localStorage.setItem('user_name', updated.name);
                }
                localStorage.setItem('company_name', updated.company_name || '');
                localStorage.setItem('company_logo', updated.company_logo || '');
                localStorage.setItem('company_logo_size', updated.company_logo_size || 'medium');
                setCompanyName(updated.company_name || '');
                setCompanyLogo(updated.company_logo || '');
                setCompanyLogoSize(updated.company_logo_size || 'medium');

                setStatus({ type: 'success', message: 'Perfil atualizado com sucesso!' });
                setTimeout(() => {
                    setShowSettingsModal(false);
                    setStatus({ type: '', message: '' });
                }, 1500);
            } else {
                const err = await response.json().catch(() => ({}));
                setStatus({ type: 'error', message: err.detail || 'Erro ao atualizar perfil.' });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Erro de conexão ou autenticação.' });
        } finally {
            setLoading(false);
        }
    };

    const openSettings = () => {
        setStatus({ type: '', message: '' });
        setActiveTab('profile');
        fetchUserData();
        setShowSettingsModal(true);
    };

    return {
        showLogoutModal,
        setShowLogoutModal,
        showSettingsModal,
        setShowSettingsModal,
        activeTab,
        setActiveTab,
        apiKey,
        generatingKey,
        revokingKey,
        handleGenerateApiKey,
        handleRevokeApiKey,
        userData,
        setUserData,
        loading,
        status,
        companyName,
        companyLogo,
        companyLogoSize,
        userRole,
        isSuperAdmin,
        isAdmin,
        isUser,
        handleUpdateUser,
        openSettings
    };
}
