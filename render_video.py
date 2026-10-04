#!/usr/bin/env python3
"""
Render 3-minute nursery rhyme video from generated assets.
Uses MoviePy for: Ken Burns pan/zoom, lyric karaoke sync, transitions, text overlays.
"""

import json
import os
from pathlib import Path
from moviepy.editor import (
    ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, VideoFileClip
)
from moviepy.video.fx.all import resize, crop
import numpy as np

# ─── CONFIG ───
WIDTH, HEIGHT = 1920, 1080
FPS = 30
OUTPUT_PATH = "output/video.mp4"
ASSETS_DIR = Path("assets")

# ─── LOAD DATA ───
with open(ASSETS_DIR / "script.json") as f:
    script = json.load(f)

with open(ASSETS_DIR / "timing.json") as f:
    timing = json.load(f)

scenes = script["scenes"]
audio_path = ASSETS_DIR / "audio" / "voiceover.wav"
images_dir = ASSETS_DIR / "images"
music_dir = ASSETS_DIR / "music"

# ─── HELPERS ───
def ken_burns_clip(image_path, duration, zoom_factor=1.15, direction="in"):
    """Apply slow Ken Burns pan/zoom to static image."""
    clip = ImageClip(str(image_path)).set_duration(duration).set_fps(FPS)
    
    # Resize to cover 1920x1080 maintaining aspect
    img_w, img_h = clip.size
    scale = max(WIDTH / img_w, HEIGHT / img_h) * zoom_factor
    new_w, new_h = int(img_w * scale), int(img_h * scale)
    clip = clip.resize((new_w, new_h))
    
    # Calculate crop movement
    max_x = new_w - WIDTH
    max_y = new_h - HEIGHT
    
    def get_frame(t):
        progress = t / duration
        if direction == "in":
            x = int(max_x * progress * 0.3)
            y = int(max_y * progress * 0.3)
        elif direction == "out":
            x = int(max_x * (1 - progress) * 0.3)
            y = int(max_y * (1 - progress) * 0.3)
        elif direction == "left":
            x = int(max_x * progress * 0.5)
            y = int(max_y * 0.1)
        elif direction == "right":
            x = int(max_x * (1 - progress) * 0.5)
            y = int(max_y * 0.1)
        else:
            x, y = int(max_x * 0.1), int(max_y * 0.1)
        return clip.get_frame(t)[y:y+HEIGHT, x:x+WIDTH]
    
    return clip.fl(get_frame, apply_to=["mask"]).set_duration(duration)

def create_lyric_text(text, start_time, duration, scene_duration):
    """Create karaoke-style highlighted lyric text."""
    # Main lyric text (center bottom)
    txt = TextClip(
        text,
        fontsize=60,
        color='white',
        font='DejaVu-Sans-Bold',
        stroke_color='black',
        stroke_width=3,
        method='caption',
        size=(WIDTH * 0.9, None),
        align='center'
    ).set_duration(scene_duration).set_start(start_time).set_position(('center', HEIGHT - 180))
    
    # Highlight effect: could animate word-by-word with more complex timing
    return txt

def create_scene_number(text, start_time, duration):
    """Small scene indicator (optional)."""
    return TextClip(
        text,
        fontsize=36,
        color='white',
        font='DejaVu-Sans',
        stroke_color='black',
        stroke_width=2
    ).set_duration(duration).set_start(start_time).set_position((50, 50))

# ─── BUILD SCENES ───
print("Building video scenes...")
scene_clips = []
current_time = 0

directions = ["in", "out", "left", "right", "in", "out", "left", "right", "in", "out", "left", "right", "in", "out", "in"]

for i, scene in enumerate(scenes):
    scene_id = scene["id"]
    duration = scene["duration"]
    img_path = images_dir / f"scene_{scene_id:03d}.png"
    
    if not img_path.exists():
        print(f"  ⚠ Missing image for scene {scene_id}, using black")
        bg = ColorClip((WIDTH, HEIGHT), color=(20, 20, 40)).set_duration(duration)
    else:
        direction = directions[i % len(directions)]
        bg = ken_burns_clip(img_path, duration, direction=direction)
    
    # Lyric overlay
    if scene.get("lyrics"):
        lyric_clip = create_lyric_text(
            scene["lyrics"], current_time, duration, duration
        )
        scene_composite = CompositeVideoClip([bg, lyric_clip], size=(WIDTH, HEIGHT))
    else:
        scene_composite = bg
    
    # Scene number (debug)
    # num_clip = create_scene_number(f"Scene {scene_id}", current_time, duration)
    # scene_composite = CompositeVideoClip([scene_composite, num_clip], size=(WIDTH, HEIGHT))
    
    scene_clips.append(scene_composite.set_start(current_time))
    current_time += duration
    print(f"  Scene {scene_id}: {duration}s @ {current_time - duration:.1f}s")

# ─── CONCATENATE WITH CROSSFADE ───
print("Concatenating scenes with crossfades...")
final_clips = []
for i, clip in enumerate(scene_clips):
    if i > 0:
        clip = clip.crossfadein(0.5)
    final_clips.append(clip)

video = CompositeVideoClip(final_clips, size=(WIDTH, HEIGHT)).set_duration(current_time)

# ─── ADD AUDIO ───
print("Adding voiceover audio...")
voiceover = AudioFileClip(str(audio_path))
video = video.set_audio(voiceover)

# ─── BACKGROUND MUSIC (optional) ───
music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
if music_files:
    print(f"Adding background music: {music_files[0]}")
    bg_music = AudioFileClip(str(music_files[0])).volumex(0.15)  # Low volume
    # Loop music to match video duration
    if bg_music.duration < video.duration:
        loops = int(video.duration / bg_music.duration) + 1
        bg_music = concatenate_audioclips([bg_music] * loops)
    bg_music = bg_music.subclip(0, video.duration)
    video = video.set_audio(CompositeAudioClip([voiceover, bg_music]))

# ─── RENDER ───
print(f"Rendering to {OUTPUT_PATH} ({current_time:.1f}s, {WIDTH}x{HEIGHT} @ {FPS}fps)...")
os.makedirs("output", exist_ok=True)

video.write_videofile(
    OUTPUT_PATH,
    fps=FPS,
    codec='libx264',
    audio_codec='aac',
    bitrate='8000k',
    threads=4,
    preset='medium',
    ffmpeg_params=['-movflags', '+faststart']
)

print("✅ Render complete!")
print(f"   Output: {OUTPUT_PATH}")
print(f"   Duration: {current_time:.1f}s")
print(f"   Size: {os.path.getsize(OUTPUT_PATH) / 1024 / 1024:.1f} MB")