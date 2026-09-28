import React from 'react';
import { formatDelay, getStatusBadge, formatDateTime, formatRelativeSchedule } from './followupPipelineHelpers';

export const PipelineStepItem = ({ step, index, isLast, onTriggerNow, onSkipStep }) => {
    const badge = getStatusBadge(step.status);
    const isCurrent = step.status === 'active';
    const isDone = step.status === 'completed';
    const isSkipped = step.status === 'skipped';

    return (
        <div 
            style={{
                display: 'flex',
                gap: '1.25rem',
                position: 'relative'
            }}
        >
            {/* Linha vertical conectora */}
            {!isLast && (
                <div 
                    style={{
                        position: 'absolute',
                        left: '19px',
                        top: '40px',
                        bottom: '-25px',
                        width: '2px',
                        background: isDone ? '#10b981' : isSkipped ? '#f59e0b' : 'rgba(255, 255, 255, 0.1)',
                        zIndex: 1
                    }}
                />
            )}

            {/* Node Icon */}
            <div 
                style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: isDone ? '#10b981' : isSkipped ? '#d97706' : isCurrent ? '#3b82f6' : 'rgba(255, 255, 255, 0.05)',
                    border: `2px solid ${isDone ? '#34d399' : isSkipped ? '#fbbf24' : isCurrent ? '#60a5fa' : 'rgba(255, 255, 255, 0.1)'}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: isSkipped ? '0.9rem' : '1rem',
                    fontWeight: 800,
                    color: '#fff',
                    zIndex: 2,
                    boxShadow: isCurrent ? '0 0 15px rgba(59, 130, 246, 0.5)' : isDone ? '0 0 10px rgba(16, 185, 129, 0.3)' : isSkipped ? '0 0 10px rgba(245, 158, 11, 0.3)' : 'none',
                    flexShrink: 0
                }}
            >
                {isDone ? '✓' : isSkipped ? '⏭' : step.step_number}
            </div>

            {/* Card do Step */}
            <div 
                style={{
                    flex: 1,
                    background: isCurrent ? 'rgba(59, 130, 246, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                    border: isCurrent ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '12px',
                    padding: '1.25rem',
                    boxShadow: isCurrent ? '0 4px 20px rgba(59, 130, 246, 0.08)' : 'none'
                }}
            >
                {/* Cabeçalho do Card */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.95rem' }}>
                            Passo {step.step_number}: {formatDelay(step.delay_minutes)}
                        </span>
                        <span style={{
                            fontSize: '0.7rem',
                            padding: '0.15rem 0.5rem',
                            borderRadius: '6px',
                            background: 'rgba(255, 255, 255, 0.06)',
                            color: '#cbd5e1'
                        }}>
                            {step.type === 'ai' ? '🤖 IA Contextual' : step.type === 'fixed' ? '📝 Mensagem Fixa' : step.type === 'whatsapp_template' ? '📱 Template WhatsApp' : '🎙️ Áudio/Mídia'}
                        </span>
                    </div>

                    <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '0.2rem 0.6rem',
                        borderRadius: '6px',
                        background: badge.bg,
                        color: badge.color,
                        border: `1px solid ${badge.border}`
                    }}>
                        {step.is_manual ? '⚡ Disparado Manualmente' : badge.label}
                    </span>
                </div>

                {/* Conteúdo / Instrução do Step */}
                <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                    {step.type === 'ai' && (
                        <div>
                            <span style={{ color: '#64748b' }}>Prompt: </span>
                            <span style={{ color: '#cbd5e1' }}>{step.custom_prompt || 'Gerar continuação inteligente de conversa.'}</span>
                        </div>
                    )}
                    {step.type === 'fixed' && (
                        <div>
                            <span style={{ color: '#64748b' }}>Texto: </span>
                            <span style={{ color: '#cbd5e1' }}>{step.fixed_message || '(Mensagem fixa em branco)'}</span>
                        </div>
                    )}
                    {step.type === 'whatsapp_template' && (
                        <div>
                            <span style={{ color: '#64748b' }}>Template Oficial: </span>
                            <span style={{ color: '#34d399', fontWeight: 600 }}>{step.template_name || '(Não selecionado)'}</span>
                            {step.language && <span style={{ color: '#94a3b8', fontSize: '0.75rem', marginLeft: '0.4rem' }}>({step.language})</span>}
                        </div>
                    )}
                </div>

                {/* Evento disparado ou dispensado (se houver) */}
                {step.dispatched_event && (
                    <div style={{
                        marginTop: '0.75rem',
                        padding: '0.75rem 1rem',
                        background: isSkipped ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                        border: `1px solid ${isSkipped ? 'rgba(245, 158, 11, 0.25)' : 'rgba(16, 185, 129, 0.2)'}`,
                        borderRadius: '8px'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: isSkipped ? '#fbbf24' : '#34d399', marginBottom: '0.35rem' }}>
                            <span>
                                {isSkipped 
                                    ? '⏭️ Passo Dispensado Manualmente' 
                                    : step.is_manual 
                                        ? '⚡ Disparado Manualmente com Sucesso' 
                                        : '🚀 Disparado com Sucesso'}
                            </span>
                            <span>{new Date(step.dispatched_event.created_at).toLocaleString('pt-BR')}</span>
                        </div>
                        {step.dispatched_event.agent_response && (
                            <div style={{ fontSize: '0.82rem', color: '#e2e8f0', background: 'rgba(0, 0, 0, 0.2)', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                                "{step.dispatched_event.agent_response}"
                            </div>
                        )}
                    </div>
                )}

                {/* Informação se este é o passo atual ativo */}
                {isCurrent && (
                    <div style={{
                        marginTop: '0.85rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.6rem'
                    }}>
                        {/* Box de Horários e Previsão */}
                        <div style={{
                            padding: '0.75rem 0.95rem',
                            background: 'rgba(59, 130, 246, 0.08)',
                            border: '1px solid rgba(59, 130, 246, 0.28)',
                            borderRadius: '10px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.45rem',
                            fontSize: '0.78rem'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.4rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', color: '#93c5fd' }}>
                                    <span>⏳</span>
                                    <span><strong>Início da contagem:</strong> {formatDateTime(step.started_at)}</span>
                                </div>
                                {step.estimated_dispatch_at && (
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                        background: 'rgba(59, 130, 246, 0.2)',
                                        padding: '0.2rem 0.55rem',
                                        borderRadius: '6px',
                                        color: '#60a5fa',
                                        fontWeight: 600
                                    }}>
                                        <span>🎯 Previsão:</span>
                                        <span>{formatRelativeSchedule(step.estimated_dispatch_at)}</span>
                                    </div>
                                )}
                            </div>

                            <div style={{ fontSize: '0.73rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                                O sistema efetuará o disparo quando o tempo de inatividade ({formatDelay(step.delay_minutes)}) for concluído dentro do horário comercial permitido.
                            </div>
                        </div>

                        {/* Alerta de Reinício por Mensagem do Usuário */}
                        {step.reset_by_lead_message && (
                            <div style={{
                                padding: '0.6rem 0.85rem',
                                background: 'rgba(245, 158, 11, 0.1)',
                                border: '1px solid rgba(245, 158, 11, 0.3)',
                                borderRadius: '8px',
                                fontSize: '0.75rem',
                                color: '#fcd34d',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem'
                            }}>
                                <span style={{ fontSize: '0.9rem' }}>🔄</span>
                                <span>
                                    <strong>Temporizador reiniciado:</strong> O contato enviou uma nova mensagem em {formatDateTime(step.lead_last_message_at)}. A contagem de inatividade foi zerada e recomeçou a partir deste horário.
                                </span>
                            </div>
                        )}

                        {/* Botões de Ação Manual no Passo Ativo */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            marginTop: '0.25rem',
                            flexWrap: 'wrap'
                        }}>
                            <button
                                type="button"
                                onClick={() => onTriggerNow && onTriggerNow(step)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.45rem',
                                    padding: '0.5rem 0.95rem',
                                    borderRadius: '8px',
                                    background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.3) 100%)',
                                    border: '1px solid rgba(16, 185, 129, 0.4)',
                                    color: '#34d399',
                                    fontSize: '0.78rem',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                                title="Iniciar o disparo imediato da mensagem deste passo para este contato"
                            >
                                <span>🚀</span>
                                <span>Disparar Agora</span>
                            </button>

                            <button
                                type="button"
                                onClick={() => onSkipStep && onSkipStep(step)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.45rem',
                                    padding: '0.5rem 0.95rem',
                                    borderRadius: '8px',
                                    background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.2) 100%)',
                                    border: '1px solid rgba(245, 158, 11, 0.35)',
                                    color: '#fbbf24',
                                    fontSize: '0.78rem',
                                    fontWeight: 700,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                                title="Pular este passo sem enviar mensagem e avançar para o próximo"
                            >
                                <span>⏭️</span>
                                <span>Pular Passo</span>
                            </button>
                        </div>
                    </div>
                )}

                {/* Informação se o passo/ciclo está cancelado */}
                {step.status === 'cancelled' && (
                    <div style={{
                        marginTop: '0.75rem',
                        padding: '0.65rem 0.85rem',
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        fontSize: '0.76rem',
                        color: '#fca5a5',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                    }}>
                        <span style={{ fontSize: '0.9rem' }}>🛑</span>
                        <span>
                            <strong>Disparo Cancelado:</strong> {step.cancellation_reason || 'O ciclo de follow-up foi desativado para este contato.'}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PipelineStepItem;

