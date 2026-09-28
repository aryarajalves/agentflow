import React from 'react';

const LeadSelectionBar = ({
    safeLeads = [],
    total = 0,
    selectedLeads = new Set(),
    toggleSelectAllLeads,
    onSelectAllTotal,
    onClearSelection,
    isSelectingAllTotal = false,
    onBulkDelete
}) => {
    const isAllOnPageSelected = safeLeads.length > 0 && safeLeads.every(l => selectedLeads?.has(l.id));
    const isAllTotalSelected = total > 0 && selectedLeads?.size === total;
    const hasSelection = selectedLeads?.size > 0;
    const hasMoreThanPage = total > safeLeads.length;

    return (
        <div style={{
            padding: '0.65rem 1.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem',
            background: hasSelection ? 'rgba(239, 68, 68, 0.08)' : 'rgba(255,255,255,0.01)',
            transition: 'all 0.2s ease'
        }}>
            {/* Checkbox de Selecionar Página Atual */}
            <div 
                onClick={() => toggleSelectAllLeads()}
                title={isAllOnPageSelected ? "Desmarcar contatos da página" : "Selecionar contatos da página atual"}
                style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', userSelect: 'none', gap: '0.6rem' }}
            >
                <div
                    style={{
                        width: '24px', height: '24px', borderRadius: '7px', 
                        border: `2px solid ${(isAllOnPageSelected || isAllTotalSelected) ? '#6366f1' : 'rgba(255,255,255,0.3)'}`,
                        background: (isAllOnPageSelected || isAllTotalSelected) ? '#6366f1' : 'rgba(255,255,255,0.05)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        boxShadow: (isAllOnPageSelected || isAllTotalSelected) ? '0 0 12px rgba(99, 102, 241, 0.5)' : 'none',
                        transition: 'all 0.2s ease',
                        flexShrink: 0
                    }}
                >
                    {(isAllOnPageSelected || isAllTotalSelected) && <span style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 800 }}>✓</span>}
                </div>
                <span 
                    style={{ fontSize: '0.85rem', color: '#cbd5e1', fontWeight: 700 }}
                >
                    Selecionar Todos
                </span>
            </div>

            {/* Opção para Selecionar Todos os Contatos do Total (Todas as páginas) */}
            {hasMoreThanPage && !isAllTotalSelected && (
                <button
                    type="button"
                    onClick={onSelectAllTotal}
                    disabled={isSelectingAllTotal}
                    style={{
                        background: isAllOnPageSelected ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                        border: isAllOnPageSelected ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid rgba(255, 255, 255, 0.1)',
                        color: isAllOnPageSelected ? '#a5b4fc' : '#94a3b8',
                        borderRadius: '6px',
                        padding: '0.25rem 0.65rem',
                        cursor: isSelectingAllTotal ? 'not-allowed' : 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        transition: 'all 0.2s ease'
                    }}
                >
                    {isSelectingAllTotal ? (
                        <>
                            <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⏳</span>
                            Selecionando {total}...
                        </>
                    ) : (
                        <>
                            <span>👉</span> Selecionar todos os {total} contatos
                        </>
                    )}
                </button>
            )}

            {/* Aviso de que todos do total estão selecionados */}
            {isAllTotalSelected && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#818cf8', fontWeight: 700 }}>
                        ✨ Todos os {total} contatos selecionados
                    </span>
                    <button
                        type="button"
                        onClick={onClearSelection}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#94a3b8',
                            textDecoration: 'underline',
                            fontSize: '0.75rem',
                            cursor: 'pointer',
                            padding: '0 4px'
                        }}
                    >
                        Desmarcar todos
                    </button>
                </div>
            )}

            {/* Botão de Excluir em Massa para Contatos Selecionados */}
            {hasSelection && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#f87171' }}>
                        ({selectedLeads.size} {selectedLeads.size === 1 ? 'contato selecionado' : 'contatos selecionados'})
                    </span>
                    <button
                        type="button"
                        onClick={onBulkDelete}
                        style={{
                            background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                            boxShadow: '0 4px 14px rgba(239, 68, 68, 0.35)',
                            border: '1.5px solid rgba(255, 255, 255, 0.15)',
                            color: '#ffffff',
                            borderRadius: '8px',
                            padding: '0.45rem 1.1rem',
                            cursor: 'pointer',
                            fontSize: '0.82rem',
                            fontWeight: 800,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            transition: 'all 0.2s ease'
                        }}
                    >
                        🗑️ Excluir Selecionados
                    </button>
                </div>
            )}

            <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#64748b' }}>
                Dica: Clique no contato para ver detalhes
            </span>
        </div>
    );
};

export default LeadSelectionBar;
