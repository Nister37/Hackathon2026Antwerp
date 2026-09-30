import { useEffect, useState } from 'react';
import {
  Bell, ChartNoAxesCombined, CreditCard, Globe2, House, Menu,
  Send, Settings, Star, UserRound,
} from 'lucide-react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { AccountsPage } from './pages/accounts-page';
import { DashboardPage } from './pages/dashboard-page';
import { MobileStartPage } from './pages/mobile-start-page';
import { KatePage } from './pages/kate-page';
import { BusinessTransferPage } from './pages/business-transfer-page';
import { SettingsPage } from './pages/settings-page';
import { TimelinePage } from './pages/timeline-page';
import { TransferPage } from './pages/transfer-page';
import { UserSettingsPage } from './pages/user-settings-page';
import { type Transaction, type TransactionState } from './transactions';
import { type Insight, type InsightState } from './insight';
import { userLabel, type UserId, type UserProfile } from './user-profile';
import './app.scss';

const desktopNavigation = [
  { to: '/', label: 'Reach dashboard', icon: ChartNoAxesCombined },
  { to: '/personal', label: 'Personal start', icon: Star },
  { to: '/transfer', label: 'Payments', icon: Send },
  { to: '/accounts', label: 'Accounts and cards', icon: CreditCard },
  { to: '/timeline', label: 'Business dashboard', icon: House },
  { to: '/settings', label: 'Business settings', icon: Settings },
  { to: '/user-settings', label: 'User settings', icon: UserRound },
] as const;

const mobileNavigation = [
  { to: '/personal', label: 'Start', icon: House },
  { to: '/accounts', label: 'My KBC', icon: CreditCard },
  { to: '/transfer', label: 'Payments', icon: Send },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

function initialUser(): UserId {
  try {
    return localStorage.getItem('kbc-demo-user') === '2' ? '2' : '1';
  } catch {
    return '1';
  }
}

export function App() {
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [activeUser, setActiveUser] = useState<UserId>(initialUser);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [usersStatus, setUsersStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [loadedTransactions, setLoadedTransactions] = useState<{
    user: UserId;
    items: Transaction[];
    status: 'ready' | 'error';
  } | null>(null);
  const [loadedInsight, setLoadedInsight] = useState<{
    user: UserId;
    item: Insight | null;
    status: 'ready' | 'error';
  } | null>(null);
  const standalone = pathname === '/transfer' || pathname === '/business-transfer';
  const noToolbarOnMobile = standalone || ['/personal', '/kate', '/accounts'].includes(pathname);
  const transactionState: TransactionState = loadedTransactions?.user === activeUser
    ? { items: loadedTransactions.items, status: loadedTransactions.status }
    : { items: [], status: 'loading' };
  const insightState: InsightState = loadedInsight?.user === activeUser
    ? { item: loadedInsight.item, status: loadedInsight.status }
    : { item: null, status: 'loading' };

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/users', { signal: controller.signal, headers: { Accept: 'application/json' } })
      .then((response) => {
        if (!response.ok) throw new Error('Users request failed');
        return response.json() as Promise<UserProfile[]>;
      })
      .then((profiles) => {
        if (!Array.isArray(profiles) || profiles.length !== 2 ||
            !profiles.some((user) => user.id === '1') || !profiles.some((user) => user.id === '2')) {
          throw new Error('Unexpected users response');
        }
        setUsers(profiles);
        setUsersStatus('ready');
      })
      .catch(() => {
        if (!controller.signal.aborted) setUsersStatus('error');
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/users/${activeUser}/transactions?limit=8`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
      .then((response) => {
        if (!response.ok) throw new Error('Transactions request failed');
        return response.json() as Promise<Transaction[]>;
      })
      .then((items) => {
        if (!Array.isArray(items)) throw new Error('Unexpected transactions response');
        setLoadedTransactions({ user: activeUser, items, status: 'ready' });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoadedTransactions({ user: activeUser, items: [], status: 'error' });
      });
    return () => controller.abort();
  }, [activeUser]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/users/${activeUser}/insight`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
      .then((response) => {
        if (!response.ok) throw new Error('Insight request failed');
        return response.json() as Promise<Insight>;
      })
      .then((item) => {
        if (!item || typeof item.title !== 'string' || typeof item.summary !== 'string' ||
            !Array.isArray(item.evidence)) throw new Error('Unexpected insight response');
        setLoadedInsight({ user: activeUser, item, status: 'ready' });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoadedInsight({ user: activeUser, item: null, status: 'error' });
      });
    return () => controller.abort();
  }, [activeUser]);

  const switchUser = (user: UserId) => {
    setActiveUser(user);
    try {
      localStorage.setItem('kbc-demo-user', user);
    } catch {
      // The demo remains usable when storage is unavailable.
    }
  };

  return (
    <div className={`app-shell${sidebarOpen ? '' : ' app-shell--sidebar-collapsed'}${noToolbarOnMobile ? ' app-shell--no-toolbar' : ''}${standalone ? ' app-shell--standalone' : ''}`}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {!standalone && <><header className="topbar">
        <button
          className="icon-button menu-button"
          type="button"
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-expanded={sidebarOpen}
          aria-controls="primary-navigation"
          onClick={() => setSidebarOpen((open) => !open)}
        >
          <Menu size={19} />
        </button>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><Globe2 size={29} strokeWidth={1.2} /></span>
          <span>KBC Reach</span>
        </div>
        <div className="topbar-actions">
          <span className="current-user">{userLabel(users, activeUser)}</span>
          <button
            className="icon-button notification-button"
            type="button"
            aria-label="Notifications, 9 alerts"
            aria-expanded={noticeOpen}
            onClick={() => setNoticeOpen((open) => !open)}
          >
            <Bell size={20} /><span className="notification-count">9</span>
          </button>
        </div>
        {noticeOpen && (
          <div className="notice-popover" role="status">
            <strong>Alerts</strong>
            <p>9 alerts are shown in the dashboard sample.</p>
            <button type="button" className="text-button" onClick={() => setNoticeOpen(false)}>Close</button>
          </div>
        )}
      </header>

      <aside id="primary-navigation" className="side-nav" aria-label="Primary navigation">
        <nav>
          {desktopNavigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} aria-label={label} title={label} tabIndex={sidebarOpen ? undefined : -1}>
              <Icon size={21} aria-hidden="true" />
            </NavLink>
          ))}
        </nav>
      </aside></>}

      <main id="main-content" className="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<DashboardPage transactions={transactionState} insight={insightState} />} />
          <Route path="/personal" element={<MobileStartPage activeUser={activeUser} users={users} transactions={transactionState} insight={insightState} />} />
          <Route path="/kate" element={<KatePage activeUser={activeUser} users={users} transactions={transactionState} />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/transfer" element={<TransferPage />} />
          <Route path="/business-transfer" element={<BusinessTransferPage />} />
          <Route path="/timeline" element={<TimelinePage activeUser={activeUser} users={users} transactions={transactionState} />} />
          <Route path="/settings" element={<SettingsPage activeUser={activeUser} users={users} />} />
          <Route path="/user-settings" element={<UserSettingsPage activeUser={activeUser} users={users} usersStatus={usersStatus} onSwitchUser={switchUser} />} />
          <Route path="*" element={<div className="not-found"><h1>Page not found</h1><Link to="/">Return to dashboard</Link></div>} />
        </Routes>
      </main>

      {!standalone && <nav className="bottom-nav" aria-label="Mobile navigation">
        {mobileNavigation.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to}>
            <Icon size={23} strokeWidth={1.5} aria-hidden="true" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>}
    </div>
  );
}

export default App;
