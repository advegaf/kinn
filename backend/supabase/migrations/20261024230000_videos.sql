-- Story videos and heard receipts. Matches docs/CONTRACT.md.

alter table public.messages add column if not exists heard_at timestamptz;

insert into storage.buckets (id, name, public)
values ('videos', 'videos', true)
on conflict (id) do nothing;

create policy "demo read videos" on storage.objects for select to anon, authenticated
  using (bucket_id = 'videos');
create policy "demo insert videos" on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'videos');
create policy "demo update videos" on storage.objects for update to anon, authenticated
  using (bucket_id = 'videos') with check (bucket_id = 'videos');
create policy "demo delete videos" on storage.objects for delete to anon, authenticated
  using (bucket_id = 'videos');
