export type Transaction = {
  date: string;
  amount: number;
  merchant: string;
  category: string;
  city: string;
};

export type TransactionState = {
  items: Transaction[];
  status: 'loading' | 'ready' | 'error';
};

const amountFormatter = new Intl.NumberFormat('nl-BE', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatAmount(amount: number): string {
  return `${amountFormatter.format(amount)} EUR`;
}

export function formatShortDate(date: string): string {
  return `${date.slice(8, 10)}/${date.slice(5, 7)}`;
}
