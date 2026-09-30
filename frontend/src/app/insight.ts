export type Insight = {
  title: string;
  summary: string;
  evidence: string[];
};

export type InsightState = {
  item: Insight | null;
  status: 'loading' | 'ready' | 'error';
};
