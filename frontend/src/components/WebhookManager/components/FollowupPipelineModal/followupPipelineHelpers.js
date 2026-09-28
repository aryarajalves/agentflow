export const formatDelay = (minutes) => {
    if (!minutes || minutes <= 0) return 'Imediato';
    if (minutes < 60) return `${minutes} min`;
    if (minutes % 1440 === 0) {
        const days = minutes / 1440;
        return `${days} ${days === 1 ? 'dia' : 'dias'}`;
    }
    const hours = (minutes / 60).toFixed(1).replace('.0', '');
    return `${hours} ${hours === '1' ? 'hora' : 'horas'}`;
};

export const getStatusBadge = (status) => {
    switch (status) {
        case 'completed':
            return { label: '✓ Disparado', bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '#10b981' };
        case 'skipped':
            return { label: '⏭️ Dispensado', bg: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '#f59e0b' };
        case 'active':
            return { label: '⏳ Aguardando Envio', bg: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '#3b82f6' };
        case 'cancelled':
            return { label: '🛑 Cancelado / Pausado', bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '#ef4444' };
        case 'disabled':
            return { label: '⚪ Desativado', bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '#64748b' };
        default:
            return { label: '⏸️ Pendente', bg: 'rgba(255, 255, 255, 0.05)', color: '#94a3b8', border: 'rgba(255, 255, 255, 0.1)' };
    }
};

export const formatDateTime = (isoStr) => {
    if (!isoStr) return '-';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return '-';
        return d.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return '-';
    }
};

export const formatRelativeSchedule = (isoStr) => {
    if (!isoStr) return '';
    try {
        const target = new Date(isoStr);
        const now = new Date();
        if (isNaN(target.getTime())) return '';

        const diffMs = target.getTime() - now.getTime();
        const diffHours = Math.round(diffMs / (1000 * 60 * 60));

        const timeStr = target.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        const dateStr = target.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });

        const isToday = target.toDateString() === now.toDateString();
        const tomorrow = new Date(now);
        tomorrow.setDate(tomorrow.getDate() + 1);
        const isTomorrow = target.toDateString() === tomorrow.toDateString();

        if (diffMs <= 0) {
            return `A qualquer momento (Janela comercial)`;
        }
        if (isToday) {
            return `Hoje às ${timeStr} (em aprox. ${Math.max(1, diffHours)}h)`;
        }
        if (isTomorrow) {
            return `Amanhã às ${timeStr}`;
        }
        return `${dateStr} às ${timeStr}`;
    } catch {
        return '';
    }
};

