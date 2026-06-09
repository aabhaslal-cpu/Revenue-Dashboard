import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { Account, Health } from '../types';

const healthLabel: Record<Health, string> = { green: 'Healthy', amber: 'At Risk', red: 'Critical' };
const healthBg: Record<Health, string> = { green: '#DCFCE7', amber: '#FEF3C7', red: '#FEE2E2' };
const healthText: Record<Health, string> = { green: '#15803D', amber: '#92400E', red: '#991B1B' };

const sourceColors: Record<string, string> = {
  Gmail: '#EA4335',
  Slack: '#4A154B',
  Notion: '#000000',
  Gainsight: '#FF6633',
  Salesforce: '#00A1E0',
  Gong: '#4CAF50',
};

function formatACV(n: number) {
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  return `$${(n / 1000).toFixed(0)}K`;
}

interface Props {
  account: Account;
}

export function AccountHeader({ account }: Props) {
  const TrendIcon = account.adoptionTrend > 0 ? TrendingUp : account.adoptionTrend < 0 ? TrendingDown : Minus;
  const trendColor = account.adoptionTrend > 0 ? '#22C55E' : account.adoptionTrend < 0 ? '#EF4444' : '#94A3B8';

  return (
    <div style={{ background: '#fff', borderRadius: 12, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 500, color: '#0F172A' }}>{account.name}</h1>
            <span style={{
              padding: '3px 10px',
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 500,
              background: healthBg[account.health],
              color: healthText[account.health],
            }}>
              {healthLabel[account.health]}
            </span>
          </div>
          <div style={{ color: '#64748B', fontSize: 14 }}>
            <span style={{ fontWeight: 500, color: '#334155' }}>{account.economicBuyer.name}</span>
            <span style={{ color: '#94A3B8' }}> · </span>
            <span>{account.economicBuyer.title}</span>
            <span style={{ color: '#94A3B8' }}> · CSM: </span>
            <span>{account.csm}</span>
          </div>
          <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {account.products.map(p => (
              <span key={p} style={{
                background: '#EFF6FF',
                color: '#1E40AF',
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 500,
              }}>{p}</span>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 2 }}>Contract ACV</div>
            <div style={{ fontSize: 20, fontWeight: 500, color: '#0F172A' }}>{formatACV(account.acv)}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 2 }}>Renewal</div>
            <div style={{ fontSize: 20, fontWeight: 500, color: '#0F172A' }}>{account.renewalDate}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 2 }}>Platform Adoption</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
              <span style={{ fontSize: 20, fontWeight: 500, color: '#0F172A' }}>{account.adoptionPct}%</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 2, color: trendColor }}>
                <TrendIcon size={14} />
                <span style={{ fontSize: 12 }}>
                  {account.adoptionTrend > 0 ? '+' : ''}{account.adoptionTrend}% QoQ
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #F1F5F9' }}>
        <span style={{ color: '#94A3B8', fontSize: 11, marginRight: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Data sources</span>
        <div style={{ display: 'inline-flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {account.dataSources.map(src => (
            <span key={src} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: '#475569' }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: sourceColors[src] ?? '#94A3B8', display: 'inline-block' }} />
              {src}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
