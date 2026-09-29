import React from 'react';
import { NavLink } from 'react-router-dom';

export default function SidebarNav({
    isSuperAdmin,
    isAdmin,
    isUser
}) {
    return (
        <nav className="sidebar-nav">
            {(isSuperAdmin || isAdmin || isUser) && (
                <>
                    <div className="nav-section">
                        <span className="nav-section-title">PRINCIPAL</span>
                        <NavLink
                            to="/"
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                        >
                            <span className="nav-icon">🤖</span>
                            <span className="nav-label">Meus Agentes</span>
                            <div className="active-indicator"></div>
                        </NavLink>
                        {(isSuperAdmin || isAdmin) && (
                            <NavLink
                                to="/prompt-vault"
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <span className="nav-icon">🛡️</span>
                                <span className="nav-label">Cofre de Prompts</span>
                                <div className="active-indicator"></div>
                            </NavLink>
                        )}
                    </div>

                    {(isSuperAdmin || isAdmin) ? (
                        <>
                            <div className="nav-section">
                                <span className="nav-section-title">ATENDIMENTO</span>
                                <NavLink
                                    to="/knowledge-bases?tab=inbox"
                                    className={({ isActive }) => {
                                        const search = (typeof window !== 'undefined' && window.location && window.location.search) || '';
                                        const isInbox = search.includes('tab=inbox');
                                        return `nav-item ${isInbox ? 'active' : ''}`;
                                    }}
                                >
                                    <span className="nav-icon">📥</span>
                                    <span className="nav-label">Inbox de Dúvidas</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                                <NavLink
                                    to="/crm"
                                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                >
                                    <span className="nav-icon">📊</span>
                                    <span className="nav-label">CRM</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                                <NavLink
                                    to="/lead-scoring"
                                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                >
                                    <span className="nav-icon">🔥</span>
                                    <span className="nav-label">Lead Scoring</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                                <NavLink
                                    to="/ranking-duvidas"
                                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                >
                                    <span className="nav-icon">🏆</span>
                                    <span className="nav-label">Ranking de Dúvidas</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                            </div>

                            <div className="nav-section">
                                <span className="nav-section-title">CONHECIMENTO</span>
                                <NavLink
                                    to="/knowledge-bases"
                                    className={({ isActive }) => {
                                        const search = (typeof window !== 'undefined' && window.location && window.location.search) || '';
                                        const isInbox = search.includes('tab=inbox');
                                        return `nav-item ${isActive && !isInbox ? 'active' : ''}`;
                                    }}
                                >
                                    <span className="nav-icon">📚</span>
                                    <span className="nav-label">Bases de Conhecimento</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                            </div>

                            <div className="nav-section">
                                <span className="nav-section-title">SISTEMA</span>
                                <NavLink
                                    to="/financeiro"
                                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                >
                                    <span className="nav-icon">💰</span>
                                    <span className="nav-label">Financeiro</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                                <NavLink
                                    to="/integrations"
                                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                >
                                    <span className="nav-icon">🔌</span>
                                    <span className="nav-label">Integrações</span>
                                    <div className="active-indicator"></div>
                                </NavLink>
                            </div>
                        </>
                    ) : (
                        /* Usuário comum vê apenas o Ranking de Dúvidas */
                        <div className="nav-section">
                            <span className="nav-section-title">ATENDIMENTO</span>
                            <NavLink
                                to="/ranking-duvidas"
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <span className="nav-icon">🏆</span>
                                <span className="nav-label">Ranking de Dúvidas</span>
                                <div className="active-indicator"></div>
                            </NavLink>
                        </div>
                    )}
                </>
            )}

            {isSuperAdmin && (
                <div className="nav-section">
                    <span className="nav-section-title">ADMINISTRAÇÃO</span>
                    <NavLink
                        to="/users"
                        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    >
                        <span className="nav-icon">👥</span>
                        <span className="nav-label">Gestão de Usuários</span>
                        <div className="active-indicator"></div>
                    </NavLink>
                    <NavLink
                        to="/backups"
                        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    >
                        <span className="nav-icon">🗄️</span>
                        <span className="nav-label">Backups do Sistema</span>
                        <div className="active-indicator"></div>
                    </NavLink>
                </div>
            )}
        </nav>
    );
}
