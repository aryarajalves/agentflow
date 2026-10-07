import React from 'react';
import { useSidebarProfile } from './hooks/useSidebarProfile';
import SidebarLogo from './components/SidebarLogo';
import SidebarNav from './components/SidebarNav';
import SidebarUserProfile from './components/SidebarUserProfile';
import ProfileSettingsModal from './components/ProfileSettingsModal';
import LogoutConfirmModal from './components/LogoutConfirmModal';

const Sidebar = ({ onLogout }) => {
    const {
        showLogoutModal,
        setShowLogoutModal,
        showSettingsModal,
        setShowSettingsModal,
        userData,
        setUserData,
        loading,
        status,
        companyName,
        companyLogo,
        companyLogoSize,
        isSuperAdmin,
        isAdmin,
        isUser,
        handleUpdateUser,
        openSettings,
        activeTab,
        setActiveTab,
        apiKey,
        generatingKey,
        revokingKey,
        handleGenerateApiKey,
        handleRevokeApiKey
    } = useSidebarProfile();

    return (
        <>
            <aside className="sidebar">
                <SidebarLogo
                    companyLogo={companyLogo}
                    companyName={companyName}
                    companyLogoSize={companyLogoSize}
                />

                <SidebarNav
                    isSuperAdmin={isSuperAdmin}
                    isAdmin={isAdmin}
                    isUser={isUser}
                />

                <SidebarUserProfile
                    onOpenSettings={openSettings}
                    onOpenLogoutModal={() => setShowLogoutModal(true)}
                />
            </aside>

            <ProfileSettingsModal
                isOpen={showSettingsModal}
                userData={userData}
                setUserData={setUserData}
                isSuperAdmin={isSuperAdmin}
                loading={loading}
                status={status}
                onSubmit={handleUpdateUser}
                onClose={() => setShowSettingsModal(false)}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                apiKey={apiKey}
                generatingKey={generatingKey}
                revokingKey={revokingKey}
                onGenerateApiKey={handleGenerateApiKey}
                onRevokeApiKey={handleRevokeApiKey}
            />

            <LogoutConfirmModal
                isOpen={showLogoutModal}
                onCancel={() => setShowLogoutModal(false)}
                onLogout={onLogout}
            />
        </>
    );
};

export default Sidebar;
