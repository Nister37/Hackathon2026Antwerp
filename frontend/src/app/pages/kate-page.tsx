import { useState } from 'react';
import { CreditCard, MessageCircle, PiggyBank, Search, WalletCards, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TransactionStatus } from '../components/transaction-status';
import { formatAmount, formatShortDate, type TransactionState } from '../transactions';
import { userName, type UserId, type UserProfile } from '../user-profile';

export function KatePage({ activeUser, users, transactions }: { activeUser: UserId; users: UserProfile[]; transactions: TransactionState }) {
  const [showPayments, setShowPayments] = useState(true);
  const [notices, setNotices] = useState([true, true]);

  return (
    <div className="kate-page page-content">
      <h1 className="sr-only">Kate</h1>
      <div className="kate-top"><Link to="/personal" className="kate-avatar" aria-label={`Back to ${userName(users, activeUser)} start`}>{userName(users, activeUser).charAt(0)}</Link><label className="kate-search"><Search size={17} aria-hidden="true" /><span className="sr-only">Ask Kate</span><input placeholder="Hoe kan ik je helpen?" /><strong>Kate</strong></label></div>
      <div className="personal-card-strip kate-cards" aria-label="Accounts and cards">
        <article className="personal-tile"><div className="personal-tile-art"><WalletCards size={50} strokeWidth={1.2} /></div><span>Simons - Peeters</span><strong>8 213,85 <small>EUR</small></strong><div className="tile-line" /></article>
        <article className="personal-tile"><div className="kate-photo" role="img" aria-label="Smiling account holder" /><span>Persoonlijke reke...</span><strong>1 042,85 <small>EUR</small></strong></article>
        <article className="personal-tile"><div className="personal-tile-art personal-tile-art--card"><CreditCard size={48} /></div><span>Simons - Peet</span><strong>213,85 <small>EUR</small></strong></article>
      </div>
      <div className="kate-transactions" aria-label="Recent transactions">
        {transactions.status === 'ready' ? <>
          {showPayments && transactions.items.slice(0, 3).map(({ date, merchant, amount }) => <p key={`${date}-${merchant}`}><time dateTime={date}>{formatShortDate(date)}</time><strong>{merchant}</strong><span>{formatAmount(amount)}</span></p>)}
          <button type="button" aria-expanded={showPayments} onClick={() => setShowPayments((show) => !show)}>{showPayments ? 'Verberg verrichtingen' : 'Toon verrichtingen'}</button>
        </> : <TransactionStatus status={transactions.status} />}
      </div>
      <h2>Meldingen</h2>
      <div className="kate-notices">
        {notices[0] && <article className="message-card"><MessageCircle size={27} aria-hidden="true" /><p><strong>Kate tip</strong><br />Van de Ardennen tot de kust: reis deze zomer vlot door ons land met KBC Mobile.</p><button aria-label="Dismiss travel tip" type="button" onClick={() => setNotices(([_, second]) => [false, second])}><X size={17} /></button></article>}
        {notices[1] && <article className="message-card"><PiggyBank size={27} aria-hidden="true" /><p><strong>Kate tip</strong><br />Ontdek nu de nieuwe mogelijkheden van KBC Mobile!</p><button aria-label="Dismiss KBC Mobile tip" type="button" onClick={() => setNotices(([first]) => [first, false])}><X size={17} /></button></article>}
      </div>
    </div>
  );
}
