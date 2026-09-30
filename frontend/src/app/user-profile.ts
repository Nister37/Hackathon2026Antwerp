export type UserId = '1' | '2';

export type UserProfile = { id: UserId; displayName: string };

export function userLabel(users: UserProfile[], id: UserId): string {
  const name = users.find((user) => user.id === id)?.displayName;
  return name ? `User ${id} · ${name}` : `User ${id}`;
}

export function userName(users: UserProfile[], id: UserId): string {
  return users.find((user) => user.id === id)?.displayName ?? `User ${id}`;
}
