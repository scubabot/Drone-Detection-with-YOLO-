"""
video_to_frames.py
------------------
Extracts frames from a video file and saves them as .jpg images.
Frames are saved to an output folder, one image per second by default.

Usage:
    python3 video_to_frames.py --input ~/Videos/my_video.webm
    python3 video_to_frames.py --input ~/Videos/my_video.webm --output ~/my_frames --fps 2
"""

import argparse
import os
import subprocess
import sys


def extract_frames(input_path: str, output_dir: str, fps: int):
    """
    Extract frames from a video file using ffmpeg.

    Args:
        input_path: Path to the input video file.
        output_dir: Folder to save the extracted frames.
        fps:        How many frames to extract per second of video.
    """
    # Expand ~ to full home path
    input_path = os.path.expanduser(input_path)
    output_dir = os.path.expanduser(output_dir)

    # Check the input file exists
    if not os.path.isfile(input_path):
        print(f"[ERROR] Video file not found: {input_path}")
        sys.exit(1)

    # Create output folder if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    print(f"[INFO] Input video : {input_path}")
    print(f"[INFO] Output folder: {output_dir}")
    print(f"[INFO] Frames per second: {fps}")
    print(f"[INFO] Starting extraction...\n")

    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"fps={fps}",
        output_pattern
    ]

    result = subprocess.run(command)

    if result.returncode != 0:
        print("\n[ERROR] ffmpeg failed. Make sure ffmpeg is installed:")
        print("        sudo apt install ffmpeg")
        sys.exit(1)

    # Count saved frames
    saved = [f for f in os.listdir(output_dir) if f.endswith(".jpg")]
    print(f"\n[DONE] {len(saved)} frames saved to: {output_dir}")
    print("       Ready to upload to Roboflow for labeling.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from a video file for drone detection labeling."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the input video file (e.g. ~/Videos/flight.webm)"
    )
    parser.add_argument(
        "--output", "-o",
        default="~/drone_video_frames",
        help="Folder to save extracted frames (default: ~/drone_video_frames)"
    )
    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=1,
        help="Frames to extract per second of video (default: 1)"
    )

    args = parser.parse_args()
    extract_frames(args.input, args.output, args.fps)


if __name__ == "__main__":
    main()
