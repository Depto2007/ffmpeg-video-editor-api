from fastapi import FastAPI, Request
import tempfile, base64, os, requests, subprocess
from typing import Dict

app = FastAPI()

# Helper function to download image
def download_image(url):
    response = requests.get(url)
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    with open(path, "wb") as f:
        f.write(response.content)
    return path

# Helper function to generate video using FFmpeg
def generate_video(scenes: Dict[str, Dict], audio_path: str) -> str:
    input_args = []
    filter_complex = ""
    duration_total = 0
    image_paths = []

    for i, (key, scene) in enumerate(scenes.items()):
        img_path = download_image(scene["imageURL"])
        duration = int(scene["duration"])
        image_paths.append(img_path)
        input_args.extend(["-loop", "1", "-t", str(duration), "-i", img_path])
        duration_total += duration

    input_args.extend(["-i", audio_path])

    filter_inputs = ''.join([f"[{i}:v]" for i in range(len(scenes))])
    filter_complex = f"{filter_inputs}concat=n={len(scenes)}:v=1:a=0[outv]"

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    cmd = [
        "ffmpeg",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", f"{len(scenes)}:a",
        "-y", output_path
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

@app.post("/generate-video")
async def generate_video_api(req: Request):
    data = await req.json()
    audio_binary = data['audioFile']
    scenes = data['imageFiles']

    # Save audio to temp file
    audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    with open(audio_path, "wb") as f:
        f.write(base64.b64decode(audio_binary))

    # Generate video
    output_path = generate_video(scenes, audio_path)

    # Upload to file.io
    with open(output_path, 'rb') as file:
        response = requests.post("https://file.io", files={"file": file})
        result = response.json()

    return {"video_url": result.get("link")}
