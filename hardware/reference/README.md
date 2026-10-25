# Reference: Dream Recorder case

`dream-recorder_front.stl` and `dream-recorder_back.stl` are the case of Modem's Dream Recorder, copied unchanged from
https://github.com/modem-works/dream-recorder/tree/main/3DAssets. The Dream Recorder is by Modem (modem.works) and is released under the MIT license. Credit for the form language (soft pillow shell, raised hump, 19 dot speaker grid, pill slots, round touch button) goes to them. The Hearth v4 case borrows that language; none of their geometry is in our STLs.

We use these files only to render the two side by side (`render/hearth_scene_v4.py -- vs-dr`) and to check proportions.

## Frame of the files (mm)

- Both parts share one frame: x about -5 to 225 along the length (229 long), y about 61 to 158 (about 97 tall), z toward the back.
- Front: z 0 to 14.5. The outer face is at z = 0 and is solid: their screen glows through thin PLA, there is no window. The tray rim tops out at z = 10.66 and the clip lugs reach 14.5.
- Back: z 0 to 50.6, open face at z = 0, hump on top. Assembled, the back's open face sits on the front's rim, so add 10.66 to its z.
- Reference renders of each part from several sides are in `render/dr-reference-*.png`.
