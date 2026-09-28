import { useState, useCallback } from 'react';
import { api } from '../../../../api/client';
import { showToast } from '../../utils/helpers';

export const useLeadsSelection = (leadsModal) => {
    const [selectedLeads, setSelectedLeads] = useState(new Set());
    const [isSelectingAllTotal, setIsSelectingAllTotal] = useState(false);

    const toggleSelectLead = useCallback((id) => {
        setSelectedLeads(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }, []);

    const toggleSelectAllLeads = useCallback((force) => {
        if (!leadsModal?.leads) return;
        const allIdsOnPage = leadsModal.leads.map(l => l.id);

        setSelectedLeads(prev => {
            const allSelected = typeof force === 'boolean' ? !force : allIdsOnPage.every(id => prev.has(id));
            const next = new Set(prev);
            if (allSelected) {
                allIdsOnPage.forEach(id => next.delete(id));
            } else {
                allIdsOnPage.forEach(id => next.add(id));
            }
            return next;
        });
    }, [leadsModal?.leads]);

    const handleSelectAllTotalLeads = useCallback(async () => {
        const webhook = leadsModal?.webhook;
        if (!webhook) return;
        setIsSelectingAllTotal(true);
        try {
            let url = `/webhooks/${webhook.id}/leads/ids?`;
            if (leadsModal?.search) url += `&q=${encodeURIComponent(leadsModal.search)}`;
            if (leadsModal?.podeEnviar && leadsModal.podeEnviar !== 'all') url += `&pode_enviar=${leadsModal.podeEnviar === 'true'}`;
            if (leadsModal?.janelaAberta && leadsModal.janelaAberta !== 'all') url += `&janela_aberta=${leadsModal.janelaAberta === 'true'}`;
            if (leadsModal?.semMensagens && leadsModal.semMensagens !== 'all') url += `&sem_mensagem=${leadsModal.semMensagens === 'true'}`;
            if (leadsModal?.dateStart) url += `&date_start=${leadsModal.dateStart}`;
            if (leadsModal?.dateEnd) url += `&date_end=${leadsModal.dateEnd}`;

            const res = await api.get(url);
            const data = await res.json();
            
            if (res.ok && Array.isArray(data.ids)) {
                setSelectedLeads(new Set(data.ids));
                showToast(`✨ ${data.ids.length} contatos selecionados.`);
            } else {
                showToast('Erro ao selecionar todos os contatos', 'error');
            }
        } catch (e) {
            console.error('Erro ao buscar todos os IDs:', e);
            showToast('Erro ao selecionar todos os contatos', 'error');
        } finally {
            setIsSelectingAllTotal(false);
        }
    }, [
        leadsModal?.webhook,
        leadsModal?.search,
        leadsModal?.podeEnviar,
        leadsModal?.janelaAberta,
        leadsModal?.semMensagens,
        leadsModal?.dateStart,
        leadsModal?.dateEnd
    ]);

    const handleClearAllSelectedLeads = useCallback(() => {
        setSelectedLeads(new Set());
    }, []);

    return {
        selectedLeads,
        setSelectedLeads,
        isSelectingAllTotal,
        toggleSelectLead,
        toggleSelectAllLeads,
        handleSelectAllTotalLeads,
        handleClearAllSelectedLeads
    };
};
