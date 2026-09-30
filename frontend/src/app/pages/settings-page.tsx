import { AppWindow, BadgeCheck, FileText, LayoutDashboard, Link2, MessageCircle, UsersRound, WalletCards } from 'lucide-react';
import { Link } from 'react-router-dom';
import { settingsGroups } from '../data';
import { userLabel, type UserId, type UserProfile } from '../user-profile';

const icons = {
  dashboard: LayoutDashboard,
  users: UsersRound,
  applications: AppWindow,
  document: FileText,
  accounts: WalletCards,
  certificate: BadgeCheck,
  communication: MessageCircle,
  connections: Link2,
} as const;

export function SettingsPage({ activeUser, users }: { activeUser: UserId; users: UserProfile[] }) {
  return (
    <div className="settings-page page-content">
      <h1>Business settings</h1>
      <Link className="mobile-user-settings-link" to="/user-settings">User settings <span>{userLabel(users, activeUser)}</span></Link>
      <div className="settings-grid">
        {settingsGroups.map(({ title, icon, items }) => {
          const Icon = icons[icon];
          return (
            <section className="settings-card" key={title} aria-labelledby={`settings-${icon}`}>
              <h2 id={`settings-${icon}`}><Icon size={29} strokeWidth={1.45} aria-hidden="true" />{title}</h2>
              <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
