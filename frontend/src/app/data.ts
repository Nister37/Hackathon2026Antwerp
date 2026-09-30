export const attentionItems = [
  { label: 'Payments to be authorised', count: 15 },
  { label: 'Due payments', count: 15 },
  { label: 'Rejected payments', count: 22 },
  { label: 'Alerts', count: 9 },
];

export const balances = [
  { suffix: 'BE1', amount: '107.09 EUR' },
  { suffix: 'BE2', amount: '13,968.53 EUR' },
  { suffix: 'BE3', amount: '141.24 EUR' },
  { suffix: 'FR7', amount: '804.73 EUR' },
];

export const settingsGroups = [
  { title: 'Dashboard', icon: 'dashboard', items: ['Companies', 'Administrators', 'Digital signers', 'Authorisers'] },
  { title: 'Users', icon: 'users', items: ['Manage users', 'New users'] },
  { title: 'Applications', icon: 'applications', items: ['In use', 'To be added'] },
  { title: 'Powers of attorney', icon: 'document', items: ['Powers of attorney'] },
  { title: 'Accounts and cards', icon: 'accounts', items: ['KBC Accounts', 'Use by third parties'] },
  { title: 'Certificates', icon: 'certificate', items: ['Certificates', 'Apply online'] },
  { title: 'Business communication', icon: 'communication', items: ['Invoice preferences', 'Documents', 'Notifications'] },
  { title: 'Data connections', icon: 'connections', items: ['Import data', 'Export data'] },
] as const;
