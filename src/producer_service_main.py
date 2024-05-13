import argparse
import sys
import os
import ffmpeg


def dump_images(args) -> None:
    # equivalent to: ffmpeg -i data/traffic.mp4 -vf fps=15 out/traffic%04d.png
    # 
    basename = os.path.basename(args.video_file)
    basename = os.path.splitext(basename)[0]

    # with ffmpeg, the decoding can be accelerate by HW by adding options, 
    # such as "-hwaccel cuda  -hwaccel_output_format cuda".
    try:
        (
            ffmpeg
            .input(args.video_file)
            .filter('fps', '15')
            .output(f'{args.log_folder}/{basename}%04d.png')
            .run()
        )
    except ffmpeg.Error as e:
        print(e.stderr.decode(), file=sys.stderr)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_file", type=str, required=True)
    parser.add_argument("--log_folder", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dump_images(args)


if __name__ == "__main__":
    main()
