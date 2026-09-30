import { useState } from 'react';
import { CreditCard, WalletCards } from 'lucide-react';
import { Link } from 'react-router-dom';
import { balances } from '../data';

export function AccountsPage() {
  const [view, setView] = useState<'personal' | 'business'>('personal');

  return (
    <div className="accounts-page page-content">
      <h1>My KBC</h1>
      <div className="account-tabs" role="group" aria-label="Account type">
        <button type="button" aria-pressed={view === 'personal'} onClick={() => setView('personal')}>Personal</button>
        <button type="button" aria-pressed={view === 'business'} onClick={() => setView('business')}>Business</button>
      </div>
      {view === 'business' ? (
        <section className="account-section" aria-label="Business accounts">
          <div className="section-title-row"><h2>Accounts</h2><Link to="/business-transfer">New transfer</Link></div>
          <div className="account-card-grid">
            {balances.map(({ suffix, amount }) => (
              <article className="account-card" key={suffix}>
                <div className="account-card-art"><WalletCards size={39} strokeWidth={1.25} aria-hidden="true" /></div>
                <div className="account-card-copy"><span>KBC B INTERNAT. CASHMANAGEMENT - {suffix}</span><strong>{amount}</strong></div>
              </article>
            ))}
          </div>
        </section>
      ) : (
        <>
          <section className="account-section" aria-labelledby="personal-accounts"><h2 id="personal-accounts">Accounts</h2>
            <article className="personal-account-row"><span className="small-account-art"><WalletCards size={27} /></span><span>PEETERS-SIMONS DE...</span><strong>130 002,03 EUR</strong></article>
            <button className="all-accounts-button" type="button" onClick={() => setView('business')}>All accounts</button>
          </section>
          <section className="account-section" aria-labelledby="means-payment"><h2 id="means-payment">Means of payment</h2>
            <div className="payment-card-row"><CreditCard size={31} aria-hidden="true" /><span>KBC Debit Card<br /><small>SIMONS DEMO ANNE<br />**** 5011</small></span></div>
            <div className="payment-card-row"><CreditCard size={31} aria-hidden="true" /><span>KBC Debit Card<br /><small>PEETERS JAN<br />**** 3011</small></span></div>
          </section>
        </>
      )}
    </div>
  );
}
