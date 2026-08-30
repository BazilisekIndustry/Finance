-- New expense characteristic: fixed is the legacy/default behaviour.
alter table public.expenses
  add column if not exists expense_kind text not null default 'fixed'
  check (expense_kind in ('fixed', 'continuous'));

-- Snapshots remain append-only in normal use, but correcting an entered actual
-- balance and deleting an accidental snapshot are explicitly supported.
create policy "own balance snapshots update" on public.balance_snapshots
  for update using (user_id = auth.uid()) with check (
    user_id = auth.uid() and exists (
      select 1 from public.accounts a where a.id = account_id and a.user_id = auth.uid()
    )
  );
