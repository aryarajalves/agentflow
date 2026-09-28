import React, { useState } from 'react';
import { useFollowupPipeline } from './FollowupPipelineModal/useFollowupPipeline';
import PipelineHeader from './FollowupPipelineModal/PipelineHeader';
import PipelineStepItem from './FollowupPipelineModal/PipelineStepItem';
import FollowupActionConfirmModal from './FollowupPipelineModal/FollowupActionConfirmModal';
import '../styles/WebhookManager.css';

const FollowupPipelineModal = ({ lead, webhook, onClose }) => {
    const {
        pipelineData,
        loading,
        error,
        fetchPipeline,
        actionLoading,
        triggerNow,
        skipStep
    } = useFollowupPipeline(lead, webhook);

    // Estado do Modal de Confirmação
    const [confirmModalConfig, setConfirmModalConfig] = useState({
        isOpen: false,
        actionType: null, // 'trigger_now' | 'skip_step'
        targetStep: null
    });

    const handleOpenTriggerNow = (step) => {
        setConfirmModalConfig({
            isOpen: true,
            actionType: 'trigger_now',
            targetStep: step
        });
    };

    const handleOpenSkipStep = (step) => {
        setConfirmModalConfig({
            isOpen: true,
            actionType: 'skip_step',
            targetStep: step
        });
    };

    const handleCloseConfirmModal = () => {
        if (actionLoading) return;
        setConfirmModalConfig({
            isOpen: false,
            actionType: null,
            targetStep: null
        });
    };

    const handleExecuteAction = async () => {
        if (!confirmModalConfig.targetStep) return;
        let ok = false;
        if (confirmModalConfig.actionType === 'trigger_now') {
            ok = await triggerNow(confirmModalConfig.targetStep);
        } else if (confirmModalConfig.actionType === 'skip_step') {
            ok = await skipStep(confirmModalConfig.targetStep);
        }
        if (ok) {
            handleCloseConfirmModal();
        }
    };

    const overallStatus = pipelineData?.overall_status || 'pending';
    const steps = pipelineData?.steps || [];
    const leadInfo = pipelineData?.lead || lead;
    const webhookInfo = pipelineData?.webhook || webhook;

    return (
        <div className="premium-modal-overlay animate-fade-in" style={{ zIndex: 10000 }}>
            <div 
                className="premium-modal-content"
                style={{
                    maxWidth: '850px',
                    maxHeight: '90vh',
                    display: 'flex',
                    flexDirection: 'column',
                    background: '#0d1117',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
                    borderRadius: '16px'
                }}
            >
                {/* Header & Status Bar */}
                <PipelineHeader
                    webhookInfo={webhookInfo}
                    leadInfo={leadInfo}
                    pipelineData={pipelineData}
                    overallStatus={overallStatus}
                    onClose={onClose}
                    onRefresh={fetchPipeline}
                    loading={loading}
                />

                {/* Body Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '1.75rem' }}>
                    {loading && (
                        <div style={{ textAlign: 'center', padding: '3rem 0', color: '#94a3b8' }}>
                            <div className="spinner" style={{ margin: '0 auto 1rem', width: '32px', height: '32px' }}></div>
                            <p>Carregando linha do tempo de follow-up...</p>
                        </div>
                    )}

                    {error && !loading && (
                        <div style={{ padding: '1.25rem', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171', textAlign: 'center' }}>
                            ⚠️ {error}
                        </div>
                    )}

                    {!loading && !error && steps.length === 0 && (
                        <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#94a3b8' }}>
                            <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: '0.75rem' }}>📭</span>
                            <h4 style={{ color: '#f1f5f9', margin: '0 0 0.5rem' }}>Nenhum Passo de Follow-Up Configurado</h4>
                            <p style={{ fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto' }}>
                                Para ativar disparos automáticos, configure os passos na aba "Follow-Up" ao editar esta integração.
                            </p>
                        </div>
                    )}

                    {!loading && !error && steps.length > 0 && (
                        <div className="pipeline-timeline" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', position: 'relative' }}>
                            {steps.map((step, index) => (
                                <PipelineStepItem
                                    key={index}
                                    step={step}
                                    index={index}
                                    isLast={index === steps.length - 1}
                                    onTriggerNow={handleOpenTriggerNow}
                                    onSkipStep={handleOpenSkipStep}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{ padding: '1.25rem 1.75rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', justifyContent: 'flex-end', background: '#0a0d14' }}>
                    <button 
                        type="button" 
                        onClick={onClose} 
                        className="btn-action-edit"
                        style={{ padding: '0.6rem 1.5rem', borderRadius: '8px', cursor: 'pointer' }}
                    >
                        Fechar
                    </button>
                </div>
            </div>

            {/* Popup Centralizado de Confirmação de Ações Manuais */}
            <FollowupActionConfirmModal
                isOpen={confirmModalConfig.isOpen}
                actionType={confirmModalConfig.actionType}
                stepNumber={confirmModalConfig.targetStep?.step_number || (leadInfo?.followup_step !== undefined ? leadInfo.followup_step + 1 : 1)}
                leadName={leadInfo?.contato_nome || leadInfo?.nome || leadInfo?.telefone}
                loading={actionLoading}
                onConfirm={handleExecuteAction}
                onClose={handleCloseConfirmModal}
            />
        </div>
    );
};

export default FollowupPipelineModal;
