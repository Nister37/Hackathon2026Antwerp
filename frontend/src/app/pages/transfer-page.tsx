import { useState, useSyncExternalStore } from 'react';
import { ArrowLeft, CalendarDays, CircleHelp, CreditCard, Gift, Send, WalletCards, X } from 'lucide-react';
import { Link } from 'react-router-dom';

type TransferType = 'sepa' | 'international';
type TransferMode = 'initial' | 'form' | 'review';

function subscribeToMobile(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const media = window.matchMedia('(max-width: 740px)');
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

function isMobileViewport() {
  return typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 740px)').matches;
}

export function TransferPage() {
  const isMobile = useSyncExternalStore(subscribeToMobile, isMobileViewport, () => false);
  const [mode, setMode] = useState<TransferMode>('initial');
  const [type, setType] = useState<TransferType>('international');
  const [recipient, setRecipient] = useState('ACOMPANY');
  const [account, setAccount] = useState('AE02020202000000301223134');
  const [amount, setAmount] = useState('200,00');
  const [reference, setReference] = useState('');
  const [signed, setSigned] = useState(false);
  const [surprisePay, setSurprisePay] = useState(false);
  const [date, setDate] = useState<'Today' | 'Tomorrow'>('Today');
  const [sourceAccount, setSourceAccount] = useState<'SIMONS DEMO ANNE' | 'PATRICK PETERS'>('SIMONS DEMO ANNE');

  const isInitialMobileReview = mode === 'initial' && isMobile;
  const reviewing = mode === 'review' || isInitialMobileReview;
  const reviewType = isInitialMobileReview ? 'sepa' : type;
  const reviewRecipient = isInitialMobileReview ? 'PETER NEWTON' : recipient;
  const reviewAmount = isInitialMobileReview ? '1,00' : amount;
  const reviewReference = isInitialMobileReview ? 'Test' : reference;

  const selectType = (next: TransferType) => {
    setType(next);
    setRecipient(next === 'sepa' ? 'PETER NEWTON' : 'ACOMPANY');
    setAccount(next === 'sepa' ? '' : 'AE02020202000000301223134');
    setAmount(next === 'sepa' ? '1,00' : '200,00');
    setSigned(false);
  };

  const editTransfer = () => {
    if (isInitialMobileReview) {
      setType('sepa');
      setRecipient('PETER NEWTON');
      setAccount('');
      setAmount('1,00');
      setReference('Test');
    }
    setMode('form');
    setSigned(false);
  };

  if (reviewing) {
    return (
      <div className="transfer-review page-content">
        <div className="review-top"><button type="button" className="icon-button" onClick={editTransfer} aria-label="Edit transfer"><ArrowLeft /></button><Link to={isMobile ? '/personal' : '/'} aria-label="Close transfer"><X /></Link></div>
        <div className="recipient-avatar" aria-hidden="true">{reviewRecipient.charAt(0)}</div>
        <h1>{reviewRecipient}</h1>
        <strong className="review-amount">{reviewAmount} {reviewType === 'sepa' ? 'EUR' : 'GBP'}</strong>
        <p className="review-reference">{reviewReference}</p>
        <div className="review-details">
          {reviewType === 'sepa' && <div className="review-detail-row"><Gift size={25} aria-hidden="true" /><span>Send a SurprisePay card<small>More info</small></span><label className="switch"><span className="sr-only">Send a SurprisePay card</span><input type="checkbox" checked={surprisePay} onChange={(event) => setSurprisePay(event.target.checked)} /><span aria-hidden="true" /></label></div>}
          <div className="review-detail-row"><CalendarDays size={25} aria-hidden="true" /><span>Date<strong>{date}</strong></span><button type="button" onClick={() => setDate((current) => current === 'Today' ? 'Tomorrow' : 'Today')}>Change</button></div>
          <div className="review-detail-row"><WalletCards size={26} aria-hidden="true" /><span>Transfer from<strong>{reviewType === 'sepa' ? sourceAccount : 'PATRICK PETERS'}</strong>{reviewType === 'sepa' && <small>158,60 EUR</small>}</span>{reviewType === 'sepa' && <button type="button" onClick={() => setSourceAccount((current) => current === 'SIMONS DEMO ANNE' ? 'PATRICK PETERS' : 'SIMONS DEMO ANNE')}>Change</button>}</div>
        </div>
        {signed ? <p className="demo-confirmation" role="status">Demo only — no payment was sent.</p> : <button className="primary-button" type="button" onClick={() => setSigned(true)}>Sign</button>}
      </div>
    );
  }

  return (
    <div className="transfer-workspace">
      <header className="transfer-workspace-header">
        <span className="transfer-workspace-logo">KBC</span>
        <span className="transfer-workspace-title">Enter transfer details <CircleHelp size={19} aria-hidden="true" /></span>
        <Link to={isMobile ? '/personal' : '/'} aria-label="Close transfer"><X size={22} /></Link>
      </header>
      <aside className="transfer-rail" aria-label="Transfer navigation">
        <Link to="/accounts" className="transfer-rail-link"><CreditCard size={22} aria-hidden="true" /><span>Business</span></Link>
        <span className="transfer-rail-current"><Send size={22} aria-hidden="true" /><span>Payments</span></span>
        <Link to="/personal" className="transfer-rail-link"><WalletCards size={22} aria-hidden="true" /><span>Personal</span></Link>
      </aside>
      <div className="transfer-page page-content">
        <button type="button" className="transfer-mobile-back" onClick={() => setMode('review')}><ArrowLeft size={20} aria-hidden="true" />Back to review</button>
        <h1>Transfer</h1>
        <div className="transfer-tabs" role="group" aria-label="Transfer type">
          <button type="button" aria-pressed={type === 'sepa'} onClick={() => selectType('sepa')}>SEPA Credit Transfer</button>
          <button type="button" aria-pressed={type === 'international'} onClick={() => selectType('international')}>International transfer</button>
        </div>
        <form className="transfer-form" onSubmit={(event) => { event.preventDefault(); setMode('review'); }}>
          <div className="form-row form-row--from"><span className="form-label">From</span><div className="form-value transfer-from-value"><span className="transfer-account-art" aria-hidden="true"><WalletCards size={22} /></span><span><strong>PATRICK PETERS</strong><small>BE64 7351 4830 0052<br />KBC Account</small></span></div><span className="transfer-balance">Balance<strong>29 061,10 EUR</strong></span></div>
          <div className="form-row form-row--to"><label className="form-label" htmlFor="recipient">To</label><div className="form-fields"><input id="recipient" value={recipient} onChange={(event) => setRecipient(event.target.value)} required /><div className="transfer-recipient-details"><div><label htmlFor="recipient-account">Account</label><input id="recipient-account" value={account} onChange={(event) => setAccount(event.target.value)} required />{type === 'international' && <small>BBMEAEA</small>}</div>{type === 'international' && <div className="transfer-address"><span>Address</span><strong>DTREET 111<br />9999 HANNOVER<br />GERMANY</strong></div>}</div></div></div>
          <div className="form-row"><label className="form-label" htmlFor="amount">Amount</label><div className="inline-fields"><input id="amount" value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" required /><select aria-label="Currency" defaultValue={type === 'sepa' ? 'EUR' : 'GBP'} key={type}><option value="EUR">EUR - Euro</option><option value="GBP">GBP - Pound sterling</option></select></div></div>
          <div className="form-row"><span className="form-label">Charges</span><span className="form-value">Principal pays all charges</span></div>
          <div className="form-row"><label className="form-label" htmlFor="reference">Reference <small>required</small></label><input id="reference" placeholder="Free format" value={reference} onChange={(event) => setReference(event.target.value)} required /></div>
          <div className="transfer-form-actions"><button className="calculate-button" type="submit" disabled={!reference.trim()}>Calculate charges</button></div>
        </form>
      </div>
    </div>
  );
}
