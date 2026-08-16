-- Family Finance Planner initial schema. Run in Supabase SQL editor or migration pipeline.
create extension if not exists pgcrypto;

create table public.settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  base_currency text not null default 'CZK' check (base_currency in ('CZK','EUR','USD')),
  payday smallint not null default 13 check (payday between 1 and 31),
  investment_ratio numeric(5,4) not null default 0.7000 check (investment_ratio between 0 and 1),
  exchange_rate_source text not null default 'manual',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table public.accounts (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null, institution text, account_type text not null check (account_type in ('main_current','current','savings','overdraft','broker')),
  currency text not null check (currency in ('CZK','EUR','USD')), is_active boolean not null default true,
  is_primary boolean not null default false, overdraft_limit numeric(14,2) not null default 0 check (overdraft_limit >= 0),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create unique index accounts_one_primary_per_user on public.accounts(user_id) where is_primary and is_active;
create index accounts_user_active_idx on public.accounts(user_id, is_active);

create or replace function public.clear_previous_primary_account()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.is_primary and new.is_active then
    update public.accounts set is_primary = false, updated_at = now()
    where user_id = new.user_id and id <> new.id and is_primary;
  end if;
  return new;
end;
$$;
create trigger accounts_clear_previous_primary
before insert or update of is_primary, is_active on public.accounts
for each row execute function public.clear_previous_primary_account();

create table public.balance_snapshots (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete restrict, snapshot_date date not null,
  balance numeric(14,2) not null, currency text not null check (currency in ('CZK','EUR','USD')),
  exchange_rate numeric(14,6) not null check (exchange_rate > 0), balance_czk numeric(14,2) not null,
  created_at timestamptz not null default now()
);
create index balance_snapshots_user_date_idx on public.balance_snapshots(user_id, snapshot_date desc);
create index balance_snapshots_account_date_idx on public.balance_snapshots(account_id, snapshot_date desc);

create table public.incomes (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete restrict, description text not null,
  amount numeric(14,2) not null check (amount > 0), currency text not null check (currency in ('CZK','EUR','USD')),
  due_date date not null, recurrence text not null check (recurrence in ('one_off','recurring')), is_active boolean not null default true,
  effective_from date not null, effective_to date, check (effective_to is null or effective_to >= effective_from),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index incomes_user_active_date_idx on public.incomes(user_id, is_active, due_date);
create index incomes_account_idx on public.incomes(account_id);

create table public.expenses (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete restrict, description text not null,
  amount numeric(14,2) not null check (amount > 0), currency text not null check (currency in ('CZK','EUR','USD')),
  due_date date not null, recurrence text not null check (recurrence in ('one_off','recurring')), is_reserve boolean not null default false,
  effective_from date not null, effective_to date, check (effective_to is null or effective_to >= effective_from),
  is_active boolean not null default true, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index expenses_user_active_date_idx on public.expenses(user_id, is_active, due_date);
create index expenses_account_idx on public.expenses(account_id);

create table public.transfers (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  source_account_id uuid not null references public.accounts(id) on delete restrict,
  target_account_id uuid not null references public.accounts(id) on delete restrict,
  amount numeric(14,2) not null check (amount > 0), target_amount numeric(14,2), currency text not null check (currency in ('CZK','EUR','USD')),
  exchange_rate numeric(14,6), transfer_date date not null, description text,
  created_at timestamptz not null default now(), check (source_account_id <> target_account_id), check (target_amount is null or target_amount > 0)
);
create index transfers_user_date_idx on public.transfers(user_id, transfer_date);
create index transfers_source_idx on public.transfers(source_account_id);
create index transfers_target_idx on public.transfers(target_account_id);

create table public.broker_snapshots (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete restrict, snapshot_date date not null,
  value numeric(14,2) not null, currency text not null check (currency in ('CZK','EUR','USD')),
  exchange_rate numeric(14,6) not null check (exchange_rate > 0), value_czk numeric(14,2) not null, created_at timestamptz not null default now()
);
create index broker_snapshots_user_date_idx on public.broker_snapshots(user_id, snapshot_date desc);
create index broker_snapshots_account_date_idx on public.broker_snapshots(account_id, snapshot_date desc);

create table public.exchange_rates (
  id uuid primary key default gen_random_uuid(), user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  rate_date date not null, currency text not null check (currency in ('CZK','EUR','USD')),
  rate_to_czk numeric(14,6) not null check (rate_to_czk > 0), source text not null, created_at timestamptz not null default now(),
  unique(user_id, rate_date, currency, source)
);
create index exchange_rates_user_date_idx on public.exchange_rates(user_id, rate_date desc);

-- RLS uses auth.uid() on every operation. Snapshot rows deliberately have no UPDATE policy: history is append-only.
alter table public.settings enable row level security;
alter table public.accounts enable row level security;
alter table public.balance_snapshots enable row level security;
alter table public.incomes enable row level security;
alter table public.expenses enable row level security;
alter table public.transfers enable row level security;
alter table public.broker_snapshots enable row level security;
alter table public.exchange_rates enable row level security;

create policy "own settings" on public.settings for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own accounts" on public.accounts for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own balance snapshots read" on public.balance_snapshots for select using (user_id = auth.uid());
create policy "own balance snapshots insert" on public.balance_snapshots for insert with check (
  user_id = auth.uid() and exists (select 1 from public.accounts a where a.id = account_id and a.user_id = auth.uid())
);
create policy "own balance snapshots delete" on public.balance_snapshots for delete using (user_id = auth.uid());
create policy "own incomes" on public.incomes for all using (user_id = auth.uid()) with check (
  user_id = auth.uid() and exists (select 1 from public.accounts a where a.id = account_id and a.user_id = auth.uid())
);
create policy "own expenses" on public.expenses for all using (user_id = auth.uid()) with check (
  user_id = auth.uid() and exists (select 1 from public.accounts a where a.id = account_id and a.user_id = auth.uid())
);
create policy "own transfers" on public.transfers for all using (user_id = auth.uid()) with check (
  user_id = auth.uid()
  and exists (select 1 from public.accounts a where a.id = source_account_id and a.user_id = auth.uid())
  and exists (select 1 from public.accounts a where a.id = target_account_id and a.user_id = auth.uid())
);
create policy "own broker snapshots read" on public.broker_snapshots for select using (user_id = auth.uid());
create policy "own broker snapshots insert" on public.broker_snapshots for insert with check (
  user_id = auth.uid() and exists (select 1 from public.accounts a where a.id = account_id and a.user_id = auth.uid() and a.account_type = 'broker')
);
create policy "own broker snapshots delete" on public.broker_snapshots for delete using (user_id = auth.uid());
create policy "own exchange rates" on public.exchange_rates for all using (user_id = auth.uid()) with check (user_id = auth.uid());
