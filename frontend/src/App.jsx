import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard/index';
import ConfigPanel from './components/ConfigPanel/index';
import FAQ from './components/FAQ';
import KnowledgeBaseList from './components/KnowledgeBaseList';
import KnowledgeBaseEditor from './components/KnowledgeBaseEditor';
import ToolsManager from './components/ToolsManager/index';
import ChatPlayground from './components/ChatPlayground/index';
import Financeiro from './components/Financeiro/index';
import IntegrationsPanel from './components/IntegrationsPanel';
import PublicChat from './components/PublicChat';
import SharedHistory from './components/SharedHistory';
import Login from './components/Login';
import Register from './components/Register';
import UserManagement from './components/UserManagement';
import PublicQuestionsView from './components/PublicQuestionsView';
import WebhookManager from './components/WebhookManager/index';
import LeadScoring from './components/LeadScoring/index';
import CRM from './components/CRM/index';
import ObjectionsDashboard from './components/ObjectionsDashboard';
import Backups from './components/Backups';
import PromptVault from './components/PromptVault';


function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('admin_token'));
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const handleToast = (e) => {
      const { message, type } = e.detail || {};
      if (!message) return;
      setToast({ message, type: type || 'success', id: Date.now() });
    };
    window.addEventListener('app:toast', handleToast);
    return () => window.removeEventListener('app:toast', handleToast);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timer);
  }, [toast]);

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
    setIsAuthenticated(false);
  };

  const userRole = localStorage.getItem('user_role') || 'Usuário';
  const isSuperAdmin = userRole === 'Super Admin' || userRole === 'SUPER_ADMIN';
  const isAdmin = userRole === 'Admin' || userRole === 'ADMIN' || isSuperAdmin;
  const isUser = userRole === 'Usuário';

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/chat/:agentId" element={<PublicChat />} />
        <Route path="/shared/:sessionId" element={<SharedHistory />} />
        <Route path="/public/questions/:token" element={<PublicQuestionsView />} />
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" /> : <Login onLogin={() => setIsAuthenticated(true)} />
        } />
        <Route path="/register/:token" element={<Register />} />
        <Route path="*" element={
          !isAuthenticated ? <Navigate to="/login" /> : (
            <div className="app-layout">
              <Sidebar onLogout={handleLogout} />
              <main className="main-content">
                <div className="content-container">
                  <Routes>
                    {/* Rotas Comuns */}
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/playground" element={<ChatPlayground />} />
                    <Route path="/ranking-duvidas" element={<ObjectionsDashboard />} />

                    {/* Rotas restritas para Admin e Super Admin */}
                    {(isAdmin || isSuperAdmin) && (
                      <>
                        <Route path="/agent/new" element={<ConfigPanel />} />
                        <Route path="/agent/:id" element={<ConfigPanel />} />
                        <Route path="/faq" element={<FAQ />} />
                        <Route path="/knowledge-bases" element={<KnowledgeBaseList />} />
                        <Route path="/knowledge-bases/:id" element={<KnowledgeBaseEditor />} />
                        <Route path="/tools" element={<ToolsManager standalone={true} />} />
                        <Route path="/financeiro" element={<Financeiro />} />
                        <Route path="/integrations" element={<IntegrationsPanel />} />
                        <Route path="/webhooks" element={<WebhookManager />} />
                        <Route path="/crm" element={<CRM />} />
                        <Route path="/lead-scoring" element={<LeadScoring />} />
                        <Route path="/prompt-vault" element={<PromptVault />} />
                      </>
                    )}

                    {/* Rota restrita APENAS para Super Admin */}
                    {isSuperAdmin && (
                      <>
                        <Route path="/users" element={<UserManagement />} />
                        <Route path="/backups" element={<Backups />} />
                      </>
                    )}

                    {/* Redirecionar qualquer acesso não autorizado para a Home */}
                    <Route path="*" element={<Navigate to="/" />} />
                  </Routes>
                </div>
              </main>
            </div>
          )
        } />
      </Routes>
      {toast && (
        <div className={`global-toast global-toast-${toast.type}`}>
          <span className="global-toast-icon">
            {toast.type === 'success' ? '✅' : toast.type === 'info' ? 'ℹ️' : toast.type === 'warning' ? '⚠️' : '❌'}
          </span>
          <span>{toast.message}</span>
        </div>
      )}
    </BrowserRouter>
  );
}

export default App;
