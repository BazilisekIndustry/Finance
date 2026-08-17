-- Store the bank-facing available overdraft value alongside the generic snapshot balance.
alter table public.balance_snapshots
  add column if not exists overdraft_available numeric(14,2);

-- Releases before this migration stored the drawn amount in `balance`. Convert
-- those historical snapshots using the account limit, then keep `balance` as the
-- common prediction value (the available amount) for backward-compatible reads.
update public.balance_snapshots snapshot
set overdraft_available = greatest(0, account.overdraft_limit - snapshot.balance),
    balance = greatest(0, account.overdraft_limit - snapshot.balance)
from public.accounts account
where snapshot.account_id = account.id
  and account.account_type = 'overdraft'
  and snapshot.overdraft_available is null;

comment on column public.balance_snapshots.overdraft_available is
  'Available overdraft shown by the bank. Used amount is accounts.overdraft_limit - overdraft_available.';
