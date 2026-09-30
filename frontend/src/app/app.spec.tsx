import { afterEach, beforeEach, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './app';

describe('KBC panel', () => {
  const mockFetch = vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    const body = path === '/api/users'
      ? [{ id: '1', displayName: 'Tom' }, { id: '2', displayName: 'Maria' }]
      : path.endsWith('/insight')
        ? path.includes('/api/users/2/')
          ? { title: 'Possible home pattern', summary: 'Your transactions may suggest a move or renovation pattern.', evidence: ['Home spend is EUR 2,598.19', 'Location changed'] }
          : { title: 'Possible travel pattern', summary: 'Your transactions may suggest upcoming travel preparation.', evidence: ['Travel spend is EUR 1,869.50', 'Foreign spend is EUR 550.00'] }
      : path.includes('/api/users/2/')
        ? [{ date: '2026-08-29', amount: -24.26, merchant: 'Cinema', category: 'Other', city: 'Ghent' }]
        : [{ date: '2026-08-31', amount: -25.73, merchant: 'Colruyt', category: 'Groceries', city: 'Brussels' },
          { date: '2026-08-28', amount: 3000, merchant: 'Employer BV', category: 'Income', city: 'Brussels' }];
    return Promise.resolve({ ok: true, json: async () => body });
  });

  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', mockFetch);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    mockFetch.mockClear();
  });

  it('shows the seven Reach dashboard widgets with API transactions and ML insight', async () => {
    await act(async () => { render(<MemoryRouter><App /></MemoryRouter>); });
    expect(screen.getByRole('heading', { name: 'KBC Reach dashboard' })).toBeTruthy();
    expect(screen.getAllByRole('region').length).toBe(7);
    expect(screen.getByRole('heading', { name: 'Recent transactions' })).toBeTruthy();
    expect(await screen.findByText('Employer BV')).toBeTruthy();
    expect(await screen.findByText('Possible travel pattern')).toBeTruthy();
    expect(mockFetch).toHaveBeenCalledWith('/api/users/1/transactions?limit=8', expect.anything());
  });

  it('lets the user switch account types', async () => {
    await act(async () => { render(<MemoryRouter initialEntries={['/accounts']}><App /></MemoryRouter>); });
    expect(screen.getByText('Means of payment')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Business' }));
    expect(screen.getByText('13,968.53 EUR')).toBeTruthy();
  });

  it('reviews a transfer without claiming to send a payment', async () => {
    await act(async () => { render(<MemoryRouter initialEntries={['/transfer']}><App /></MemoryRouter>); });
    fireEvent.change(screen.getByLabelText(/reference/i), { target: { value: 'Test' } });
    fireEvent.click(screen.getByRole('button', { name: 'Calculate charges' }));
    expect(screen.getByRole('heading', { name: 'ACOMPANY' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Sign' }));
    expect(screen.getByRole('status').textContent).toContain('no payment was sent');
  });

  it('has one desktop navigation link per destination and a working sidebar toggle', async () => {
    await act(async () => { render(<MemoryRouter><App /></MemoryRouter>); });
    expect(screen.getAllByRole('link', { name: 'Business settings' })).toHaveLength(1);
    const toggle = screen.getByRole('button', { name: 'Collapse sidebar' });
    fireEvent.click(toggle);
    expect(screen.getByRole('button', { name: 'Expand sidebar' }).getAttribute('aria-expanded')).toBe('false');
  });

  it('switches between the two API-backed demo users', async () => {
    await act(async () => { render(<MemoryRouter initialEntries={['/user-settings']}><App /></MemoryRouter>); });
    const userTwo = await screen.findByRole('button', { name: /User 2 · Maria/ });
    await act(async () => { fireEvent.click(userTwo); });
    expect(userTwo.getAttribute('aria-pressed')).toBe('true');
    expect(localStorage.getItem('kbc-demo-user')).toBe('2');
    expect(mockFetch).toHaveBeenCalledWith('/api/users/2/transactions?limit=8', expect.anything());
    expect(mockFetch).toHaveBeenCalledWith('/api/users/2/insight', expect.anything());
  });

  it('lets a personal user inspect ML evidence and review transactions', async () => {
    await act(async () => { render(<MemoryRouter initialEntries={['/personal']}><App /></MemoryRouter>); });
    expect(await screen.findByText('Possible travel pattern')).toBeTruthy();
    const evidenceButton = screen.getByRole('button', { name: 'Show supporting signals' });
    expect(evidenceButton.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(evidenceButton);
    expect(screen.getByText('Travel spend is EUR 1,869.50')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Review transactions' }));
    expect(screen.getByRole('heading', { name: 'Transactions' })).toBeTruthy();
  });
});
