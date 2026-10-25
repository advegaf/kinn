# Live demo script

Two presenters. Angel holds the iPhone (Kinn app, in English). He is himself:
he does not speak Spanish, and neither does the rest of the team. A teammate
plays his grandmother Margaret at the tablet (the Hearth) and reads her lines
in Spanish from this script. The whole run takes about three minutes.

Margaret never types anything. There is no keyboard on the Hearth and nothing
to set up on her side.

## Setup

Tablet. Point the kiosk at the live thread:

```sh
cd fire-kiosk
scripts/setup-device.sh "https://mothertongue-hearth.netlify.app/?thread=b849ad40-4610-453b-9126-0447921bd915&profile=cad0551e-96bc-4545-a2e1-1647674caa97&subs=en"
```

`subs=en` puts English under the Spanish so judges can follow.

Phone. Open Settings in the app and turn demo mode off. The Hearth shows the
family code `B849AD` on its clock screen. Angel reads it off the tablet and
types it on his phone. That is the whole pairing. Margaret does nothing.

Check before judges arrive: the tablet shows the clock, the phone shows the
week, and both are on the venue wifi.

## Reset between rehearsals

1. Reseed the demo stories:

   ```sh
   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... deno run -A backend/scripts/seed-demo.ts
   ```

2. Delete the live messages from the last run. They are the rows in
   `messages` whose `original_path` starts with the thread id. Delete the
   replies (rows with `reply_to` set) first, then the rest. In the Supabase SQL
   editor:

   ```sql
   delete from messages
   where original_path like 'b849ad40-4610-453b-9126-0447921bd915%'
     and reply_to is not null;

   delete from messages
   where original_path like 'b849ad40-4610-453b-9126-0447921bd915%';
   ```

   Seeded rows use `demo/` paths, so they stay.

3. Reload the tablet and force quit and reopen the app on the phone.

## The run

### 1. The clock (0:00 to 0:15)

The tablet shows the clock, Spanish with English under it.

Say: "This is the Hearth. It sits in my grandma Margaret's kitchen in
Monterrey. It has no buttons and she never types anything. The code on the
clock is how I paired my phone to it."

### 2. Margaret talks (0:15 to 0:50)

Margaret presses and holds the screen for 3 seconds while a ring fills. It says "te escucho / I'm listening".

Margaret reads, word for word:

> Mi mamá nos despertaba a las cinco cada Navidad, sin falta. Todavía estaba
> oscuro y la cocina olía a leña. Prendía el foco amarillo de la mesa y nos
> decía: ándale, que la masa no espera. Desde la noche antes dejaba todo listo.

Say (while she talks, quietly, or right after): "She holds once and tells a
story, the way she would to someone at the table."

### 3. Saved (0:50 to 1:00)

Margaret taps to stop. The tablet says "tu historia está guardada / your story is
saved".

Say: "That's all she has to do. Her words are already on the way to Austin."

### 4. Angel hears it (1:00 to 1:45)

Angel's phone shows "Mama's tamales" in English with its five scenes. He taps
play. The narration is in English and the scenes change with the words.

Say: "I don't speak Spanish. None of us on this team do. I just heard my
grandmother's story in English, in her voice."

### 5. Angel writes back (1:45 to 2:20)

Angel taps Write back, taps the disc and reads, word for word:

> Abuela, I listened twice. I didn't know you and Tía Lupe made the tamales
> sitting on the floor. Will you teach me this Christmas, at five in the
> morning? What song was she singing?

He taps the disc to stop, then taps Send.

Say: "The questions on this screen come from what she just said. I tap and
talk, in English."

### 6. Margaret hears it (2:20 to 3:00)

The tablet glows "Angel te escribió / Angel wrote to you". Margaret taps it and
hears the message in Spanish. The scenes match each question (her mother
singing, the kitchen at dawn), with English subtitles under the Spanish.

Say: "She hears me in Spanish, in my voice. I can't say a sentence of that
myself. Without the AI in the middle, we can't have this conversation."

## If the network fails

Switch both devices to demo mode and run the same click order.

- Tablet: load the same URL with `?demo=1`, for example
  `https://mothertongue-hearth.netlify.app/?demo=1&subs=en`.
- Phone: Settings, turn demo mode on.

Demo mode plays the seeded story and reply without the backend. Keep the same
beats and lines.

## A note on what runs live

Speech to text runs live through ElevenLabs Scribe. Translation and the cloned
voice are canned in presenter mode for now. They go live once we have an LLM
key and the ElevenLabs paid tier, which voice cloning needs. If a judge asks,
say: "Speech to text is live. Translation and the voice are canned today until
we have the API keys."
