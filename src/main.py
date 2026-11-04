import argparse

from config import get_output_dir, set_output_dir
from transcript import get_video_id, get_title, get_transcript
from save import save_md, save_transcript


def run(url):
    """Link in, note out."""
    # imported here so --show-output / --set-output work without an API key
    from summery import summarize

    title = get_title(url) or get_video_id(url)
    print(f"Working on: {title}")

    tran = get_transcript(url)
    if not tran:
        raise SystemExit("Couldn't get a transcript for this video.")

    try:
        summar, tags = summarize(tran)
        path = save_md(title, url, summar, tags=tags)
        print(f"Saved to {path}")

    except SystemExit:
        path = save_transcript(title, url, tran)
        print(f"Summary failed. Transcript saved to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Summarize YouTube videos into Markdown notes."
    )
    parser.add_argument("url", nargs="?", help="YouTube link to summarize")
    parser.add_argument(
        "--set-output", metavar="FOLDER", help="change where notes are saved"
    )
    parser.add_argument(
        "--show-output", action="store_true", help="show the current save folder"
    )
    args = parser.parse_args()

    if args.set_output:
        print(f"Save location set to: {set_output_dir(args.set_output)}")
    elif args.show_output:
        print(f"Notes are saved to: {get_output_dir()}")
    elif args.url:
        run(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
