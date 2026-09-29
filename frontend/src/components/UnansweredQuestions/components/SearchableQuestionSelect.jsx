import React, { useState, useRef, useEffect, useMemo } from 'react';

export default function SearchableQuestionSelect({ 
    items = [], 
    selectedId, 
    onSelect, 
    placeholder = "Selecione uma pergunta...",
    loading = false 
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const containerRef = useRef(null);
    const searchInputRef = useRef(null);

    // Encontra o item atualmente selecionado
    const selectedItem = useMemo(() => {
        return items.find(i => String(i.id) === String(selectedId)) || null;
    }, [items, selectedId]);

    // Filtra itens com base no termo de busca
    const filteredItems = useMemo(() => {
        if (!searchTerm.trim()) return items;
        const term = searchTerm.toLowerCase();
        return items.filter(item => 
            (item.question && item.question.toLowerCase().includes(term)) ||
            (item.answer && item.answer.toLowerCase().includes(term))
        );
    }, [items, searchTerm]);

    // Fechar ao clicar fora
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
            // Auto-focus no campo de busca ao abrir
            setTimeout(() => {
                if (searchInputRef.current) {
                    searchInputRef.current.focus();
                }
            }, 50);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    // Fechar ao pressionar ESC
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen]);

    const handleItemClick = (item) => {
        onSelect(String(item.id));
        setIsOpen(false);
        setSearchTerm('');
    };

    return (
        <div className="searchable-select-container" ref={containerRef}>
            {/* Gatilho Principal (Aparência de Select Premium) */}
            <div 
                className={`searchable-select-trigger ${isOpen ? 'active' : ''}`}
                onClick={() => !loading && setIsOpen(prev => !prev)}
            >
                <div className="searchable-select-value">
                    {loading ? (
                        <span className="select-placeholder">Carregando perguntas da base...</span>
                    ) : selectedItem ? (
                        <span className="selected-question-text">{selectedItem.question}</span>
                    ) : (
                        <span className="select-placeholder">{placeholder}</span>
                    )}
                </div>
                <div className={`select-arrow-icon ${isOpen ? 'open' : ''}`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </div>
            </div>

            {/* Menu Suspenso Customizado (Abre para baixo com estilo Neon Glassmorphism) */}
            {isOpen && (
                <div className="searchable-select-dropdown fade-in-down">
                    {/* Campo de Pesquisa Integrado */}
                    <div className="dropdown-search-wrapper">
                        <span className="dropdown-search-icon">🔍</span>
                        <input
                            ref={searchInputRef}
                            type="text"
                            className="dropdown-search-input"
                            placeholder="Digite para filtrar perguntas..."
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            onClick={e => e.stopPropagation()}
                        />
                        {searchTerm && (
                            <button 
                                type="button" 
                                className="dropdown-search-clear"
                                onClick={(e) => { e.stopPropagation(); setSearchTerm(''); }}
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    {/* Lista de Perguntas */}
                    <div className="dropdown-items-list custom-scrollbar">
                        {filteredItems.length === 0 ? (
                            <div className="dropdown-empty-state">
                                <span>Nenhuma pergunta encontrada com esse termo.</span>
                            </div>
                        ) : (
                            filteredItems.map(item => {
                                const isSelected = String(item.id) === String(selectedId);
                                return (
                                    <div
                                        key={item.id}
                                        className={`dropdown-item ${isSelected ? 'selected' : ''}`}
                                        onClick={() => handleItemClick(item)}
                                    >
                                        <div className="dropdown-item-question">
                                            {item.question}
                                        </div>
                                        {isSelected && (
                                            <span className="dropdown-item-check">✓</span>
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
