import { ArrowRight, CreditCard } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Widget } from '../components/widget';
import { TransactionStatus } from '../components/transaction-status';
import { InsightCard } from '../components/insight-card';
import type { InsightState } from '../insight';
import { attentionItems, balances } from '../data';
import { formatAmount, formatShortDate, type TransactionState } from '../transactions';

function SpendingChart({ transactions }: { transactions: TransactionState }) {
  if (transactions.status !== 'ready') return <TransactionStatus status={transactions.status} />;
  const spending = transactions.items.filter(({ amount }) => amount < 0).slice(0, 7).reverse();
  if (spending.length === 0) return <p className="transaction-status">No spending transactions in this period.</p>;
  const maximum = Math.ceil(Math.max(...spending.map(({ amount }) => -amount)) / 20) * 20;

  return (
    <figure className="balance-chart">
      <figcaption>(in EUR)</figcaption>
      <div className="chart-body" role="img" aria-label={`Spending by date: ${spending.map(({ date, amount }) => `${formatShortDate(date)}, ${formatAmount(-amount)}`).join('; ')}`}>
        <div className="chart-y-axis" aria-hidden="true"><span>{maximum}</span><span>{Math.round(maximum * 2 / 3)}</span><span>{Math.round(maximum / 3)}</span><span>0</span></div>
        <div className="chart-plot" aria-hidden="true">
          {spending.map(({ date, amount, merchant }) => (
            <div className="chart-column" key={`${date}-${merchant}`}>
              <span className={`chart-bar chart-bar--${Math.max(1, Math.round((-amount / maximum) * 10))}`} />
              <span className="chart-label">{formatShortDate(date)}</span>
            </div>
          ))}
        </div>
      </div>
    </figure>
  );
}

export function DashboardPage({ transactions, insight }: { transactions: TransactionState; insight: InsightState }) {
  const recent = transactions.items.slice(0, 3);

  return (
    <div className="dashboard-grid">
      <h1 className="sr-only">KBC Reach dashboard</h1>
      <Widget title="For your attention" className="attention-widget" destination="/transfer">
        <ul className="attention-list">
          {attentionItems.map(({ label, count }) => (
            <li key={label}><Link to="/transfer"><span>{label}</span><strong>{count}</strong></Link></li>
          ))}
        </ul>
      </Widget>

      <Widget title="Balances by currencies" className="currency-widget" destination="/accounts">
        <div className="unit-label">(in K EUR)</div>
        <div className="donut" role="img" aria-label="Balances by currencies: 15.0 thousand euros, EUR"><span>15.0</span></div>
        <div className="donut-label">EUR</div>
      </Widget>

      <Widget title="Favourite views" className="favourites-widget" destination="/accounts">
        <ul className="plain-list">
          <li><Link className="link-accent" to="/accounts">Balances</Link></li>
          <li><Link to="/accounts">Balances based on account statements</Link></li>
        </ul>
      </Widget>

      <Widget title="Balances" className="balances-widget" destination="/accounts">
        <ul className="balance-list">
          {balances.map(({ suffix, amount }) => (
            <li key={suffix}>
              <Link to="/accounts" aria-label={`KBC B Internat. Cashmanagement ${suffix}, ${amount}`}>
                <span className="mobile-account-art" aria-hidden="true"><CreditCard size={31} strokeWidth={1.4} /></span>
                <span className="balance-copy"><span className="balance-name">KBC B INTERNAT. CASHMANAGEMENT - {suffix}</span><strong>{amount}</strong></span>
                <ArrowRight size={18} className="balance-arrow" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </Widget>

      <Widget title="Recent transactions" className="transactions-widget" destination="/timeline">
        {transactions.status === 'ready' ? <ul className="transaction-list">
          {recent.map(({ date, merchant, amount, category }) => (
            <li key={`${date}-${merchant}`}>
              <Link to="/timeline">
                <span className="transaction-copy"><strong>{category}</strong><span>{formatShortDate(date)}</span><span>{merchant}</span></span>
                <span className="transaction-amount">{formatAmount(amount)}</span>
              </Link>
            </li>
          ))}
        </ul> : <TransactionStatus status={transactions.status} />}
      </Widget>

      <Widget title="Spending by date" className="chart-widget" destination="/timeline"><SpendingChart transactions={transactions} /></Widget>
      <Widget title="LifeLine insight" className="insight-widget"><InsightCard insight={insight} /></Widget>
    </div>
  );
}
