export type Health = 'green' | 'amber' | 'red';

export interface TimelineEvent {
  date: string;
  title: string;
  description: string;
  type: 'milestone' | 'win' | 'watch' | 'escalation' | 'roadmap';
}

export interface BVAItem {
  outcome: string;
  icon: string;
  before: string;
  after: string;
  delta: string;
  deltaColor: 'green' | 'blue' | 'teal';
}

export interface Opportunity {
  signalType: 'over-consumption' | 'pro-tier' | 'es-pipeline' | 'faint-signal';
  title: string;
  description: string;
  value: string;
}

export interface Account {
  id: string;
  name: string;
  health: Health;
  acv: number;
  renewalDate: string;
  economicBuyer: { name: string; title: string };
  csm: string;
  products: string[];
  adoptionPct: number;
  adoptionTrend: number;
  adoptionHistory: number[];
  timeline: TimelineEvent[];
  bva: BVAItem[];
  opportunities: Opportunity[];
  dataSources: string[];
}
