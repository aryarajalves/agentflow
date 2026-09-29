import React, { createContext, useContext, useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';

export const ConfigContext = createContext();

export const useConfig = () => {
    const context = useContext(ConfigContext);
    if (!context) throw new Error('useConfig must be used within a ConfigProvider');
    return context;
};

export const ConfigProvider = ({ children }) => {
    const { id } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const initialTab = queryParams.get('tab') || 'prompts';

    const isNew = id === 'new' || !id;

    // Global States
    const [googleConnected, setGoogleConnected] = useState(false);
    const [models, setModels] = useState([]);
    const [kbList, setKbList] = useState([]);
    const [toolsList, setToolsList] = useState([]);
    const [status, setStatus] = useState('');
    const [activeTab, setActiveTab] = useState(initialTab);
    const [isLoadingData, setIsLoadingData] = useState(!isNew);
    const [isSaving, setIsSaving] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);
    
    // Auth Status
    const [openaiConnected, setOpenaiConnected] = useState(true);
    const [geminiConnected, setGeminiConnected] = useState(true);
    const [anthropicConnected, setAnthropicConnected] = useState(true);

    // Form States
    const getInitialPrefill = () => {
        if (!isNew) return null;
        try {
            const raw = sessionStorage.getItem('prefill_agent_prompt');
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    };
    const prefillData = getInitialPrefill();

    const [name, setName] = useState(prefillData?.name || (isNew ? 'Novo Agente' : ''));
    const [description, setDescription] = useState('');
    const [selectedModel, setSelectedModel] = useState('');
    const [fallbackModel, setFallbackModel] = useState(null);
    const [temperature, setTemperature] = useState(1.0);
    const [topP, setTopP] = useState(1.0);
    const [topK, setTopK] = useState(40);
    const [presencePenalty, setPresencePenalty] = useState(0.0);
    const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);
    const [reasoningEffort, setReasoningEffort] = useState('medium');
    const [safetySettings, setSafetySettings] = useState('standard');
    
    const [dateAwareness, setDateAwareness] = useState(false);
    const [dateAwarenessPastDays, setDateAwarenessPastDays] = useState(7);
    const [dateAwarenessFutureDays, setDateAwarenessFutureDays] = useState(7);
    const [simulatedTime, setSimulatedTime] = useState('');
    const [systemPrompt, setSystemPrompt] = useState(prefillData?.system_prompt !== undefined ? prefillData.system_prompt : 'Você é um assistente útil e inteligente.');
    const [dynamicPrompt, setDynamicPrompt] = useState('');
    const [preRouterPrompt, setPreRouterPrompt] = useState(prefillData?.pre_router_prompt || '');
    const [contextWindow, setContextWindow] = useState(5);
    
    // Knowledge & Tools
    const [knowledgeBaseIds, setKnowledgeBaseIds] = useState([]);
    const [selectedTools, setSelectedTools] = useState([]);
    const [ragRetrievalCount, setRagRetrievalCount] = useState(5);
    const [ragTranslationEnabled, setRagTranslationEnabled] = useState(false);
    const [ragMultiQueryEnabled, setRagMultiQueryEnabled] = useState(true);
    const [ragRerankEnabled, setRagRerankEnabled] = useState(true);
    const [ragAgenticEvalEnabled, setRagAgenticEvalEnabled] = useState(true);
    const [ragParentExpansionEnabled, setRagParentExpansionEnabled] = useState(false);
    const [ragRelevanceThreshold, setRagRelevanceThreshold] = useState(0); // Percentual (0-100) exibido na UI
    const [ragKbRoutingEnabled, setRagKbRoutingEnabled] = useState(false);
    const [ragKbRoutingVariable, setRagKbRoutingVariable] = useState('');
    const [semanticCacheEnabled, setSemanticCacheEnabled] = useState(true);
    const [semanticCacheThreshold, setSemanticCacheThreshold] = useState(92); // Percentual (70-99) exibido na UI
    const [inboxCaptureEnabled, setInboxCaptureEnabled] = useState(true);
    const [toolPrompts, setToolPrompts] = useState(prefillData?.tool_prompts || {});

    // Messages
    const [initialMessage, setInitialMessage] = useState('');
    const [initialQuestionMessage, setInitialQuestionMessage] = useState('');
    const [initialIgnoreMessage, setInitialIgnoreMessage] = useState([]);
    const [qualificationQuestions, setQualificationQuestions] = useState([]);
    const [qualificationLabels, setQualificationLabels] = useState([]);
    const [qualificationCriteria, setQualificationCriteria] = useState('');
    const [qualificationFinalAction, setQualificationFinalAction] = useState('');
    const [qualificationFinalActionTrigger, setQualificationFinalActionTrigger] = useState('all');
    const [qualificationFunnels, setQualificationFunnels] = useState([]);
    const [activeFunnelId, setActiveFunnelId] = useState('');
    
    // Greeting, Question, and Ad Modes
    const [greetingMode, setGreetingMode] = useState('prompt');
    const [questionMode, setQuestionMode] = useState('panel');
    const [adMode, setAdMode] = useState('panel');
    
    // Security
    const [securityBlacklist, setSecurityBlacklist] = useState('');
    const [securityForbidden, setSecurityForbidden] = useState('');
    const [securityDiscount, setSecurityDiscount] = useState('');
    const [securityComplexity, setSecurityComplexity] = useState('standard');
    const [securityPii, setSecurityPii] = useState(false);
    const [securityValidatorIa, setSecurityValidatorIa] = useState(false);
    const [securityBotProtection, setSecurityBotProtection] = useState(false);
    const [securityMaxMessages, setSecurityMaxMessages] = useState(20);
    const [securitySemanticThreshold, setSecuritySemanticThreshold] = useState(0.85);
    const [securityLoopCount, setSecurityLoopCount] = useState(3);

    // Router
    const [routerEnabled, setRouterEnabled] = useState(true);
    const [routerSimpleModel, setRouterSimpleModel] = useState('gpt-4o-mini');
    const [routerSimpleFallbackModel, setRouterSimpleFallbackModel] = useState('');
    const [routerComplexModel, setRouterComplexModel] = useState('gpt-4o');
    const [routerComplexFallbackModel, setRouterComplexFallbackModel] = useState('');
    const [handoffEnabled, setHandoffEnabled] = useState(false);
    const [unansweredHandoffEnabled, setUnansweredHandoffEnabled] = useState(true);
    const [unansweredHandoffLimit, setUnansweredHandoffLimit] = useState(2);
    const [unansweredQuestionPrompt, setUnansweredQuestionPrompt] = useState(prefillData?.unanswered_question_prompt || '');
    const [responseTranslationEnabled, setResponseTranslationEnabled] = useState(false);
    const [responseTranslationFallbackLang, setResponseTranslationFallbackLang] = useState('pt-br');

    // UI
    const [uiPrimaryColor, setUiPrimaryColor] = useState('#6366f1');
    const [uiHeaderColor, setUiHeaderColor] = useState('#0f172a');
    const [uiChatTitle, setUiChatTitle] = useState('Suporte Inteligente');
    const [uiWelcomeMessage, setUiWelcomeMessage] = useState('Olá! Como posso te ajudar hoje?');

    // Guides
    const [showGeralGuide, setShowGeralGuide] = useState(false);
    const [showHabilidadesGuide, setShowHabilidadesGuide] = useState(false);
    const [showSecurityGuide, setShowSecurityGuide] = useState(false);
    const [showWhitelabelGuide, setShowWhitelabelGuide] = useState(false);

    // Advanced
    const [modelSettings, setModelSettings] = useState({});
    const [configRole, setConfigRole] = useState('main');

    const value = {
        id, isNew, navigate,
        googleConnected, setGoogleConnected,
        models, setModels,
        kbList, setKbList,
        toolsList, setToolsList,
        status, setStatus,
        activeTab, setActiveTab,
        isLoadingData, setIsLoadingData,
        isSaving, setIsSaving,
        validationErrors, setValidationErrors,
        openaiConnected, setOpenaiConnected,
        geminiConnected, setGeminiConnected,
        anthropicConnected, setAnthropicConnected,
        name, setName,
        description, setDescription,
        selectedModel, setSelectedModel,
        fallbackModel, setFallbackModel,
        temperature, setTemperature,
        topP, setTopP,
        topK, setTopK,
        presencePenalty, setPresencePenalty,
        frequencyPenalty, setFrequencyPenalty,
        reasoningEffort, setReasoningEffort,
        safetySettings, setSafetySettings,
        dateAwareness, setDateAwareness,
        dateAwarenessPastDays, setDateAwarenessPastDays,
        dateAwarenessFutureDays, setDateAwarenessFutureDays,
        simulatedTime, setSimulatedTime,
        systemPrompt, setSystemPrompt,
        dynamicPrompt, setDynamicPrompt,
        preRouterPrompt, setPreRouterPrompt,
        contextWindow, setContextWindow,
        knowledgeBaseIds, setKnowledgeBaseIds,
        selectedTools, setSelectedTools,
        ragRetrievalCount, setRagRetrievalCount,
        ragTranslationEnabled, setRagTranslationEnabled,
        ragMultiQueryEnabled, setRagMultiQueryEnabled,
        ragRerankEnabled, setRagRerankEnabled,
        ragAgenticEvalEnabled, setRagAgenticEvalEnabled,
        ragParentExpansionEnabled, setRagParentExpansionEnabled,
        ragRelevanceThreshold, setRagRelevanceThreshold,
        ragKbRoutingEnabled, setRagKbRoutingEnabled,
        ragKbRoutingVariable, setRagKbRoutingVariable,
        semanticCacheEnabled, setSemanticCacheEnabled,
        semanticCacheThreshold, setSemanticCacheThreshold,
        inboxCaptureEnabled, setInboxCaptureEnabled,
        toolPrompts, setToolPrompts,
        initialMessage, setInitialMessage,
        initialQuestionMessage, setInitialQuestionMessage,
        initialIgnoreMessage, setInitialIgnoreMessage,
        qualificationQuestions, setQualificationQuestions,
        qualificationLabels, setQualificationLabels,
        qualificationCriteria, setQualificationCriteria,
        qualificationFinalAction, setQualificationFinalAction,
        qualificationFinalActionTrigger, setQualificationFinalActionTrigger,
        qualificationFunnels, setQualificationFunnels,
        activeFunnelId, setActiveFunnelId,
        greetingMode, setGreetingMode,
        questionMode, setQuestionMode,
        adMode, setAdMode,
        securityBlacklist, setSecurityBlacklist,
        securityForbidden, setSecurityForbidden,
        securityDiscount, setSecurityDiscount,
        securityComplexity, setSecurityComplexity,
        securityPii, setSecurityPii,
        securityValidatorIa, setSecurityValidatorIa,
        securityBotProtection, setSecurityBotProtection,
        securityMaxMessages, setSecurityMaxMessages,
        securitySemanticThreshold, setSecuritySemanticThreshold,
        securityLoopCount, setSecurityLoopCount,
        routerEnabled, setRouterEnabled,
        routerSimpleModel, setRouterSimpleModel,
        routerSimpleFallbackModel, setRouterSimpleFallbackModel,
        routerComplexModel, setRouterComplexModel,
        routerComplexFallbackModel, setRouterComplexFallbackModel,
        handoffEnabled, setHandoffEnabled,
        unansweredHandoffEnabled, setUnansweredHandoffEnabled,
        unansweredHandoffLimit, setUnansweredHandoffLimit,
        unansweredQuestionPrompt, setUnansweredQuestionPrompt,
        responseTranslationEnabled, setResponseTranslationEnabled,
        responseTranslationFallbackLang, setResponseTranslationFallbackLang,
        uiPrimaryColor, setUiPrimaryColor,
        uiHeaderColor, setUiHeaderColor,
        uiChatTitle, setUiChatTitle,
        uiWelcomeMessage, setUiWelcomeMessage,
        showGeralGuide, setShowGeralGuide,
        showHabilidadesGuide, setShowHabilidadesGuide,
        showSecurityGuide, setShowSecurityGuide,
        showWhitelabelGuide, setShowWhitelabelGuide,
        modelSettings, setModelSettings,
        configRole, setConfigRole
    };

    return (
        <ConfigContext.Provider value={value}>
            {children}
        </ConfigContext.Provider>
    );
};
