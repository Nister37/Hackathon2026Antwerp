import type { TransactionState } from '../transactions';

export function TransactionStatus({ status }: { status: TransactionState['status'] }) {
  return status === 'error'
    ? <p className="transaction-status" role="alert">Transactions unavailable. Check the backend connection.</p>
    : <p className="transaction-status" role="status">Loading transactions…</p>;
}
