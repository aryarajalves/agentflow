import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { api } from '../../../../../api/client';
import { API_URL } from '../../../../../config';
import { showToast } from '../../../utils/helpers';

export const useLeadHistoryEvents = (lead, webhook) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(20);
    const [confirmDelete, setConfirmDelete] = useState({ isOpen: false, eventId: null });
    const [confirmRetry, setConfirmRetry] = useState({ isOpen: false, eventId: null });
    const [retryingEvents, setRetryingEvents] = useState(new Set());

    const fetchLeadHistory = useCallback(async () => {
        if (!webhook || !webhook.id) return;
        setLoading(true);
        try {
            const cleanPhone = (lead?.telefone || '').replace(/\D/g, '');
            const res = await api.get(`/webhooks/${webhook.id}/events?search=${cleanPhone}&page=${page}&limit=${limit}&event_type=all`);
            const data = await res.json();
            setEvents(data.items || data.events || []);
            setTotal(data.total || 0);
        } catch (e) {
            console.error('Erro ao buscar histórico do lead:', e);
        } finally {
            setLoading(false);
        }
    }, [webhook?.id, lead?.telefone, page, limit]);

    useEffect(() => {
        fetchLeadHistory();
    }, [fetchLeadHistory]);

    const handleDeleteEvent = useCallback((eventId) => {
        setConfirmDelete({ isOpen: true, eventId });
    }, []);

    const confirmDeleteEvent = useCallback(async () => {
        try {
            const res = await api.post(`/webhooks/${webhook.id}/events/bulk-delete`, { event_ids: [confirmDelete.eventId] });
            if (res.ok) {
                showToast('Mensagem excluída com sucesso!', 'success');
                fetchLeadHistory();
                setConfirmDelete({ isOpen: false, eventId: null });
            } else {
                showToast('Erro ao excluir mensagem.', 'error');
            }
        } catch (e) {
            console.error('Erro ao excluir evento:', e);
            showToast('Erro ao excluir mensagem.', 'error');
        }
    }, [webhook?.id, confirmDelete.eventId, fetchLeadHistory]);

    const handleRetryEvent = useCallback((eventId) => {
        setConfirmRetry({ isOpen: true, eventId });
    }, []);

    const confirmRetryEvent = useCallback(async () => {
        const eventId = confirmRetry.eventId;
        if (!eventId || retryingEvents.has(eventId)) return;

        setRetryingEvents(prev => {
            const next = new Set(prev);
            next.add(eventId);
            return next;
        });

        setConfirmRetry({ isOpen: false, eventId: null });

        try {
            const res = await api.post(`/webhooks/${webhook.id}/events/${eventId}/retry`);
            if (res.ok) {
                showToast('Automação reiniciada com sucesso! Aguarde a resposta do agente.', 'success');
                fetchLeadHistory();
            } else {
                const errorData = await res.json().catch(() => ({}));
                const errorMsg = errorData.detail || 'Erro ao reiniciar automação.';
                showToast(errorMsg, 'error');
            }
        } catch (e) {
            console.error('Erro ao reiniciar automação:', e);
            showToast('Erro ao reiniciar automação.', 'error');
        } finally {
            setRetryingEvents(prev => {
                const next = new Set(prev);
                next.delete(eventId);
                return next;
            });
        }
    }, [confirmRetry.eventId, retryingEvents, webhook?.id, fetchLeadHistory]);

    // Polling silencioso
    useEffect(() => {
        const hasProcessingEvent = events.some(evt => evt.status === 'processing' || (!evt.agent_response && evt.dono !== 'agente' && evt.dono !== 'bot'));
        if (!hasProcessingEvent) return;

        const interval = setInterval(async () => {
            if (!webhook || !webhook.id) return;
            try {
                const cleanPhone = (lead?.telefone || '').replace('+', '');
                const res = await api.get(`/webhooks/${webhook.id}/events?search=${cleanPhone}&page=${page}&limit=${limit}&event_type=all`);
                const data = await res.json();
                setEvents(data.items || data.events || []);
                setTotal(data.total || 0);
            } catch (e) {
                console.error('Erro no polling silencioso:', e);
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [events, page, limit, webhook, lead?.telefone]);

    // WebSocket com auto-reconexão
    useEffect(() => {
        if (!webhook || !webhook.id) return;
        
        let ws;
        let reconnectTimeout;
        const cleanPhone = (lead?.telefone || '').replace('+', '');
        
        const connectWS = () => {
            const wsUrl = API_URL.replace('http', 'ws') + '/ws/events';
            try {
                ws = new WebSocket(wsUrl);
                
                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'new_event' && data.webhook_id === webhook.id) {
                            if (data.event?.status === 'skipped') return;
                            const eventPhone = (data.event.telefone || '').replace('+', '');
                            if (eventPhone === cleanPhone) {
                                setEvents(prev => {
                                    if (prev.some(e => e.id === data.event.id)) return prev;
                                    return [data.event, ...prev];
                                });
                                setTotal(prev => prev + 1);
                            }
                        } else if (data.type === 'status_update' && data.webhook_id === webhook.id) {
                            setEvents(prev => prev.map(evt => {
                                if (evt.id === data.event_id) {
                                    return {
                                        ...evt,
                                        status: data.status,
                                        processing_steps: JSON.stringify(data.steps)
                                    };
                                }
                                return evt;
                            }));

                            if (['completed', 'error', 'ignored'].includes(data.status)) {
                                api.get(`/webhooks/${webhook.id}/events/${data.event_id}`)
                                    .then(res => res.json())
                                    .then(updatedEvent => {
                                        setEvents(prev => prev.map(evt => {
                                            if (evt.id === data.event_id) {
                                                return {
                                                    ...evt,
                                                    ...updatedEvent
                                                };
                                            }
                                            return evt;
                                        }));
                                    })
                                    .catch(err => console.error("Erro ao buscar detalhes do evento pós-update:", err));
                            }
                        }
                    } catch (e) {
                        console.error('Erro ao processar mensagem WS:', e);
                    }
                };

                ws.onclose = () => {
                    reconnectTimeout = setTimeout(connectWS, 5000);
                };

                ws.onerror = (err) => {
                    console.error('Erro WS:', err);
                    ws.close();
                };
            } catch (e) {
                console.error('Falha ao conectar WS:', e);
                reconnectTimeout = setTimeout(connectWS, 5000);
            }
        };

        connectWS();

        return () => {
            if (ws) {
                ws.onclose = null;
                ws.close();
            }
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
        };
    }, [webhook?.id, lead?.telefone]);

    const getMessageTypeLabel = useCallback((type) => {
        switch (type) {
            case 'template': return '📋 Template';
            case 'image': return '🖼️ Imagem';
            case 'audio': return '🎙️ Áudio';
            case 'video': return '🎥 Vídeo';
            case 'document': return '📄 Doc';
            default: return '📝 Texto';
        }
    }, []);

    // Consolidação de respostas e filtragem de eventos duplicados
    const displayEvents = useMemo(() => {
        if (!events || events.length === 0) return [];

        const isAgentEvent = (e) => e.event_type !== 'followup' && (e.dono === 'agente' || e.dono === 'bot' || e.dono === 'Agente' || e.dono === 'Agente de IA' || e.dono === 'agent');

        const isSystemBadgeEvent = (e) => {
            if (!e) return false;
            if (e.event_type === 'followup') return false;
            if (e.message_type === 'template' || e.is_template) return false;
            if (e.sender_type === 'system' || e.message_type === 'funnel_event' || e.message_type === 'system_event') return true;
            const text = (e.mensagem || e.agent_response || e.conteudo || '').toLowerCase().trim();
            if (!text) return false;
            if (text.includes('marcador(es)') && (text.includes('adicionou') || text.includes('removeu') || text.includes('adicionado'))) return true;
            if (text.includes('o atendente') && (text.includes('marcador') || text.includes('adicionou') || text.includes('removeu'))) return true;
            if (text.includes('🚀 funil') || text.includes('funil iniciado') || text.includes('funil em execução')) return true;
            return false;
        };

        const hiddenIds = new Set();
        const responseAdditions = new Map();

        // 1. Identificar eventos de Follow-Up e ocultar webhooks de eco/retorno do ZapVoice com o mesmo texto
        const followupEvents = events.filter(e => e.event_type === 'followup');
        followupEvents.forEach(fu => {
            const fuText = (fu.agent_response || fu.mensagem || '').trim();
            if (!fuText) return;
            const fuTime = new Date(fu.created_at).getTime();

            events.forEach(other => {
                if (other.id === fu.id) return;
                // Se for confirmação de saída do ZapVoice (memory ou message sem input de usuário) com o mesmo texto em +/- 3 minutos
                if (other.event_type === 'memory' || other.message_type === 'template' || isAgentEvent(other)) {
                    const otherText = (other.mensagem || other.agent_response || other.conteudo || '').trim();
                    if (otherText && (otherText === fuText || otherText.includes(fuText) || fuText.includes(otherText))) {
                        const otherTime = new Date(other.created_at).getTime();
                        if (Math.abs(fuTime - otherTime) < 180000) {
                            hiddenIds.add(other.id);
                        }
                    }
                }
            });
        });

        // 1.1 Identificar templates duplicados consecutivos (ex: disparo do ZapVoice + sincronização de memória)
        const templateEvents = events.filter(e => e.message_type === 'template' || e.is_template || (e.agent_response && e.agent_response.includes('Disparo de Template')));
        for (let i = 0; i < templateEvents.length; i++) {
            const tA = templateEvents[i];
            if (hiddenIds.has(tA.id)) continue;
            const txtA = (tA.mensagem || tA.agent_response || tA.conteudo || '').replace(/^Modo Silencioso[^\n]*/i, '').replace(/\s+/g, ' ').trim().toLowerCase();
            if (!txtA) continue;
            const timeA = new Date(tA.created_at).getTime();

            for (let j = i + 1; j < templateEvents.length; j++) {
                const tB = templateEvents[j];
                if (hiddenIds.has(tB.id)) continue;
                if (Math.abs(timeA - new Date(tB.created_at).getTime()) < 180000) {
                    const txtB = (tB.mensagem || tB.agent_response || tB.conteudo || '').replace(/^Modo Silencioso[^\n]*/i, '').replace(/\s+/g, ' ').trim().toLowerCase();
                    if (txtB && (txtA === txtB || txtA.includes(txtB) || txtB.includes(txtA))) {
                        const bHasMedia = (tB.mensagem || '').includes('[Conteúdo da Mídia');
                        const aHasMedia = (tA.mensagem || '').includes('[Conteúdo da Mídia');
                        hiddenIds.add(bHasMedia && !aHasMedia ? tA.id : tB.id);
                    }
                }
            }
        }

        // 2. Agrupamento de respostas imediatas do agente (apenas se geradas na MESMA interação imediata, < 15s)
        for (let i = 0; i < events.length; i++) {
            const current = events[i];
            const isAgentCurrent = isAgentEvent(current);

            if (!isAgentCurrent && current.event_type !== 'followup' && (current.mensagem || current.conteudo)) {
                let additions = '';
                const currentTime = new Date(current.created_at).getTime();

                for (let j = i - 1; j >= 0; j--) {
                    const prev = events[j];
                    if (prev.event_type === 'followup' || prev.message_type === 'template' || prev.is_template) break;
                    
                    const isPrevUser = !isAgentEvent(prev) && (prev.dono === 'usuario' || prev.dono === 'cliente' || (!prev.dono && prev.event_type !== 'memory'));
                    if (isPrevUser) break;

                    const prevTime = new Date(prev.created_at).getTime();
                    // Só agrupa se a resposta do agente foi emitida até 15 segundos da mensagem do usuário
                    if (Math.abs(prevTime - currentTime) > 15000) break;

                    if (isAgentEvent(prev)) {
                        const prevText = (prev.mensagem || prev.agent_response || prev.conteudo || '').trim();
                        if (prevText) {
                            const curResp = (current.agent_response || '').trim();
                            if (!curResp.includes(prevText) && !additions.includes(prevText)) {
                                additions += (additions ? '\n\n' : '') + prevText;
                            }
                            hiddenIds.add(prev.id);
                        }
                    }
                }

                if (additions) {
                    responseAdditions.set(current.id, additions);
                }
            }
        }

        return events
            .filter(evt => {
                if (hiddenIds.has(evt.id)) return false;
                if (isSystemBadgeEvent(evt)) return false;
                if (evt.event_type === 'followup') return true;
                if (evt.message_type === 'template' || evt.is_template) return true;
                const isAgent = isAgentEvent(evt);
                if (isAgent) {
                    const text = (evt.mensagem || evt.agent_response || '').trim();
                    const isPartOfSomeResponse = events.some(other => 
                        other.id !== evt.id && 
                        !hiddenIds.has(other.id) &&
                        other.agent_response && 
                        other.agent_response.includes(text)
                    );
                    if (isPartOfSomeResponse) return false;
                }
                return true;
            })
            .map(evt => {
                const add = responseAdditions.get(evt.id);
                if (add) {
                    const base = (evt.agent_response || '').trim();
                    return {
                        ...evt,
                        agent_response: base ? `${base}\n\n${add}` : add
                    };
                }
                return evt;
            });
    }, [events]);

    return {
        events,
        displayEvents,
        loading,
        total,
        page,
        setPage,
        limit,
        setLimit,
        fetchLeadHistory,
        confirmDelete,
        setConfirmDelete,
        confirmRetry,
        setConfirmRetry,
        retryingEvents,
        handleDeleteEvent,
        confirmDeleteEvent,
        handleRetryEvent,
        confirmRetryEvent,
        getMessageTypeLabel
    };
};
