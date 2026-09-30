import { userLabel, type UserId, type UserProfile } from '../user-profile';

type UserSettingsPageProps = {
  activeUser: UserId;
  users: UserProfile[];
  usersStatus: 'loading' | 'ready' | 'error';
  onSwitchUser: (user: UserId) => void;
};

export function UserSettingsPage({ activeUser, users, usersStatus, onSwitchUser }: UserSettingsPageProps) {
  return (
    <div className="user-settings-page page-content">
      <h1>User settings</h1>
      <section className="user-switcher" aria-labelledby="switch-user-heading">
        <h2 id="switch-user-heading">Switch user</h2>
        <p>Choose one of the two demo users. No login or registration is required.</p>
        {usersStatus === 'error' && <p role="alert">Users unavailable. Check the backend connection.</p>}
        {usersStatus === 'loading' && <p role="status">Loading users…</p>}
        {usersStatus === 'ready' && <div className="user-options" role="group" aria-label="Available users">
          {users.map((user) => (
            <button key={user.id} type="button" aria-pressed={activeUser === user.id} onClick={() => onSwitchUser(user.id)}>
              <span className="user-avatar" aria-hidden="true">{user.id}</span>
              <span>{userLabel(users, user.id)}</span>
              <span className="user-option-state">{activeUser === user.id ? 'Current user' : 'Switch'}</span>
            </button>
          ))}
        </div>}
        <p className="user-demo-note">Only recent transactions change with the user. Balances and cards remain reference samples because the CSV files contain no account balances.</p>
      </section>
    </div>
  );
}
