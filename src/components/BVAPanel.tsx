import { Shield, ClipboardCheck, Zap } from 'lucide-react';
import type { BVAItem } from '../types';

const icons: Record<string, React.FC<{ size?: number; color?: string }>> = {
  Shield,
  ClipboardCheck,
  Zap,
};

const deltaStyles: Record<string, { bg: string; color: string }> = {
  green: { bg: '#DCFCE7', color: '#15803D' },
  blue: { bg: '#DBEAFE', color: '#1E40AF' },
  teal: { bg: '#CCFBF1', color: '#0F766E' },
};

interface Props {
  bva: BVAItem[];
}

export function BVAPanel({ bva }: Props) {
  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 500, color: '#0F172A' }}>Business Value Assessment</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        {bva.map(item => {
          const Icon = icons[item.icon] ?? Shield;
          const ds = deltaStyles[item.deltaColor];
          return (
            <div key={item.outcome} style={{
              border: '1px solid #F1F5F9',
              borderRadius: 10,
              padding: 20,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ padding: 8, background: '#F8FAFC', borderRadius: 8 }}>
                  <Icon size={16} color="#0D9488" />
                </div>
                <span style={{ fontWeight: 500, fontSize: 13, color: '#0F172A' }}>{item.outcome}</span>
              </div>

              <div>
                <div style={{ fontSize: 11, color: '#94A3B8', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Before Saviynt</div>
                <div style={{ fontSize: 13, color: '#DC2626', background: '#FFF5F5', padding: '6px 10px', borderRadius: 6 }}>{item.before}</div>
              </div>

              <div>
                <div style={{ fontSize: 11, color: '#94A3B8', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>After Saviynt</div>
                <div style={{ fontSize: 13, color: '#16A34A', background: '#F0FDF4', padding: '6px 10px', borderRadius: 6 }}>{item.after}</div>
              </div>

              <div style={{
                alignSelf: 'flex-start',
                padding: '4px 12px',
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 500,
                background: ds.bg,
                color: ds.color,
              }}>
                {item.delta}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
