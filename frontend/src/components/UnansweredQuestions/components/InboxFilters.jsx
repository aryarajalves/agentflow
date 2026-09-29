import React from 'react';
import { useQuestions } from '../QuestionsContext';

const InboxFilters = () => {
    const {
        agents,
        filterAgentId, setFilterAgentId,
        filterPhone, setFilterPhone,
        filterDateStart, setFilterDateStart,
        filterDateEnd, setFilterDateEnd,
        filterSource, setFilterSource,
        setPage
    } = useQuestions();

    const handleClearFilters = () => {
        setFilterAgentId('');
        setFilterPhone('');
        setFilterDateStart('');
        setFilterDateEnd('');
        setFilterSource('');
        setPage(1);
    };

    const hasActiveFilters = Boolean(
        filterAgentId || filterPhone || filterDateStart || filterDateEnd || filterSource
    );

    return (
        <div className="uq-filters-panel">
            <div className="uq-filters-row">
                {/* 1. Filtro por Agente */}
                <div className="uq-filter-group">
                    <label className="uq-filter-label">🤖 Agente:</label>
                    <select
                        value={filterAgentId}
                        onChange={e => {
                            setFilterAgentId(e.target.value);
                            setPage(1);
                        }}
                        className="uq-filter-select"
                    >
                        <option value="">Todos os Agentes</option>
                        {agents.map(ag => (
                            <option key={ag.id} value={ag.id}>
                                {ag.name || `Agente #${ag.id}`}
                            </option>
                        ))}
                    </select>
                </div>

                {/* 2. Filtro por Telefone / Contato */}
                <div className="uq-filter-group">
                    <label className="uq-filter-label">📞 Contato / Telefone:</label>
                    <input
                        type="text"
                        placeholder="Ex: 5511999999999"
                        value={filterPhone}
                        onChange={e => {
                            setFilterPhone(e.target.value);
                            setPage(1);
                        }}
                        className="uq-filter-input"
                    />
                </div>

                {/* 3. Filtro por Origem (Chat vs ZapJords) */}
                <div className="uq-filter-group">
                    <label className="uq-filter-label">💬 Origem:</label>
                    <select
                        value={filterSource}
                        onChange={e => {
                            setFilterSource(e.target.value);
                            setPage(1);
                        }}
                        className="uq-filter-select"
                    >
                        <option value="">Todas as Origens</option>
                        <option value="chat">💻 Chat Direto</option>
                        <option value="zapvoice">💬 Integração ZapJords</option>
                    </select>
                </div>

                {/* 4. Filtro por Data Inicial */}
                <div className="uq-filter-group">
                    <label className="uq-filter-label">📅 Data Inicial:</label>
                    <input
                        type="date"
                        value={filterDateStart}
                        onChange={e => {
                            setFilterDateStart(e.target.value);
                            setPage(1);
                        }}
                        className="uq-filter-input uq-filter-date"
                    />
                </div>

                {/* 5. Filtro por Data Final */}
                <div className="uq-filter-group">
                    <label className="uq-filter-label">📅 Data Final:</label>
                    <input
                        type="date"
                        value={filterDateEnd}
                        onChange={e => {
                            setFilterDateEnd(e.target.value);
                            setPage(1);
                        }}
                        className="uq-filter-input uq-filter-date"
                    />
                </div>

                {/* Botão de Limpar Filtros */}
                {hasActiveFilters && (
                    <div className="uq-filter-group-actions">
                        <button
                            type="button"
                            onClick={handleClearFilters}
                            className="btn-clear-filters"
                            title="Limpar todos os filtros aplicados"
                        >
                            🧹 Limpar Filtros
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default InboxFilters;
