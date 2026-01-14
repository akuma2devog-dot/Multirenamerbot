import subprocess

def add_thumbnail(video, thumb, output):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video,
        "-i", thumb,
        "-map", "0",
        "-map", "1",
        "-c", "copy",
        "-disposition:v:1", "attached_pic",
        output
    ])
