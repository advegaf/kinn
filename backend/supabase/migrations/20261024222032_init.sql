-- Mother Tongue schema. Matches docs/CONTRACT.md. Hackathon mode: permissive RLS, no auth.

create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  role text not null check (role in ('elder','family')),
  lang text not null,
  voice_id text,
  created_at timestamptz default now()
);

create table if not exists public.threads (
  id uuid primary key default gen_random_uuid(),
  elder_id uuid references public.profiles(id),
  family_id uuid references public.profiles(id),
  created_at timestamptz default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references public.threads(id) not null,
  sender_id uuid references public.profiles(id) not null,
  source_lang text not null,
  target_lang text not null,
  original_path text not null,
  transcript text,
  translation text,
  translated_path text,
  cultural_notes jsonb default '[]',
  ask_about jsonb default '[]',
  story jsonb,
  status text not null default 'uploaded' check (status in ('uploaded','processing','ready','error')),
  error text,
  created_at timestamptz default now()
);

create index if not exists messages_thread_created_idx on public.messages (thread_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.threads enable row level security;
alter table public.messages enable row level security;

create policy "demo all profiles" on public.profiles for all to anon, authenticated using (true) with check (true);
create policy "demo all threads" on public.threads for all to anon, authenticated using (true) with check (true);
create policy "demo all messages" on public.messages for all to anon, authenticated using (true) with check (true);

grant all on public.profiles, public.threads, public.messages to anon, authenticated;

-- Realtime. Full replica identity so UPDATE events carry the whole row.
alter table public.messages replica identity full;
alter publication supabase_realtime add table public.messages;

-- Storage
insert into storage.buckets (id, name, public)
values ('audio', 'audio', true), ('images', 'images', true)
on conflict (id) do nothing;

create policy "demo read media" on storage.objects for select to anon, authenticated
  using (bucket_id in ('audio','images'));
create policy "demo insert media" on storage.objects for insert to anon, authenticated
  with check (bucket_id in ('audio','images'));
create policy "demo update media" on storage.objects for update to anon, authenticated
  using (bucket_id in ('audio','images')) with check (bucket_id in ('audio','images'));
create policy "demo delete media" on storage.objects for delete to anon, authenticated
  using (bucket_id in ('audio','images'));
