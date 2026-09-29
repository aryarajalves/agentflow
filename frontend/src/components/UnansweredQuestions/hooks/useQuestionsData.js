import { useEffect, useCallback, useRef } from 'react';
import { useQuestions } from '../QuestionsContext';
import { api } from '../../../api/client';
import { API_URL } from '../../../config';

export const useQuestionsData = () => {
    const { 
        setQuestions, setLoading, setKbList, setAgents, 
        setPublicToken, setSelectedKbId, setSelectedAgentId,
        limit, page, setTotalCount, setSelectedIds, setIsLiveConnected,
        filterAgentId, filterPhone, filterDateStart, filterDateEnd, filterSource
    } = useQuestions();

    const isFetchingRef = useRef(false);

    const fetchQuestions = useCallback(async (isSilent = false) => {
        if (!isSilent) setLoading(true);
        // Reseta os selecionados na atualização/mudança de página apenas se não for atualização silenciosa
        if (!isSilent) setSelectedIds(new Set());
        isFetchingRef.current = true;
        try {
            const offset = (page - 1) * limit;
            const queryParams = new URLSearchParams({
                status: 'PENDENTE',
                limit: limit.toString(),
                offset: offset.toString()
            });

            if (filterAgentId) queryParams.append('agent_id', filterAgentId);
            if (filterPhone && filterPhone.trim()) queryParams.append('phone', filterPhone.trim());
            if (filterDateStart) queryParams.append('date_start', filterDateStart);
            if (filterDateEnd) queryParams.append('date_end', filterDateEnd);
            if (filterSource) queryParams.append('source', filterSource);

            const [kbRes, uqRes, agentsRes, settingsRes] = await Promise.all([
                api.get('/knowledge-bases'),
                api.get(`/unanswered-questions?${queryParams.toString()}`),
                api.get('/agents'),
                api.get('/settings/public-tokens')
            ]);

            const kbData = await kbRes.json();
            setKbList(kbData);
            if (kbData.length > 0) setSelectedKbId(prev => prev || kbData[0].id);

            const uqData = await uqRes.json();
            if (uqData.success) {
                setQuestions(uqData.items);
                setTotalCount(uqData.total);
            }

            const agentsData = await agentsRes.json();
            setAgents(agentsData);
            if (agentsData.length > 0) setSelectedAgentId(prev => prev || agentsData[0].id);

            if (settingsRes.ok) {
                const settings = await settingsRes.json();
                setPublicToken(settings.PUBLIC_ACCESS_TOKEN_UNANSWERED || '');
            }
        } catch (err) {
            console.error("Erro ao buscar dados do Inbox", err);
        } finally {
            isFetchingRef.current = false;
            if (!isSilent) setLoading(false);
        }
    }, [
        setQuestions, setLoading, setKbList, setAgents, setPublicToken, 
        setSelectedKbId, setSelectedAgentId, limit, page, setTotalCount, setSelectedIds,
        filterAgentId, filterPhone, filterDateStart, filterDateEnd, filterSource
    ]);

    useEffect(() => {
        fetchQuestions(false);
    }, [fetchQuestions]);

    // Conexão WebSocket para escutar e atualizar o Inbox de Dúvidas em tempo real
    useEffect(() => {
        let ws = null;
        let reconnectTimer = null;
        let debounceTimer = null;
        let isMounted = true;

        const connectWS = () => {
            if (!isMounted) return;
            try {
                const wsUrl = API_URL.replace('http', 'ws') + '/ws/events';
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    if (isMounted) {
                        setIsLiveConnected(true);
                    }
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        // Se receber evento de nova dúvida, dúvida respondida ou descartada
                        const isQuestionEvent = (
                            data.type === 'unanswered_question_created' ||
                            data.type === 'unanswered_question_updated' ||
                            data.type === 'unanswered_question_bulk_discarded'
                        );

                        if (isQuestionEvent) {
                            if (debounceTimer) clearTimeout(debounceTimer);
                            debounceTimer = setTimeout(() => {
                                if (isMounted) {
                                    fetchQuestions(true);
                                }
                            }, 300);
                        }
                    } catch (e) {
                        // ignore json parse error
                    }
                };

                ws.onclose = () => {
                    if (isMounted) {
                        setIsLiveConnected(false);
                        if (reconnectTimer) clearTimeout(reconnectTimer);
                        reconnectTimer = setTimeout(connectWS, 4000);
                    }
                };

                ws.onerror = () => {
                    if (ws) ws.close();
                };
            } catch (err) {
                console.warn('Erro ao conectar WebSocket no Inbox:', err);
            }
        };

        connectWS();

        return () => {
            isMounted = false;
            if (debounceTimer) clearTimeout(debounceTimer);
            if (reconnectTimer) clearTimeout(reconnectTimer);
            if (ws) {
                ws.onclose = null;
                ws.close();
            }
        };
    }, [fetchQuestions, setIsLiveConnected]);

    return { fetchQuestions };
};
