import { useState } from 'react';
import { Search } from 'lucide-react';
import type { Account, Health } from '../types';

const healthColor: Record<Health, string> = {
  green: '#22C55E',
  amber: '#F59E0B',
  red: '#EF4444',
};

function formatACV(n: number) {
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  return `$${(n / 1000).toFixed(0)}K`;
}

interface Props {
  accounts: Account[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function Sidebar({ accounts, selectedId, onSelect }: Props) {
  const [query, setQuery] = useState('');

  const filtered = accounts.filter(a =>
    a.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <aside style={{
      width: 260,
      minWidth: 260,
      background: '#0B1F3A',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
    }}>
      <div style={{ padding: '24px 20px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <div style={{ width: 28, height: 28, background: '#0D9488', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#fff', fontWeight: 600, fontSize: 13 }}>S</span>
          </div>
          <span style={{ color: '#fff', fontWeight: 500, fontSize: 15 }}>CS Intelligence</span>
        </div>
        <span style={{ color: '#64748B', fontSize: 11, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Saviynt</span>
      </div>

      <div style={{ padding: '0 16px 16px' }}>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#4B5563' }} />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search accounts…"
            style={{
              width: '100%',
              background: '#0F2845',
              border: '1px solid #1E3A5F',
              borderRadius: 8,
              padding: '8px 10px 8px 30px',
              color: '#CBD5E1',
              fontSize: 13,
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
        <div style={{ color: '#4B5E78', fontSize: 11, fontWeight: 500, padding: '4px 12px 8px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Accounts ({filtered.length})
        </div>
        {filtered.map(account => {
          const isActive = account.id === selectedId;
          return (
            <button
              key={account.id}
              onClick={() => onSelect(account.id)}
              style={{
                width: '100%',
                background: isActive ? '#0F2845' : 'transparent',
                border: isActive ? '1px solid #1E3A5F' : '1px solid transparent',
                borderRadius: 8,
                padding: '10px 12px',
                cursor: 'pointer',
                textAlign: 'left',
                marginBottom: 4,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: healthColor[account.health],
                  flexShrink: 0,
                }} />
                <span style={{ color: '#E2E8F0', fontSize: 13, fontWeight: isActive ? 500 : 400 }}>
                  {account.name}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 16 }}>
                <span style={{ color: '#64748B', fontSize: 11 }}>{formatACV(account.acv)} ACV</span>
                <span style={{ color: '#4B5E78', fontSize: 11 }}>{account.renewalDate}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
