import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../api/client';
import { showToast } from '../../utils/helpers';

export const useFollowupPipeline = (lead, webhook) => {
    const [pipelineData, setPipelineData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchPipeline = useCallback(async () => {
        if (!webhook?.id || !lead?.id) return;
        setLoading(true);
        setError(null);
        try {
            const res = await api.get(`/webhooks/${webhook.id}/leads/${lead.id}/followup-pipeline`);
            if (!res.ok) {
                throw new Error(`Erro ao carregar dados da pipeline (${res.status})`);
            }
            const data = await res.json();
            setPipelineData(data);
        } catch (e) {
            console.error('Erro ao buscar pipeline de follow-up:', e);
            setError(e.message || 'Erro ao carregar pipeline de follow-up');
            showToast('Erro ao carregar pipeline de follow-up', 'error');
        } finally {
            setLoading(false);
        }
    }, [webhook?.id, lead?.id]);

    useEffect(() => {
        fetchPipeline();
    }, [fetchPipeline]);

    // Bloquear scroll ao abrir o modal
    useEffect(() => {
        const originalStyle = window.getComputedStyle(document.body).overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = originalStyle;
        };
    }, []);

    const [actionLoading, setActionLoading] = useState(false);

    const triggerNow = useCallback(async (step) => {
        if (!webhook?.id || !lead?.id) return;
        setActionLoading(true);
        try {
            const res = await api.post(`/webhooks/${webhook.id}/leads/${lead.id}/followup/trigger-now`, {});
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Falha ao disparar follow-up');
            }
            showToast(data.message || 'Follow-up disparado com sucesso!', 'success');
            await fetchPipeline();
            return true;
        } catch (e) {
            console.error('Erro ao disparar follow-up imediatamente:', e);
            showToast(e.message || 'Erro ao disparar follow-up', 'error');
            return false;
        } finally {
            setActionLoading(false);
        }
    }, [webhook?.id, lead?.id, fetchPipeline]);

    const skipStep = useCallback(async (step) => {
        if (!webhook?.id || !lead?.id) return;
        setActionLoading(true);
        try {
            const res = await api.post(`/webhooks/${webhook.id}/leads/${lead.id}/followup/skip-step`, {});
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Falha ao pular passo de follow-up');
            }
            showToast(data.message || 'Passo pulado com sucesso!', 'success');
            await fetchPipeline();
            return true;
        } catch (e) {
            console.error('Erro ao pular passo de follow-up:', e);
            showToast(e.message || 'Erro ao pular passo', 'error');
            return false;
        } finally {
            setActionLoading(false);
        }
    }, [webhook?.id, lead?.id, fetchPipeline]);

    return {
        pipelineData,
        loading,
        error,
        fetchPipeline,
        actionLoading,
        triggerNow,
        skipStep
    };
};

