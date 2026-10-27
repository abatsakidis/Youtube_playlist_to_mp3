
import os
from yt_dlp import YoutubeDL


def download_playlist():
    playlist_url = input("Δώσε το URL της YouTube playlist: ").strip()

    if not playlist_url:
        print("Δεν έδωσες URL.")
        return

    output_folder = "MP3_Downloads"
    os.makedirs(output_folder, exist_ok=True)

    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(
            output_folder,
            "%(playlist_index)03d - %(title)s.%(ext)s"
        ),
        "noplaylist": False,
        "ignoreerrors": True,
        "windowsfilenames": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "download_archive": os.path.join(
            output_folder, "downloaded.txt"
        ),
        "retries": 3,
        "quiet": False,
    }

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([playlist_url])

        print(f"\nΗ διαδικασία ολοκληρώθηκε!")
        print(f"Τα αρχεία βρίσκονται στον φάκελο: {output_folder}")

    except Exception as error:
        print(f"Παρουσιάστηκε σφάλμα: {error}")


if __name__ == "__main__":
    download_playlist()
