import type { TimelineEvent } from '../types';

const typeStyles: Record<TimelineEvent['type'], { dot: string; border: string; bg: string }> = {
  milestone:  { dot: '#3B82F6', border: '#BFDBFE', bg: '#EFF6FF' },
  win:        { dot: '#22C55E', border: '#BBF7D0', bg: '#F0FDF4' },
  watch:      { dot: '#F59E0B', border: '#FDE68A', bg: '#FFFBEB' },
  escalation: { dot: '#EF4444', border: '#FECACA', bg: '#FFF1F2' },
  roadmap:    { dot: '#0D9488', border: '#99F6E4', bg: '#F0FDFA' },
};

const typeLabel: Record<TimelineEvent['type'], string> = {
  milestone:  'Milestone',
  win:        'Win',
  watch:      'Watch',
  escalation: 'Escalation',
  roadmap:    'Roadmap',
};

interface Props {
  events: TimelineEvent[];
}

export function Timeline({ events }: Props) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 500, color: '#0F172A' }}>Relationship Timeline</h2>
      <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
        <div style={{ display: 'flex', gap: 0, minWidth: 'max-content', position: 'relative', alignItems: 'flex-start' }}>
          <div style={{
            position: 'absolute',
            top: 20,
            left: 20,
            right: 20,
            height: 2,
            background: '#F1F5F9',
            zIndex: 0,
          }} />

          {events.map((event, i) => {
            const s = typeStyles[event.type];
            return (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 180, flexShrink: 0, position: 'relative', zIndex: 1 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: s.dot,
                  border: '3px solid #fff',
                  boxShadow: `0 0 0 2px ${s.dot}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 12,
                }}>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#fff' }} />
                </div>

                <div style={{
                  background: s.bg,
                  border: `1px solid ${s.border}`,
                  borderRadius: 10,
                  padding: '10px 12px',
                  width: '100%',
                  boxSizing: 'border-box',
                }}>
                  <div style={{ fontSize: 10, color: '#94A3B8', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{event.date}</div>
                  <div style={{ fontWeight: 500, fontSize: 12, color: '#0F172A', marginBottom: 4 }}>{event.title}</div>
                  <div style={{ fontSize: 11, color: '#64748B', lineHeight: 1.5 }}>{event.description}</div>
                  <div style={{ marginTop: 6 }}>
                    <span style={{
                      fontSize: 10,
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: s.dot,
                      color: '#fff',
                      fontWeight: 500,
                    }}>{typeLabel[event.type]}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
