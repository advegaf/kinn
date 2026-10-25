-- Presenter mode. Demo threads skip the LLM and map recordings onto the canned stories in
-- functions/_shared/demo-stories.json. reply_to links a family reply to the elder message it answers.

alter table public.threads add column if not exists demo boolean not null default false;

alter table public.messages add column if not exists reply_to uuid references public.messages(id) on delete set null;
