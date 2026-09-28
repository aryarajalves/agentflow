import React, { useEffect, useState } from 'react';
import LeadFilterBar from './LeadFilterBar';
import LeadCard from './LeadCard';
import LeadSelectionBar from './LeadSelectionBar';
import LeadsModalHeader from './LeadsModal/LeadsModalHeader';
import LeadsModalPagination from './LeadsModal/LeadsModalPagination';
import LeadsSubModals from './LeadsModal/LeadsSubModals';

const LeadsModal = ({
    leadsModal,
    onClose,
    onSearch,
    onFilterChange,
    onPageChange,
    selectedLeads,
    toggleSelectLead,
    toggleSelectAllLeads,
    onSelectAllTotal,
    onClearSelection,
    isSelectingAllTotal = false,
    onBulkDelete,
    onDeleteLead,
    onSyncAll,
    isSyncing,
    onImportChat,
    onCancelImport,
    isCancellingImport = false,
    importProgress,
    onCloseImportProgress,
    onOpenImportProgress,
    isStartingImport = false,
    onViewHistory
}) => {
    const { 
        leads = [], 
        total = 0, 
        loading = false, 
        page = 1, 
        pageSize = 20, 
        search = '', 
        podeEnviar = 'all', 
        dateStart = '', 
        dateEnd = '', 
        janelaAberta = 'all', 
        semMensagens = 'all' 
    } = leadsModal;

    const safeLeads = Array.isArray(leads) ? leads : [];

    const isImportRunning = Boolean(
        !importProgress?.done && !importProgress?.error &&
        (importProgress?.total > 0 || (importProgress?.status && importProgress.status.includes('...')))
    );

    // Estado local para controlar qual card está expandido (apenas 1 por vez - Accordion)
    const [expandedLeadId, setExpandedLeadId] = useState(null);
    const [pipelineEvent, setPipelineEvent] = useState(null);
    const [followupLead, setFollowupLead] = useState(null);
    const [selectedLeadForVariables, setSelectedLeadForVariables] = useState(null);
    const [showConfirmImport, setShowConfirmImport] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());

    // Timer para atualizar contagens regressivas
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const getRemainingTime = (lastInteraction) => {
        if (!lastInteraction) return 'Expirado';
        const dateStr = lastInteraction.includes('T') && !lastInteraction.endsWith('Z') && !lastInteraction.includes('+')
            ? `${lastInteraction}Z`
            : lastInteraction;
        
        const lastDate = new Date(dateStr);
        const expiryDate = new Date(lastDate.getTime() + 24 * 60 * 60 * 1000);
        const diff = expiryDate - currentTime;
        
        if (diff <= 0) return 'Expirado';
        
        const h = Math.floor(diff / (1000 * 60 * 60));
        const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const s = Math.floor((diff % (1000 * 60)) / 1000);
        return `${h}h ${m}m ${s}s`;
    };

    // Bloquear scroll ao montar o modal e limpar seleção apenas ao desmontar (fechar modal)
    const onClearSelectionRef = React.useRef(onClearSelection);
    useEffect(() => {
        onClearSelectionRef.current = onClearSelection;
    }, [onClearSelection]);

    useEffect(() => {
        const originalStyle = window.getComputedStyle(document.body).overflow;
        document.body.style.overflow = 'hidden';
        return () => { 
            document.body.style.overflow = originalStyle;
            if (onClearSelectionRef.current) onClearSelectionRef.current();
        };
    }, []);

    const toggleExpandLead = (id) => {
        setExpandedLeadId(prev => prev === id ? null : id);
    };

    return (
        <div className="premium-modal-overlay">
            <div
                className="premium-modal-content"
                style={{ maxWidth: '1100px', height: '90vh', maxHeight: '950px', display: 'flex', flexDirection: 'column' }}
                onClick={e => e.stopPropagation()}
            >
                {/* Cabeçalho e Banner de Progresso */}
                <LeadsModalHeader
                    total={total}
                    onSyncAll={onSyncAll}
                    isSyncing={isSyncing}
                    isImportRunning={isImportRunning}
                    isStartingImport={isStartingImport}
                    importProgress={importProgress}
                    onOpenImportProgress={onOpenImportProgress}
                    setShowConfirmImport={setShowConfirmImport}
                    onClose={onClose}
                />

                {/* Filtros - Componente Modular de Alto Contraste */}
                <LeadFilterBar
                    search={search}
                    onSearch={onSearch}
                    podeEnviar={podeEnviar}
                    janelaAberta={janelaAberta}
                    semMensagens={semMensagens}
                    dateStart={dateStart}
                    dateEnd={dateEnd}
                    onFilterChange={onFilterChange}
                />

                {/* Barra de Seleção em Massa (Página e Total) */}
                <LeadSelectionBar
                    safeLeads={safeLeads}
                    total={total}
                    selectedLeads={selectedLeads}
                    toggleSelectAllLeads={toggleSelectAllLeads}
                    onSelectAllTotal={onSelectAllTotal}
                    onClearSelection={onClearSelection}
                    isSelectingAllTotal={isSelectingAllTotal}
                    onBulkDelete={onBulkDelete}
                />

                {/* Lista de Cards - Área de Scroll */}
                <div 
                    className="custom-scrollbar"
                    style={{ flex: 1, overflowY: 'auto', padding: '1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', background: 'rgba(0,0,0,0.1)' }}
                >
                    {loading ? (
                        <div style={{ padding: '6rem 0', textAlign: 'center', color: '#64748b' }}>Carregando...</div>
                    ) : safeLeads.length === 0 ? (
                        <div style={{ padding: '6rem 0', textAlign: 'center', color: '#64748b' }}>Nenhum contato encontrado.</div>
                    ) : safeLeads.map(l => (
                        <LeadCard
                            key={l.id}
                            lead={l}
                            isExpanded={expandedLeadId === l.id}
                            isSelected={selectedLeads?.has(l.id)}
                            onToggleExpand={toggleExpandLead}
                            onToggleSelect={toggleSelectLead}
                            onViewHistory={onViewHistory}
                            onViewFollowupPipeline={(lead) => setFollowupLead(lead)}
                            onViewVariables={(lead) => setSelectedLeadForVariables(lead)}
                            onDeleteLead={onDeleteLead}
                            getRemainingTime={getRemainingTime}
                        />
                    ))}
                </div>

                {/* Rodapé: Paginação */}
                <LeadsModalPagination
                    pageSize={pageSize}
                    page={page}
                    total={total}
                    loading={loading}
                    onFilterChange={onFilterChange}
                    onPageChange={onPageChange}
                />

                {/* Modais Auxiliares e Confirmações */}
                <LeadsSubModals
                    webhook={leadsModal?.webhook}
                    pipelineEvent={pipelineEvent}
                    setPipelineEvent={setPipelineEvent}
                    followupLead={followupLead}
                    setFollowupLead={setFollowupLead}
                    selectedLeadForVariables={selectedLeadForVariables}
                    setSelectedLeadForVariables={setSelectedLeadForVariables}
                    importProgress={importProgress}
                    onCloseImportProgress={onCloseImportProgress}
                    onCancelImport={onCancelImport}
                    isCancellingImport={isCancellingImport}
                    showConfirmImport={showConfirmImport}
                    setShowConfirmImport={setShowConfirmImport}
                    onImportChat={onImportChat}
                />
            </div>
        </div>
    );
};

export default LeadsModal;
