import React from 'react';
import { formatDate } from '../utils/helpers';

export const parseLabels = (labelsField) => {
    if (!labelsField) return [];
    if (Array.isArray(labelsField)) return labelsField;
    if (typeof labelsField === 'string') {
        try {
            const parsed = JSON.parse(labelsField);
            if (Array.isArray(parsed)) return parsed;
            return [labelsField];
        } catch (e) {
            if (labelsField.startsWith('[') && labelsField.endsWith(']')) {
                return [];
            }
            return [labelsField];
        }
    }
    return [];
};

const LeadCard = ({
    lead: l,
    isExpanded,
    isSelected,
    onToggleExpand,
    onToggleSelect,
    onViewHistory,
    onViewFollowupPipeline,
    onViewVariables,
    onDeleteLead,
    getRemainingTime
}) => {
    return (
        <div className="lead-card-premium" style={{
            background: isExpanded ? 'rgba(30, 41, 59, 0.7)' : 'rgba(15, 23, 42, 0.3)',
            border: `1px solid ${isSelected ? 'rgba(99, 102, 241, 0.6)' : isExpanded ? 'rgba(99, 102, 241, 0.3)' : 'rgba(255,255,255,0.03)'}`,
            borderRadius: '16px', padding: '1rem 1.25rem',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: isExpanded ? '0 20px 40px -15px rgba(0,0,0,0.6)' : 'none',
            marginBottom: isExpanded ? '0.5rem' : '0'
        }}>
            {/* Top Info - Clicável para expandir */}
            <div
                onClick={() => onToggleExpand(l.id)}
                style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer', alignItems: 'center' }}
            >
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {/* Seleção Individual à Esquerda */}
                    <div
                        onClick={(e) => { e.stopPropagation(); onToggleSelect(l.id); }}
                        title={isSelected ? "Desmarcar contato" : "Selecionar contato"}
                        data-testid={`lead-select-checkbox-${l.id}`}
                        style={{
                            width: '24px', height: '24px', borderRadius: '7px',
                            border: `2px solid ${isSelected ? '#6366f1' : 'rgba(255,255,255,0.3)'}`,
                            background: isSelected ? '#6366f1' : 'rgba(255,255,255,0.05)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                            boxShadow: isSelected ? '0 0 12px rgba(99, 102, 241, 0.5)' : 'none',
                            flexShrink: 0,
                            transition: 'all 0.2s ease',
                            userSelect: 'none'
                        }}
                    >
                        {isSelected && <span style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 800 }}>✓</span>}
                    </div>

                    <div style={{
                        width: '46px', height: '46px', borderRadius: '14px',
                        background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '1.2rem', color: '#fff', border: '1px solid rgba(255,255,255,0.1)',
                        flexShrink: 0, boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                    }}>
                        {l.contato_nome ? l.contato_nome[0].toUpperCase() : '👤'}
                    </div>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap', rowGap: '0.4rem' }}>
                            <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>{l.contato_nome || '—'}</span>
                            <span style={{ fontSize: '0.65rem', fontWeight: 800, padding: '2px 10px', borderRadius: '20px', background: 'rgba(34, 197, 94, 0.1)', color: '#4ade80', border: '1px solid rgba(34, 197, 94, 0.2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                ● Ativa
                            </span>
                            {l.sem_mensagem_usuario && (
                                <span style={{ fontSize: '0.65rem', fontWeight: 800, padding: '2px 10px', borderRadius: '20px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    ⚠️ Sem Mensagens
                                </span>
                            )}
                             <span style={{ fontSize: '0.7rem', fontWeight: 600, color: l.janela_24h_aberta ? '#4ade80' : '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                ⏰ {l.janela_24h_aberta ? `Aberta (${getRemainingTime(l.ultima_mensagem_em)})` : 'Fechada'}
                            </span>
                            {l.total_disparos > 0 && (
                                <span style={{
                                    fontSize: '0.65rem', fontWeight: 800, padding: '2px 12px', borderRadius: '20px',
                                    background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.2)'
                                }}>
                                    {l.total_disparos} disparos
                                </span>
                            )}
                            {l.active_followup_funnel_id && (
                                <span style={{
                                    fontSize: '0.65rem', fontWeight: 800, padding: '2px 10px', borderRadius: '20px',
                                    background: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.3)',
                                    textTransform: 'uppercase', letterSpacing: '0.05em'
                                }} title={`Funil de Follow-Up: ${l.active_followup_funnel_id}`}>
                                    📦 {l.active_followup_funnel_id}
                                </span>
                            )}
                            {l.message_type === 'audio' && (
                                <span title="Última mensagem foi um áudio" style={{ fontSize: '1rem' }}>🎤</span>
                            )}
                            {l.message_type === 'image' && (
                                <span title="Última mensagem foi uma imagem" style={{ fontSize: '1rem' }}>🖼️</span>
                            )}
                            <span style={{ fontSize: '0.9rem', color: isExpanded ? '#6366f1' : '#475569', transition: 'transform 0.3s ease', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                                ▼
                            </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginTop: '0.6rem' }}>
                            <div style={{ fontSize: '0.9rem', color: '#6366f1', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>{l.telefone}</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap', rowGap: '0.4rem' }}>
                            {parseLabels(l.labels).map((label, idx) => (
                                <span
                                    key={idx} 
                                    style={{
                                        fontSize: '0.65rem', 
                                        fontWeight: 700, 
                                        padding: '3px 10px',
                                        borderRadius: '12px',
                                        background: 'rgba(99, 102, 241, 0.15)', 
                                        color: '#a5b4fc', 
                                        border: '1px solid rgba(99, 102, 241, 0.25)', 
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        gap: '4px',
                                        backdropFilter: 'blur(4px)'
                                    }}
                                >
                                    🏷️ {label}
                                </span>
                            ))}
                            </div>
                        </div>
                    </div>
                </div>
                <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                    {!isExpanded && (
                        <div style={{ fontSize: '0.75rem', color: '#64748b', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', fontStyle: 'italic' }}>
                            Última: {l.mensagem || '—'}
                        </div>
                    )}
                    <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                        <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); onViewFollowupPipeline && onViewFollowupPipeline(l); }}
                            className="btn-action-history"
                            style={{ borderRadius: '10px', padding: '0.5rem 0.85rem', fontSize: '0.8rem', fontWeight: 700, background: 'rgba(99, 102, 241, 0.12)', borderColor: 'rgba(99, 102, 241, 0.25)', color: '#a5b4fc' }}
                            title="Ver Pipeline de Follow-Up deste contato"
                        ><span>⏱️</span> Follow-up</button>
                        <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); onViewVariables && onViewVariables(l); }}
                            className="btn-action-history"
                            style={{ borderRadius: '10px', padding: '0.5rem 0.85rem', fontSize: '0.8rem', fontWeight: 700, background: 'rgba(56, 189, 248, 0.12)', borderColor: 'rgba(56, 189, 248, 0.25)', color: '#38bdf8' }}
                            title="Ver Variáveis capturadas deste contato"
                            data-testid={`lead-vars-btn-${l.id}`}
                        ><span>🌍</span> Variáveis</button>
                        <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); onViewHistory(l); }}
                            className="btn-action-history"
                            style={{ borderRadius: '10px', padding: '0.5rem 1rem', fontSize: '0.8rem', fontWeight: 700 }}
                        ><span>💬</span> Histórico</button>
                        <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); onDeleteLead(l); }}
                            className="btn-action-delete"
                            style={{ borderRadius: '10px', padding: '0.5rem 0.8rem', fontSize: '0.8rem' }}
                        ><span>🗑️</span></button>
                    </div>
                </div>
            </div>

            {/* Conteúdo Expandido - Detalhes Completos */}
            {isExpanded && (
                <div style={{ marginTop: '1.5rem', padding: '0.5rem 0', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
                        {[
                            { label: 'CRIADO EM', value: formatDate(l.created_at), icon: '📅' },
                            { label: 'ID INTERNO', value: l.id, icon: '🆔' },
                            { label: 'ID DO CLIENTE (CLIENT ID)', value: l.inbox_id || '—', icon: '🏦' },
                            { label: 'CONTATO ID', value: l.contato_id || '—', icon: '👤' },
                            { label: 'JANELA 24H', value: getRemainingTime(l.ultima_mensagem_em), icon: '⏰', color: l.janela_24h_aberta ? '#4ade80' : '#ef4444' },
                            { label: 'FLUXO FOLLOW-UP', value: l.active_followup_funnel_id || 'Principal (Padrão)', icon: '📦' },
                            { label: 'TIPO DE MENSAGEM', value: (l.message_type || 'text').toUpperCase(), icon: '🏷️' },
                            { 
                                label: 'LINK DA MÍDIA', 
                                value: l.link ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                        <a href={l.link} target="_blank" rel="noopener noreferrer" style={{ color: '#818cf8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700 }}>
                                            🔗 Abrir Mídia Original ↗
                                        </a>
                                        {(l.message_type === 'audio' || l.link.match(/\.(ogg|mp3|wav|m4a|oga|opus)($|\?)/i)) && (
                                            <audio controls src={l.link} style={{ height: '28px', width: '100%', maxWidth: '220px', outline: 'none', marginTop: '2px' }} />
                                        )}
                                    </div>
                                ) : 'Sem mídia', 
                                icon: '🔗' 
                            },
                            { label: 'ÚLTIMA MENSAGEM DO USUÁRIO', value: l.mensagem || '—', icon: '💬', fullWidth: true },
                            { label: 'ÚLTIMA RESPOSTA DO AGENTE', value: l.ultima_resposta_agente || '—', icon: '🤖', fullWidth: true },
                            { 
                                label: 'ETIQUETAS DO ZAPVOICE', 
                                value: parseLabels(l.labels).length > 0 ? (
                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        {parseLabels(l.labels).map((label, idx) => (
                                            <span 
                                                key={idx} 
                                                style={{
                                                    fontSize: '0.7rem', 
                                                    fontWeight: 700, 
                                                    padding: '2px 10px', 
                                                    borderRadius: '20px',
                                                    background: 'rgba(99, 102, 241, 0.15)', 
                                                    color: '#a5b4fc', 
                                                    border: '1px solid rgba(99, 102, 241, 0.25)',
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: '4px'
                                                }}
                                            >
                                                🏷️ {label}
                                            </span>
                                        ))}
                                    </div>
                                ) : 'Sem etiquetas', 
                                icon: '🏷️', 
                                fullWidth: true 
                            },
                        ].map((item, i) => (
                            <div key={i} style={{ 
                                background: 'rgba(255, 255, 255, 0.03)', 
                                border: '1px solid rgba(255, 255, 255, 0.05)', 
                                borderRadius: '12px', 
                                padding: '0.75rem 1rem',
                                gridColumn: item.fullWidth ? 'span 4' : 'auto',
                                boxShadow: 'inset 0 0 10px rgba(0,0,0,0.1)'
                            }}>
                                <div style={{ fontSize: '0.6rem', fontWeight: 900, color: '#64748b', marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                    <span>{item.icon}</span> {item.label}
                                </div>
                                <div style={{ 
                                    fontSize: '0.85rem', 
                                    color: item.color || '#f1f5f9', 
                                    fontWeight: 600, 
                                    overflow: item.fullWidth ? 'visible' : 'hidden', 
                                    textOverflow: item.fullWidth ? 'unset' : 'ellipsis', 
                                    whiteSpace: item.fullWidth ? 'pre-wrap' : 'nowrap',
                                    lineHeight: 1.5,
                                    maxHeight: item.fullWidth ? '120px' : 'unset',
                                    overflowY: item.fullWidth ? 'auto' : 'unset'
                                }} className="custom-scrollbar">
                                    {item.value}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default LeadCard;
