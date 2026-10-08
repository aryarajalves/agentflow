import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import React from 'react';
import ProfileSettingsModal from '../../components/Sidebar/components/ProfileSettingsModal';

describe('ProfileSettingsModal - Abas e Chave de API', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    const defaultProps = {
        isOpen: true,
        userData: {
            name: 'Aryaraj Alves',
            email: 'aryarajmarketing@gmail.com',
            password: '',
            company_name: 'Minha Empresa Tech',
            company_logo: '',
            company_logo_size: 'medium'
        },
        setUserData: vi.fn(),
        isSuperAdmin: false,
        loading: false,
        status: { type: '', message: '' },
        onSubmit: vi.fn(e => e.preventDefault()),
        onClose: vi.fn(),
        activeTab: 'profile',
        setActiveTab: vi.fn(),
        apiKey: '',
        generatingKey: false,
        revokingKey: false,
        onGenerateApiKey: vi.fn(),
        onRevokeApiKey: vi.fn()
    };

    it('não deve renderizar nada quando isOpen for falso', () => {
        const { container } = render(<ProfileSettingsModal {...defaultProps} isOpen={false} />);
        expect(container.firstChild).toBeNull();
    });

    it('deve renderizar as três abas de navegação quando isOpen for true', () => {
        render(<ProfileSettingsModal {...defaultProps} />);
        expect(screen.getByText('Configurações')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /perfil/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /white-label/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /chave api/i })).toBeInTheDocument();
    });

    it('deve chamar setActiveTab ao clicar nas abas', () => {
        render(<ProfileSettingsModal {...defaultProps} />);
        const whiteLabelTabBtn = screen.getByRole('button', { name: /white-label/i });
        fireEvent.click(whiteLabelTabBtn);
        expect(defaultProps.setActiveTab).toHaveBeenCalledWith('whitelabel');

        const apiKeyTabBtn = screen.getByRole('button', { name: /chave api/i });
        fireEvent.click(apiKeyTabBtn);
        expect(defaultProps.setActiveTab).toHaveBeenCalledWith('api_key');
    });

    it('deve renderizar a aba de perfil com os campos corretos', () => {
        render(<ProfileSettingsModal {...defaultProps} activeTab="profile" />);
        expect(screen.getByDisplayValue('Aryaraj Alves')).toBeInTheDocument();
        expect(screen.getByDisplayValue('aryarajmarketing@gmail.com')).toBeInTheDocument();
        expect(screen.getByText('Salvar Alterações')).toBeInTheDocument();
    });

    it('deve renderizar a aba de White-Label com seus campos', () => {
        render(<ProfileSettingsModal {...defaultProps} activeTab="whitelabel" />);
        expect(screen.getByDisplayValue('Minha Empresa Tech')).toBeInTheDocument();
        expect(screen.getByText('Tamanho da Logo na Barra Lateral')).toBeInTheDocument();
    });

    it('deve exibir mensagem e botão para gerar chave na aba Chave API se não possuir chave', () => {
        render(<ProfileSettingsModal {...defaultProps} activeTab="api_key" apiKey="" />);
        expect(screen.getByText('Nenhuma Chave de API Criada')).toBeInTheDocument();
        const generateBtn = screen.getByRole('button', { name: /gerar nova chave de api/i });
        expect(generateBtn).toBeInTheDocument();

        fireEvent.click(generateBtn);
        expect(defaultProps.onGenerateApiKey).toHaveBeenCalled();
    });

    it('deve exibir chave ativa, botão de copiar e regenerar na aba Chave API se possuir chave', () => {
        render(<ProfileSettingsModal {...defaultProps} activeTab="api_key" apiKey="ag_live_1234567890abcdef" />);
        expect(screen.getByDisplayValue('ag_live_1234567890abcdef')).toBeInTheDocument();
        expect(screen.getByText('Ativa')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /copiar/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /regenerar chave/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /revogar/i })).toBeInTheDocument();
        expect(screen.queryByText(/como usar em outra interface/i)).not.toBeInTheDocument();
    });
});
