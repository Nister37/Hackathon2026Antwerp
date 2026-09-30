import { useState } from 'react';
import { CreditCard, Lightbulb, MessageCircle, PiggyBank, WalletCards, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TransactionStatus } from '../components/transaction-status';
import { InsightCard } from '../components/insight-card';
import type { InsightState } from '../insight';
import { formatAmount, formatShortDate, type TransactionState } from '../transactions';
import { userName, type UserId, type UserProfile } from '../user-profile';

export function MobileStartPage({ activeUser, users, transactions, insight }: { activeUser: UserId; users: UserProfile[]; transactions: TransactionState; insight: InsightState }) {
  const [showTransactions, setShowTransactions] = useState(true);
  const [showFirstNotice, setShowFirstNotice] = useState(true);
  const [showSecondNotice, setShowSecondNotice] = useState(true);

  return (
    <div className="personal-start page-content">
      <header className="personal-header"><h1>{userName(users, activeUser)}</h1><Link to="/kate" aria-label="Open Kate assistant"><MessageCircle size={20} aria-hidden="true" /></Link></header>
      <div className="personal-card-strip" aria-label="Accounts and cards">
        <article className="personal-tile"><div className="personal-tile-art"><WalletCards size={52} strokeWidth={1.15} /></div><span>SIMONS DEMO A...</span><strong>158,60 <small>EUR</small></strong><div className="tile-line" /></article>
        <article className="personal-tile"><div className="personal-tile-art"><PiggyBank size={52} strokeWidth={1.15} /></div><span>SIMONS DEMO A...</span><strong>10 000,00 <small>EUR</small></strong></article>
        <article className="personal-tile"><div className="personal-tile-art personal-tile-art--card"><CreditCard size={52} strokeWidth={1.15} /></div><span>SIMONS DEMO A...</span><strong>1 194,33 <small>EUR</small></strong></article>
      </div>
      <section className="personal-transactions" aria-label="Recent payments">
        {transactions.status === 'ready' ? <>
          {showTransactions && transactions.items.slice(0, 3).map(({ date, merchant, amount }) => <div className="personal-transaction" key={`${date}-${merchant}`}><time dateTime={date}>{formatShortDate(date)}</time><strong>{merchant}</strong><span>{formatAmount(amount)}</span></div>)}
          <button className="collapse-payments" type="button" aria-expanded={showTransactions} onClick={() => setShowTransactions((show) => !show)}>{showTransactions ? 'Hide payments' : 'Show payments'}</button>
        </> : <TransactionStatus status={transactions.status} />}
      </section>
      <section className="personal-news" aria-label="Messages">
        <article className="message-card personal-insight"><InsightCard insight={insight} interactive /></article>
        {showFirstNotice && <article className="message-card"><span className="message-icon">NW</span><p>Financieel nieuws: Na Colruyt en Lidl, ook Carrefour en Aldi beperken verkoop van producten: "Nog geen tekorten, maar consumenten kopen plots meer"</p><button type="button" aria-label="Dismiss financial news" onClick={() => setShowFirstNotice(false)}><X size={18} /></button></article>}
        {showSecondNotice && <article className="message-card"><Lightbulb size={30} className="tip-icon" aria-hidden="true" /><p>Your free trial period for Spotify has ended. You paid 9,99 EUR for the first time.</p><button type="button" aria-label="Dismiss Spotify message" onClick={() => setShowSecondNotice(false)}><X size={18} /></button></article>}
      </section>
    </div>
  );
}
