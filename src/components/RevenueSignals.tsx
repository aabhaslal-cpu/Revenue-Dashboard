import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { Account, Opportunity } from '../types';

const signalStyles: Record<Opportunity['signalType'], { bg: string; color: string; label: string }> = {
  'over-consumption': { bg: '#FEF3C7', color: '#92400E', label: 'Over-consumption' },
  'pro-tier':         { bg: '#EDE9FE', color: '#6D28D9', label: 'Pro tier ready' },
  'es-pipeline':      { bg: '#DBEAFE', color: '#1E40AF', label: 'ES pipeline' },
  'faint-signal':     { bg: '#F1F5F9', color: '#475569', label: 'Faint signal' },
};

const months = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];

interface Props {
  account: Account;
  onAction: (action: string) => void;
}

export function RevenueSignals({ account, onAction }: Props) {
  const chartData = account.adoptionHistory.map((v, i) => ({ month: months[i], pct: v }));

  const totalOpportunity = account.opportunities
    .map(o => parseInt(o.value.replace(/[^0-9]/g, '')) * (o.value.includes('K') ? 1000 : 1000000))
    .reduce((a, b) => a + b, 0);

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 15, fontWeight: 500, color: '#0F172A' }}>Hidden Revenue Signals</h2>
        <span style={{
          background: '#F0FDFA',
          color: '#0F766E',
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: 12,
          fontWeight: 500,
        }}>
          ${(totalOpportunity / 1000).toFixed(0)}K identified
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        {account.opportunities.map((opp, i) => {
          const s = signalStyles[opp.signalType];
          return (
            <div key={i} style={{
              border: '1px solid #F1F5F9',
              borderRadius: 10,
              padding: 16,
            }}>
              <span style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 500,
                background: s.bg,
                color: s.color,
                marginBottom: 8,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>
                {s.label}
              </span>
              <div style={{ fontWeight: 500, fontSize: 13, color: '#0F172A', marginBottom: 6 }}>{opp.title}</div>
              <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.5, marginBottom: 10 }}>{opp.description}</div>
              <div style={{ fontSize: 16, fontWeight: 500, color: '#0D9488' }}>{opp.value}</div>
            </div>
          );
        })}
      </div>

      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 12 }}>Platform Adoption — Last 12 Months</div>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#0F172A', border: 'none', borderRadius: 6, color: '#fff', fontSize: 12 }}
              formatter={(v) => [`${v ?? ''}%`, 'Adoption']}
            />
            <Line
              type="monotone"
              dataKey="pct"
              stroke="#0D9488"
              strokeWidth={2}
              dot={{ r: 3, fill: '#0D9488', strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {[
          { label: 'Build renewal story', bg: '#0D9488' },
          { label: 'Draft expansion email', bg: '#2563EB' },
          { label: 'Pre-call brief', bg: '#7C3AED' },
        ].map(btn => (
          <button
            key={btn.label}
            onClick={() => onAction(btn.label)}
            style={{
              padding: '10px 18px',
              background: btn.bg,
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {btn.label}
          </button>
        ))}
      </div>
    </div>
  );
}
