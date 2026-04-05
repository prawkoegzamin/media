

Project aiming to provide reencoded / size optimized media from https://www.gov.pl/pliki/mi/multimedia_do_pytan.zip. 

🔵 HIGH

Goal: good quality, still compressed

Video
Codec: H.264 (standard, widely compatible)
Quality: CRF 20 → visually close to original
Encoder speed: slow → better compression efficiency
Resolution: 1280px width (~720p), height auto
FPS: unchanged (unless thumbs)
Audio
AAC 128 kbps → decent quality

👉 Result:
Looks clean, small-ish files, good for normal viewing or archiving.

🟡 MEDIUM

Goal: balance size vs quality

Video
CRF 23 → noticeable compression but still fine
Preset: medium
Resolution: 854px width (~480p)
Audio
AAC 96 kbps

👉 Result:
Good enough for casual watching. Smaller files. Slight blur/artifacts.

🔴 LOW

Goal: aggressive compression

Video
CRF 28 → quite lossy
Preset: fast (less efficient compression)
Resolution: 640px width (~360p)
Audio
AAC 64 kbps

👉 Result:
Small files, but visibly degraded (blurry, blocky).
Useful for previews, low bandwidth, or storage saving.

🟣 THUMBS

Goal: tiny preview videos

Video
CRF 23
No audio (-an)
Height: fixed (default 80px)
Width: auto (keeps aspect ratio)
FPS: forced to 23
Images
Resized to height = 80px

👉 Result:
Very small animated previews. Think:

gallery hover previews
UI thumbnails
not for real watching
