import { useState } from 'react';
import { X } from 'lucide-react';
import { Link } from 'react-router-dom';

export function BusinessTransferPage() {
  const [signed, setSigned] = useState(false);

  return (
    <div className="business-transfer page-content">
      <div className="business-transfer-top"><span>KBC Business PRO</span><Link to="/accounts" aria-label="Close business transfer"><X size={24} /></Link></div>
      <div className="business-progress"><small>Step 3 of 3</small><strong>Your account</strong><div className="progress-track"><span /></div></div>
      <h1>Your transfer to your new<br />business account</h1>
      <dl className="business-transfer-details">
        <dt>From</dt><dd>PEETERS-SIMONS DEMO J &amp; A</dd>
        <dt>To</dt><dd>SIMONS-PEETERS BV</dd>
        <dt>Amount</dt><dd>100,00 EUR</dd>
      </dl>
      {signed ? <p className="demo-confirmation" role="status">Demo only — no payment was sent.</p> : <button className="primary-button" type="button" onClick={() => setSigned(true)}>Sign</button>}
    </div>
  );
}
