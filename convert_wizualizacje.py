#!/usr/bin/env python3
import argparse
import json
from fractions import Fraction
from pathlib import Path
import subprocess
import multiprocessing
import shutil
import sys

# ==============================
#   DEBUG / DOT PRINTER
# ==============================

DEBUG = False
_dcounter = 0

doVideos = True #False
doImages = True #False

def dprint(msg=""):
    """
    If debug is ON -> normal print.
    If debug is OFF -> print a dot every 16 calls to show script is alive.
    """
    global DEBUG, _dcounter

    if DEBUG:
        print(msg)
    else:
        _dcounter += 1
        if _dcounter % 8 == 0:
            print(".", end="", flush=True)


# ==============================
#       PROCESSING LOGIC
# ==============================

def get_video_info(path):
    proc = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            str(path)
        ],
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        return None

    try:
        data = json.loads(proc.stdout)
        s = data["streams"][0]

        w = int(s["width"])
        h = int(s["height"])

        # r_frame_rate is e.g.: "30000/1001"
        fps_raw = s.get("r_frame_rate", "0/0")
        fps = float(Fraction(fps_raw)) if fps_raw != "0/0" else None

        return w, h, fps
    except Exception:
        return None

def run_cmd(cmd, cwd=None):
    """Silent ffmpeg/imagemagick wrapper with dprint."""
    dprint(f"cmd: {' '.join(cmd)}")
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cwd)


def process_preset(src_dir: Path, preset: str, target: str, max_threads: int, thumb_height: int):

    dst = src_dir.parent / f"{target}-{preset}"
    dst.mkdir(parents=True, exist_ok=True)

    print(f"\n== PRESET {preset} ({src_dir} → {dst}) ==")

    # Counters
    processed_videos = 0
    processed_images = 0

    # ==============================
    #         PRESET OPTIONS
    # ==============================
    target_fps = 23

    if preset == "high":
        vopts = ["-c:v", "libx264", "-crf", "20", "-preset", "slow"]
        aopts = ["-c:a", "aac", "-b:a", "128k"]
        img_width = 1280
        img_height = -2
        video_scale = ["-vf", f"scale={img_width}:{img_height}"]

    elif preset == "medium":
        vopts = ["-c:v", "libx264", "-crf", "23", "-preset", "medium"]
        aopts = ["-c:a", "aac", "-b:a", "96k"]
        img_width = 854
        img_height = -2
        video_scale = ["-vf", f"scale={img_width}:{img_height}"]

    elif preset == "low":
        vopts = ["-c:v", "libx264", "-crf", "28", "-preset", "fast"]
        aopts = ["-c:a", "aac", "-b:a", "64k"]
        img_width = 640
        img_height = -2
        video_scale = ["-vf", f"scale={img_width}:{img_height}"]

    elif preset == "thumbs":
        vopts = ["-c:v", "libx264", "-crf", "23", "-preset", "fast", "-an"]
        aopts = []
        img_width = -2
        target_fps = 23
        # In ffmpeg:
        #   -1 = auto - calculate
        #   while preserving aspect ratio (but can produce odd numbers)
        #   -2 = auto - calculate
        #   while preserving aspect ratio and round to the nearest even number, which video codecs require (especially H.264 / WebP).

        img_height = thumb_height
        video_scale = ["-vf", f"scale={img_width}:{img_height}"
                              f",fps={target_fps}"
                       ]

    elif preset == "thumbs_webp":
        vopts = [
            "-vcodec", "libwebp", "-lossless", "0", "-q:v", "75", "-preset", "default", "-an"
        ]
        aopts = []
        img_width = -2
        img_height = thumb_height
        target_fps = 23
        video_scale = ["-vf", f"scale={img_width}:{img_height}"
                              f",fps={target_fps}"
                       ]

    else:
        print(f"Unknown preset: {preset}")
        sys.exit(1)

    is_thumbs_preset = preset in ["thumbs", "thumbs_webp"]
    # ==============================
    #          VIDEO PROCESSING
    # ==============================

    if doVideos:
        for file in src_dir.glob("*.wmv"):

            final_video_file = dst / file.name

            if preset == "thumbs_webp":
                final_video_file = final_video_file.with_name(final_video_file.name + ".webp")

            if is_thumbs_preset:
                final_video_file = final_video_file.with_name(final_video_file.name + ".thumb")

            if final_video_file.exists():
                info = get_video_info(final_video_file)

                if info is None:
                    need_resize = True
                else:
                    w, h, fps = info

                    # resolution check
                    if is_thumbs_preset:
                        need_resize = (h != img_height)
                    else:
                        need_resize = (w != img_width)

                    if is_thumbs_preset:
                        if fps is None or fps != target_fps:
                            need_resize = True

                    #print(f"DBG: need_resize: {need_resize} : {fps} {target_fps} , {w} {img_width} ,{h} {img_height}")

                if not need_resize:
                    dprint(f"Not needing resize VIDEO: {file} -> {final_video_file}")
                    continue

            # Temporary output before renaming
            if preset == "thumbs_webp":
                out_file = dst / f"{file.name}.webp"
            else:
                out_file = dst / file.with_suffix(".mkv").name

            cmd = ["ffmpeg", "-y", "-i", str(file), *vopts, *video_scale, *aopts, str(out_file), "-threads",
                   str(max_threads)]

            dprint(f"processing video {file} -> {final_video_file}")

            # Run command and check for success
            try:
                run_cmd(cmd)
                out_file.rename(final_video_file)
                processed_videos += 1
            except Exception as e:
                print(f"Failed processing {file}: {e}")

    # ==============================
    #       IMAGE COPYING / WEBP
    # ==============================

    if doImages:
        img_files = [f for f in src_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg")]

        for img in img_files:

            dst_img_file = dst / img.name

            if preset == "thumbs_webp":
                dst_img_file = dst_img_file.with_name(dst_img_file.name + ".webp")

            final_img_file = dst_img_file

            if is_thumbs_preset:
                final_img_file = final_img_file.with_name(final_img_file.name + ".thumb")

            if final_img_file.exists():
                proc = subprocess.run(
                    ["identify", "-format", "%w %h", str(final_img_file)],
                    capture_output=True,
                    text=True
                )
                if proc.returncode != 0:
                    need_resize = True
                else:
                    w, h = map(int, proc.stdout.split())
                    if is_thumbs_preset:
                        need_resize = (h != img_height)
                    else:
                        need_resize = (w != img_width)

                if not need_resize:
                    dprint(f"Not needing resize: {img} -> {final_img_file}")
                    continue


            dprint(f"processing image {img} -> {final_img_file}")
            #subprocess.run(["magick", str(img), "-resize", f"x{thumb_height}", str(out_img)])

            if preset in ["thumbs", "thumbs_webp"]:
                resize_value = f"x{img_height}"
            else:
                resize_value = f"{img_width}x"

            subprocess.run([
                "magick", str(img),
                "-resize", resize_value,
                "-quality", "95",
                "-define", "jpeg:optimize-coding=true",
                "-define", "jpeg:trellis-quantization=true",
                "-define", "jpeg:dct-method=float",
                "-define", "jpeg:quant-table=1",
                "-sampling-factor", "4:2:0",
                "-interlace",
                "plane",
                str(dst_img_file)
            ])

            dst_img_file.rename(final_img_file)

            processed_images += 1


    # ==============================
    #           ZIP CREATION
    # ==============================

    output_dir = Path("multimedia")
    output_dir.mkdir(exist_ok=True)
    zip_file = output_dir / f"{target}-{preset}.zip"

    if zip_file.exists():
        zip_file.unlink()

    run_cmd([
        "zip", "-r", "-0",
        str(zip_file),
        str(dst.name)
    ], cwd=str(dst.parent))

    print(f"\n== DONE {preset}: videos={processed_videos} images={processed_images} "
          f" zip={zip_file.name} ==")

    return {
        "videos": processed_videos,
        "images": processed_images,
        "zip": zip_file.name
    }


# ==============================
#              MAIN
# ==============================

def main():
    global DEBUG

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", required=True)
    parser.add_argument("-p", "--preset", default="all")
    parser.add_argument("--max-threads", type=int, default=int(multiprocessing.cpu_count() * 0.8))
    parser.add_argument("--thumb-height", type=int, default=80)
    parser.add_argument("-t", "--target")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    # if target not provided, use source folder name
    if not args.target:
        args.target = Path(args.source).name

    DEBUG = args.verbose

    presets_to_run = (
        ["high", "medium", "low", "thumbs", "thumbs_webp"]
        if args.preset == "all"
        else [args.preset]
    )

    src_dir = Path(args.source)

    proc_results = {}
    for p in presets_to_run:
        proc_results[p] = process_preset(src_dir, p, args.target, args.max_threads, args.thumb_height)

    print("\n== ALL PRESETS DONE ==")
    for preset, stats in proc_results.items():
        print(f"{preset:<14} videos={stats['videos']} images={stats['images']} zip={stats['zip']}")

if __name__ == "__main__":
    main()
