import { useState } from 'react';
import { Search } from 'lucide-react';
import { TransactionStatus } from '../components/transaction-status';
import { formatAmount, type TransactionState } from '../transactions';
import { userLabel, type UserId, type UserProfile } from '../user-profile';

export function TimelinePage({ activeUser, users, transactions }: { activeUser: UserId; users: UserProfile[]; transactions: TransactionState }) {
  const [query, setQuery] = useState('');
  const visible = transactions.items.filter(({ merchant, category, city }) =>
    [merchant, category, city].some((value) => value.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div className="timeline-page page-content">
      <h1>Transactions</h1>
      <div className="timeline-layout">
        <section className="timeline-content" aria-label="Recent transactions">
          <div className="timeline-account">
            <div><strong>{userLabel(users, activeUser)}</strong>{transactions.items[0] && <small>{transactions.items[0].city}</small>}</div>
            <label className="timeline-search"><span className="sr-only">Search transactions</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search transactions" /><Search size={18} aria-hidden="true" /></label>
          </div>
          {transactions.status === 'ready' ? <ol className="timeline-list">
            {visible.map(({ date, merchant, amount, category }, index) => (
              <li key={`${date}-${merchant}-${index}`}>
                <time dateTime={date}>{date}</time><span className="timeline-dot" aria-hidden="true" />
                <span className="timeline-entry"><strong>{merchant}<small>{category}</small></strong><span>{formatAmount(amount)}</span></span>
              </li>
            ))}
          </ol> : <TransactionStatus status={transactions.status} />}
          {transactions.status === 'ready' && visible.length === 0 && <p className="timeline-empty">No matching transactions</p>}
        </section>
      </div>
    </div>
  );
}
