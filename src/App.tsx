import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { AccountHeader } from './components/AccountHeader';
import { BVAPanel } from './components/BVAPanel';
import { Timeline } from './components/Timeline';
import { RevenueSignals } from './components/RevenueSignals';
import { AIDrawer } from './components/AIDrawer';
import { accounts } from './data/accounts';

export default function App() {
  const [selectedId, setSelectedId] = useState(accounts[0].id);
  const [aiAction, setAiAction] = useState<string | null>(null);

  const account = accounts.find(a => a.id === selectedId) ?? accounts[0];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
      <Sidebar accounts={accounts} selectedId={selectedId} onSelect={id => { setSelectedId(id); setAiAction(null); }} />

      <main style={{ flex: 1, background: '#F8FAFC', overflowY: 'auto', minHeight: '100vh' }}>
        <div style={{
          position: 'sticky', top: 0, zIndex: 10,
          background: '#F8FAFC',
          borderBottom: '1px solid #E2E8F0',
          padding: '8px 32px',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
        }}>
          <span style={{
            fontSize: 10, fontWeight: 500,
            background: '#FEF3C7', color: '#92400E',
            padding: '2px 8px', borderRadius: 4,
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
            Demo data
          </span>
        </div>

        <div style={{ padding: '24px 32px', maxWidth: 1100, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <AccountHeader account={account} />
          <BVAPanel bva={account.bva} />
          <Timeline events={account.timeline} />
          <RevenueSignals account={account} onAction={setAiAction} />
        </div>
      </main>

      {aiAction !== null && (
        <AIDrawer
          account={account}
          action={aiAction}
          onClose={() => setAiAction(null)}
        />
      )}

      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; }
        @keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.3 } }
        @keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0 } }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
      `}</style>
    </div>
  );
}
