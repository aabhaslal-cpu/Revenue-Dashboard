import { useState, useRef, useEffect } from 'react';
import { X, Copy, Send, Check } from 'lucide-react';
import type { Account } from '../types';

function buildAccountContext(account: Account): string {
  return `
ACCOUNT: ${account.name}
Health: ${account.health} | ACV: $${account.acv.toLocaleString()} | Renewal: ${account.renewalDate}
Economic Buyer: ${account.economicBuyer.name}, ${account.economicBuyer.title}
CSM: ${account.csm}
Products: ${account.products.join(', ')}
Adoption: ${account.adoptionPct}% (${account.adoptionTrend > 0 ? '+' : ''}${account.adoptionTrend}% QoQ)

BUSINESS VALUE:
${account.bva.map(b => `- ${b.outcome}: ${b.before} → ${b.after} (${b.delta})`).join('\n')}

TIMELINE:
${account.timeline.map(e => `- ${e.date}: ${e.title} [${e.type}] — ${e.description}`).join('\n')}

REVENUE OPPORTUNITIES:
${account.opportunities.map(o => `- ${o.title} (${o.value}): ${o.description}`).join('\n')}
`.trim();
}

const actionPrompts: Record<string, string> = {
  'Build renewal story': `You are a Customer Success expert. Based on the account context below, craft a compelling renewal story for a CS director to use in a renewal meeting. Structure it as: (1) What we delivered — 3 specific business outcomes with numbers, (2) The relationship arc — acknowledge challenges and how they were resolved, (3) Why renewing is the clear choice — forward momentum and roadmap. Be specific, crisp, and confident. Avoid filler. Use executive language.\n\nACCOUNT CONTEXT:\n`,
  'Draft expansion email': `You are a Customer Success expert. Based on the account context below, draft a concise expansion email from the CSM to the economic buyer. The email should: reference a specific win or recent positive moment, introduce one or two expansion opportunities that are natural given their usage, and propose a 20-minute call. Tone: warm but direct. Length: under 200 words. No bullet points — write in prose.\n\nACCOUNT CONTEXT:\n`,
  'Pre-call brief': `You are a Customer Success expert. Create a 60-second pre-call brief for a CS director walking into a meeting with this account. Format: (1) One-line account status, (2) What went well (2 bullets), (3) What needs care (1-2 bullets), (4) The ask or objective for this call. Be blunt. Assume the director has zero context. Write like a smart colleague briefing you in the elevator.\n\nACCOUNT CONTEXT:\n`,
};

interface Props {
  account: Account;
  action: string | null;
  onClose: () => void;
}

export function AIDrawer({ account, action, onClose }: Props) {
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [copied, setCopied] = useState(false);
  const responseRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const context = buildAccountContext(account);

  async function streamResponse(prompt: string) {
    setResponse('');
    setLoading(true);

    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch('/api/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
        signal: ctrl.signal,
      });

      if (!res.ok) {
        const err = await res.text();
        setResponse(`Error: ${err}`);
        setLoading(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let accumulated = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.text) {
                accumulated += parsed.text;
                setResponse(accumulated);
              }
            } catch { /* ignore parse errors */ }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setResponse('Failed to connect to AI. Make sure the API server is running and ANTHROPIC_API_KEY is set.');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (action) {
      const basePrompt = actionPrompts[action] ?? `Answer the following about this account:\n\n`;
      streamResponse(basePrompt + context);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, account.id]);

  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response]);

  function handleAsk() {
    if (!question.trim()) return;
    const prompt = `You are a Customer Success intelligence system. Answer the following question about the account below. Be specific and cite data from the context.\n\nQuestion: ${question}\n\nACCOUNT CONTEXT:\n${context}`;
    streamResponse(prompt);
    setQuestion('');
  }

  function handleCopy() {
    navigator.clipboard.writeText(response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const title = action ? `${action} — ${account.name}` : `Ask about ${account.name}`;

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
          zIndex: 100, backdropFilter: 'blur(2px)',
        }}
      />
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 520,
        background: '#fff',
        zIndex: 101,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '-4px 0 24px rgba(0,0,0,0.12)',
      }}>
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: '#0F172A' }}>{title}</div>
            <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>Powered by Claude</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {response && (
              <button onClick={handleCopy} style={{ padding: '6px 12px', border: '1px solid #E2E8F0', borderRadius: 6, background: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#64748B' }}>
                {copied ? <Check size={13} color="#22C55E" /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
            <button onClick={onClose} style={{ padding: 6, border: 'none', background: 'transparent', cursor: 'pointer', color: '#94A3B8' }}>
              <X size={18} />
            </button>
          </div>
        </div>

        <div style={{ padding: '16px 24px', borderBottom: '1px solid #F1F5F9' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAsk()}
              placeholder="Ask anything about this account…"
              style={{
                flex: 1,
                border: '1px solid #E2E8F0',
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 13,
                color: '#0F172A',
                outline: 'none',
              }}
            />
            <button
              onClick={handleAsk}
              disabled={!question.trim()}
              style={{
                padding: '8px 14px',
                background: '#0D9488',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                cursor: 'pointer',
                opacity: question.trim() ? 1 : 0.5,
              }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>

        <div ref={responseRef} style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          {loading && !response && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', color: '#94A3B8', fontSize: 13 }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#0D9488', animation: 'pulse 1s infinite' }} />
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#0D9488', animation: 'pulse 1s 0.2s infinite' }} />
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#0D9488', animation: 'pulse 1s 0.4s infinite' }} />
              <span style={{ marginLeft: 4 }}>Generating…</span>
            </div>
          )}
          {response && (
            <div style={{ fontSize: 14, color: '#334155', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {response}
              {loading && <span style={{ display: 'inline-block', width: 2, height: 16, background: '#0D9488', marginLeft: 2, animation: 'blink 1s infinite', verticalAlign: 'text-bottom' }} />}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
