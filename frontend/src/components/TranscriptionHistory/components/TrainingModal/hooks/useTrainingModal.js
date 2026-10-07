import { useState, useEffect } from 'react';
import { useTranscription } from '../../../TranscriptionContext';
import { useTranscriptionData } from '../../../hooks/useTranscriptionData';
import { api } from '../../../../../api/client';

export function useTrainingModal() {
    const { 
        isTrainingModalOpen, 
        setIsTrainingModalOpen, 
        taskForTraining, 
        setTaskForTraining,
        knowledgeBases 
    } = useTranscription();

    const { fetchTasks } = useTranscriptionData();

    const [selectedKbId, setSelectedKbId] = useState('');
    const [numQuestions, setNumQuestions] = useState(5);
    const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
    const [models, setModels] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [method, setMethod] = useState('qa');
    const [chunkSize, setChunkSize] = useState(1200);
    const [overlapSize, setOverlapSize] = useState(150);
    const [showMetadata, setShowMetadata] = useState(false);
    const [metaVideoName, setMetaVideoName] = useState('');
    const [metaModule, setMetaModule] = useState('');
    const [metaChapter, setMetaChapter] = useState('');
    const [qaList, setQaList] = useState([]);
    const [targetKbItems, setTargetKbItems] = useState([]);
    const [usedLlmModel, setUsedLlmModel] = useState('');
    const [generationCostUsd, setGenerationCostUsd] = useState(0);
    const [generationCostBrl, setGenerationCostBrl] = useState(0);

    useEffect(() => {
        if (isTrainingModalOpen && taskForTraining) {
            setSelectedKbId('');
            setNumQuestions(5);
            setQaList([]);
            setIsGenerating(false);
            setIsSaving(false);
            setMethod('qa');
            setChunkSize(1200);
            setOverlapSize(150);
            setShowMetadata(false);
            setMetaVideoName(taskForTraining.filename || '');
            setMetaModule('');
            setMetaChapter('');
            setTargetKbItems([]);
            setUsedLlmModel('');
            setGenerationCostUsd(0);
            setGenerationCostBrl(0);

            // Busca dinamicamente os modelos ativos da API
            api.get('/models')
                .then(res => res.json())
                .then(data => {
                    const fetchedModels = data.models || [];
                    setModels(fetchedModels);
                    if (fetchedModels.length > 0) {
                        const defaultModel = fetchedModels.find(m => m.id === 'gpt-5-mini' || m.id === 'gpt-4o-mini') || fetchedModels[0];
                        setSelectedModel(defaultModel.id);
                    }
                })
                .catch(err => {
                    console.error("Erro ao carregar modelos da API:", err);
                    setModels([
                        { id: 'gpt-4o-mini', real_id: 'gpt-4o-mini', provider: 'openai' },
                        { id: 'gpt-4o', real_id: 'gpt-4o', provider: 'openai' },
                        { id: 'gemini-1.5-flash', real_id: 'gemini-1.5-flash-002', provider: 'gemini' },
                        { id: 'gemini-1.5-pro', real_id: 'gemini-1.5-pro-002', provider: 'gemini' },
                        { id: 'claude-4.5-haiku', real_id: 'claude-haiku-4-5', provider: 'anthropic' }
                    ]);
                    setSelectedModel('gpt-4o-mini');
                });
        }
    }, [isTrainingModalOpen, taskForTraining]);

    // Fetch silencioso dos itens da base selecionada para detecção de duplicatas
    useEffect(() => {
        if (selectedKbId) {
            api.get(`/knowledge-bases/${selectedKbId}`)
                .then(res => res.json())
                .then(data => {
                    setTargetKbItems(data.items || []);
                })
                .catch(err => console.error("Erro ao buscar itens da base alvo:", err));
        } else {
            setTargetKbItems([]);
        }
    }, [selectedKbId]);

    const showToast = (message, type = 'success') => {
        window.dispatchEvent(new CustomEvent('app:toast', { detail: { message, type } }));
    };

    const buildMetadataVal = () => {
        const parts = [];
        const videoName = metaVideoName.trim() || (taskForTraining ? taskForTraining.filename : '');
        parts.push(`Vídeo: ${videoName}`);
        if (metaModule.trim()) parts.push(`Módulo: ${metaModule.trim()}`);
        if (metaChapter.trim()) parts.push(`Capítulo: ${metaChapter.trim()}`);
        return parts.join(' | ');
    };

    const handleGenerateQA = async () => {
        if (!selectedKbId) { showToast('Selecione uma base de conhecimento de destino.', 'error'); return; }
        setIsGenerating(true);
        try {
            const response = await api.post('/knowledge-bases/generate-qa-from-transcription', {
                text: taskForTraining.result_text || '',
                total_questions: Number(numQuestions),
                model: selectedModel,
                task_id: taskForTraining.id
            });
            if (response.ok) {
                const data = await response.json();
                const resultItems = Array.isArray(data) ? data : (data.items || []);
                const modelUsed = data.model || '';
                const costUsd = data.cost_usd || 0;
                const costBrl = data.cost_brl || 0;
                
                if (resultItems.length > 0) {
                    setUsedLlmModel(modelUsed);
                    setGenerationCostUsd(costUsd);
                    setGenerationCostBrl(costBrl);
                    setQaList(resultItems.map((item, i) => {
                        const ans = (item.resposta || item.answer || '').trim();
                        const isDup = targetKbItems.some(existing => existing.answer && existing.answer.trim() === ans);
                        
                        return {
                            localId: `qa-${Date.now()}-${i}`,
                            question: item.pergunta || item.question || '',
                            answer: ans,
                            category: item.categoria || item.category || 'Treinamento',
                            isDuplicate: isDup
                        };
                    }));
                    showToast(`${resultItems.length} perguntas e respostas geradas com sucesso!`);
                    
                    if (typeof fetchTasks === 'function') {
                        fetchTasks();
                    }
                } else { showToast('A IA não conseguiu extrair perguntas. Tente novamente.', 'error'); }
            } else {
                const err = await response.json().catch(() => ({}));
                showToast(err.detail || 'Falha ao conectar com o serviço de IA.', 'error');
            }
        } catch { showToast('Erro de conexão ao gerar perguntas.', 'error'); }
        finally { setIsGenerating(false); }
    };

    const handleGenerateChunks = async () => {
        if (!selectedKbId) { showToast('Selecione uma base de conhecimento de destino.', 'error'); return; }
        setIsGenerating(true);
        try {
            const response = await api.post('/knowledge-bases/generate-chunks-from-transcription', {
                text: taskForTraining.result_text || '',
                chunk_size: Number(chunkSize),
                overlap: Number(overlapSize)
            });
            if (response.ok) {
                const data = await response.json();
                if (Array.isArray(data) && data.length > 0) {
                    setUsedLlmModel('');
                    setQaList(data.map((item, i) => {
                        const ans = (item.answer || '').trim();
                        const isDup = targetKbItems.some(existing => existing.answer && existing.answer.trim() === ans);
                        return {
                            localId: `chunk-${Date.now()}-${i}`,
                            question: item.question || `Trecho da Aula #${i + 1}`,
                            answer: ans,
                            category: 'Transcrição',
                            isDuplicate: isDup
                        };
                    }));
                    showToast(`${data.length} trechos gerados com sucesso!`);
                } else { showToast('Nenhum chunk gerado. O texto pode ser muito curto.', 'error'); }
            } else {
                const err = await response.json().catch(() => ({}));
                showToast(err.detail || 'Falha ao gerar trechos.', 'error');
            }
        } catch { showToast('Erro de conexão ao gerar trechos.', 'error'); }
        finally { setIsGenerating(false); }
    };

    const handleGenerateBoth = async () => {
        if (!selectedKbId) { showToast('Selecione uma base de conhecimento de destino.', 'error'); return; }
        setIsGenerating(true);
        try {
            const [qaResponse, chunksResponse] = await Promise.all([
                api.post('/knowledge-bases/generate-qa-from-transcription', {
                    text: taskForTraining.result_text || '',
                    total_questions: Number(numQuestions),
                    model: selectedModel,
                    task_id: taskForTraining.id
                }),
                api.post('/knowledge-bases/generate-chunks-from-transcription', {
                    text: taskForTraining.result_text || '',
                    chunk_size: Number(chunkSize),
                    overlap: Number(overlapSize)
                })
            ]);

            let combinedList = [];
            let modelUsed = selectedModel;
            let costUsd = 0;
            let costBrl = 0;

            if (qaResponse.ok) {
                const qaData = await qaResponse.json();
                const resultItems = Array.isArray(qaData) ? qaData : (qaData.items || []);
                modelUsed = qaData.model || selectedModel;
                costUsd = qaData.cost_usd || 0;
                costBrl = qaData.cost_brl || 0;

                const formattedQa = resultItems.map((item, i) => {
                    const ans = (item.resposta || item.answer || '').trim();
                    const isDup = targetKbItems.some(existing => existing.answer && existing.answer.trim() === ans);
                    return {
                        localId: `qa-${Date.now()}-${i}`,
                        question: item.pergunta || item.question || '',
                        answer: ans,
                        category: item.categoria || item.category || 'Treinamento',
                        isDuplicate: isDup
                    };
                });
                combinedList.push(...formattedQa);
            }

            if (chunksResponse.ok) {
                const chunksData = await chunksResponse.json();
                if (Array.isArray(chunksData)) {
                    const formattedChunks = chunksData.map((item, i) => {
                        const ans = (item.answer || '').trim();
                        const isDup = targetKbItems.some(existing => existing.answer && existing.answer.trim() === ans);
                        return {
                            localId: `chunk-${Date.now()}-${i}`,
                            question: item.question || `Trecho da Aula #${i + 1}`,
                            answer: ans,
                            category: 'Transcrição',
                            isDuplicate: isDup
                        };
                    });
                    combinedList.push(...formattedChunks);
                }
            }

            if (combinedList.length > 0) {
                setUsedLlmModel(modelUsed);
                setGenerationCostUsd(costUsd);
                setGenerationCostBrl(costBrl);
                setQaList(combinedList);
                showToast(`${combinedList.length} itens gerados (P&R + Chunks) com sucesso!`);
                if (typeof fetchTasks === 'function') {
                    fetchTasks();
                }
            } else {
                showToast('Falha ao gerar itens híbridos. Tente novamente.', 'error');
            }
        } catch {
            showToast('Erro de conexão ao gerar conteúdo.', 'error');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleGenerate = () => {
        if (method === 'qa') return handleGenerateQA();
        if (method === 'chunks') return handleGenerateChunks();
        return handleGenerateBoth();
    };

    const handleRemoveDuplicates = () => {
        const filtered = qaList.filter(item => !item.isDuplicate);
        const removed = qaList.length - filtered.length;
        setQaList(filtered);
        showToast(`${removed} itens duplicados removidos.`);
    };

    const hasDuplicates = qaList.some(i => i.isDuplicate);

    const handleSave = async () => {
        if (qaList.length === 0) { showToast('Gere ou adicione pelo menos um item para salvar.', 'error'); return; }
        if (qaList.some(i => !i.question.trim() || !i.answer.trim())) {
            showToast('Preencha todos os campos antes de salvar.', 'error'); return;
        }
        setIsSaving(true);
        try {
            const metadataVal = buildMetadataVal();
            const response = await api.post(`/knowledge-bases/${selectedKbId}/items/add-batch`, {
                items: qaList.map(item => ({
                    question: item.question.trim(),
                    answer: item.answer.trim(),
                    category: item.category || (method === 'chunks' ? 'Transcrição' : 'Treinamento'),
                    metadata_val: metadataVal
                }))
            });
            if (response.ok) {
                showToast('Treinamento integrado à base de conhecimento com sucesso!');
                setIsTrainingModalOpen(false);
                setTaskForTraining(null);
                if (typeof fetchTasks === 'function') {
                    fetchTasks();
                }
            } else {
                const err = await response.json().catch(() => ({}));
                showToast(err.detail || 'Erro ao salvar os itens.', 'error');
            }
        } catch { showToast('Erro de rede ao salvar treinamento.', 'error'); }
        finally { setIsSaving(false); }
    };

    const handleFieldChange = (localId, field, value) =>
        setQaList(prev => prev.map(item => item.localId === localId ? { ...item, [field]: value } : item));

    const handleRemoveCard = (localId) => {
        setQaList(prev => prev.filter(item => item.localId !== localId));
        showToast('Item removido da lista.');
    };

    const handleAddManualCard = () => {
        setQaList(prev => [...prev, {
            localId: `manual-${Date.now()}`,
            question: method === 'chunks' ? `Trecho Manual #${prev.length + 1}` : '',
            answer: '',
            category: method === 'chunks' ? 'Transcrição' : 'Treinamento Manual'
        }]);
        showToast('Novo item adicionado.');
    };

    const handleClose = () => {
        if (!isGenerating) {
            setIsTrainingModalOpen(false);
            setTaskForTraining(null);
        }
    };

    return {
        isTrainingModalOpen,
        taskForTraining,
        knowledgeBases,
        selectedKbId,
        setSelectedKbId,
        numQuestions,
        setNumQuestions,
        selectedModel,
        setSelectedModel,
        models,
        isGenerating,
        isSaving,
        method,
        setMethod,
        chunkSize,
        setChunkSize,
        overlapSize,
        setOverlapSize,
        showMetadata,
        setShowMetadata,
        metaVideoName,
        setMetaVideoName,
        metaModule,
        setMetaModule,
        metaChapter,
        setMetaChapter,
        qaList,
        usedLlmModel,
        generationCostUsd,
        generationCostBrl,
        hasDuplicates,
        buildMetadataVal,
        handleGenerate,
        handleRemoveDuplicates,
        handleSave,
        handleFieldChange,
        handleRemoveCard,
        handleAddManualCard,
        handleClose
    };
}
