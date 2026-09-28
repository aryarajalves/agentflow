import React from 'react';
import EventCostBadge from '../EventCostBadge';
import AiStatusBadge from './AiStatusBadge';

const ResponseAiCell = ({ event, isAgent, isGrouped, message, setMaximizedText }) => {
    if (event.event_type === 'followup') {
        const hasLongResponse = (event.agent_response || '').length > 50;
        return (
            <td style={{ padding: '1rem', fontSize: '0.85rem', color: '#818cf8', maxWidth: '250px' }}>
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ marginBottom: '4px' }}>
                        <EventCostBadge event={event} />
                    </div>
                    <div style={{ maxHeight: '60px', overflowY: 'auto', lineHeight: '1.4', paddingRight: hasLongResponse ? '24px' : '0' }}>
                        {event.agent_response || '—'}
                    </div>
                    {hasLongResponse && (
                        <button
                            onClick={() => setMaximizedText(event.agent_response)}
                            title="Maximizar"
                            style={{
                                position: 'absolute',
                                top: 0,
                                right: 0,
                                background: 'rgba(255, 255, 255, 0.05)',
                                border: 'none',
                                color: '#818cf8',
                                borderRadius: '4px',
                                width: '18px',
                                height: '18px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.65rem',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                zIndex: 10
                            }}
                            onMouseOver={e => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'}
                            onMouseOut={e => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                        >⛶</button>
                    )}
                </div>
            </td>
        );
    }

    if ((isAgent || event.agent_response) && !isGrouped) {
        const textToDisplay = isAgent ? message : event.agent_response;
        const hasLongText = (textToDisplay || '').length > 50;
        return (
            <td style={{ padding: '1rem', fontSize: '0.85rem', color: '#818cf8', maxWidth: '250px' }}>
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ marginBottom: '4px' }}>
                        <EventCostBadge event={event} />
                    </div>
                    <div style={{ maxHeight: '90px', overflowY: 'auto', lineHeight: '1.4', whiteSpace: 'pre-wrap', paddingRight: hasLongText ? '24px' : '0' }}>
                        {textToDisplay}
                    </div>
                    {hasLongText && (
                        <button
                            onClick={() => setMaximizedText(textToDisplay)}
                            title="Maximizar"
                            style={{
                                position: 'absolute',
                                top: 0,
                                right: 0,
                                background: 'rgba(255, 255, 255, 0.05)',
                                border: 'none',
                                color: '#818cf8',
                                borderRadius: '4px',
                                width: '18px',
                                height: '18px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.65rem',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                zIndex: 10
                            }}
                            onMouseOver={e => e.currentTarget.style.background = 'rgba(129, 140, 248, 0.2)'}
                            onMouseOut={e => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                        >⛶</button>
                    )}
                </div>
            </td>
        );
    }

    return (
        <td style={{ padding: '1rem', fontSize: '0.85rem', color: '#818cf8', maxWidth: '250px' }}>
            <AiStatusBadge event={event} isGrouped={isGrouped} />
        </td>
    );
};

export default ResponseAiCell;
