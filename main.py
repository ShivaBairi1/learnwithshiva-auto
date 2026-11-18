import os, json, re, subprocess, textwrap, datetime, pathlib, random, hashlib, sys
import requests
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "output"
WORK = ROOT / "work"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

GEMINI_MODEL = "gemini-2.5-flash"
# Start with private for the first test. Change to "public" after checking outputs.
PRIVACY_STATUS = "private"
CATEGORY_ID = "27"  # Education
LANGUAGE = "en"

def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required GitHub Actions secret: {name}")
    return value

def gemini(prompt):
    key = require_env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "responseMimeType": "application/json"}
    }
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:1200]}")
    data = r.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        # Remove accidental markdown fences if the model returns them.
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
        return json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Could not parse Gemini JSON: {e}; response={str(data)[:1000]}")

def make_episode(kind):
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    duration = "a 40–55 second YouTube Short" if kind == "short" else "a 2–4 minute horizontal YouTube explainer"
    count = "4" if kind == "short" else "7"
    prompt = f"""
Create a fresh, accurate, original educational episode for the LearnWithShiva YouTube channel.
Today's date: {date}. Format: {duration}. Choose a surprising but verifiable educational topic
from science, history, geography, technology, nature, or everyday reasoning. Avoid politics,
medical advice, financial advice, sensational claims, celebrity gossip, and topics already
commonly covered in generic fact channels. Explain one useful idea with a concrete example.
Do not invent statistics, quotes, studies, or dates. If uncertain, choose a simpler well-known fact.
Use clear natural English for Indian and international viewers.

Return ONLY valid JSON with this exact structure:
{{
 "title": "compelling accurate YouTube title, no misleading clickbait",
 "description": "2-4 sentence original description, then a short learning takeaway and 3-4 relevant hashtags",
 "tags": ["tag1","tag2","tag3","tag4","tag5"],
 "thumbnail_text": "2-5 short words",
 "segments": [
   {{"heading":"short on-screen heading","narration":"spoken narration, conversational, self-contained","visual_hint":"a simple diagram or illustration idea"}}
 ]
}}
Include exactly {count} segments. Each segment narration should be about {"20-30" if kind=="long" else "12-20"} words.
Ensure the whole episode has a beginning, clear explanation, example, and memorable takeaway.
The visuals will be created from original geometric illustrations and text, so visual_hint should
describe simple shapes, comparisons, arrows, timelines, or diagrams, not copyrighted characters/logos.
"""
    obj = gemini(prompt)
    if not isinstance(obj, dict) or len(obj.get("segments", [])) != int(count):
        raise RuntimeError(f"Gemini returned an invalid {kind} episode structure")
    for s in obj["segments"]:
        if not all(isinstance(s.get(k), str) and s[k].strip() for k in ("heading","narration","visual_hint")):
            raise RuntimeError("A segment is missing heading, narration, or visual_hint")
    return obj

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0,0), trial, font=fnt)[2] <= max_width:
            line = trial
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def draw_scene(segment, idx, total, size, kind, seed):
    w, h = size
    rng = random.Random(seed + idx * 101)
    im = Image.new("RGB", size, (9, 17, 38))
    px = im.load()
    # Smooth dark blue/purple gradient generated locally.
    for y in range(h):
        t = y / max(1, h-1)
        c = (int(8+14*t), int(18+10*t), int(42+25*t))
        for x in range(w):
            px[x,y] = c
    d = ImageDraw.Draw(im, "RGBA")
    # Original decorative geometry; no downloaded/copyrighted imagery.
    for j in range(18):
        x, y = rng.randint(0,w), rng.randint(0,h)
        r = rng.randint(max(8,w//90), max(18,w//24))
        d.ellipse((x-r,y-r,x+r,y+r), outline=(88,160,255,35), width=max(2,w//500))
    accent = (54, 211, 180, 230)
    d.rounded_rectangle((int(w*.07), int(h*.08), int(w*.93), int(h*.10)), radius=12, fill=accent)
    d.text((int(w*.08), int(h*.14)), f"LEARNWITHSHIVA  •  {idx+1:02d}/{total:02d}",
           font=font(max(18,w//48), True), fill=(155,190,225,255))
    heading_font = font(max(38, int(w*.060)), True)
    body_font = font(max(25, int(w*.032)), False)
    maxw = int(w*.82)
    heading_lines = wrap_text(d, segment["heading"].upper(), heading_font, maxw)
    y = int(h*.25)
    for line in heading_lines[:3]:
        d.text((int(w*.08), y), line, font=heading_font, fill=(255,255,255,255), stroke_width=1)
        y += int(heading_font.size*1.2)
    # A simple original visual cue panel.
    panel_top = int(h*.51)
    panel_bottom = int(h*.70)
    d.rounded_rectangle((int(w*.08),panel_top,int(w*.92),panel_bottom), radius=28,
                        fill=(25,45,78,210), outline=(54,211,180,170), width=max(2,w//500))
    hint = segment["visual_hint"]
    hint_lines = wrap_text(d, hint, body_font, int(w*.76))
    yy = panel_top + int(h*.045)
    for line in hint_lines[:3]:
        box = d.textbbox((0,0), line, font=body_font)
        d.text(((w-(box[2]-box[0]))//2, yy), line, font=body_font, fill=(180,235,230,255))
        yy += int(body_font.size*1.25)
    takeaway = "ONE IDEA. CLEARLY EXPLAINED."
    d.text((int(w*.08), int(h*.88)), takeaway, font=font(max(18,w//55),True), fill=(185,205,235,240))
    return im

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(f"Command failed: {' '.join(map(str,cmd))}\n{p.stderr[-2500:]}")
    return p.stdout

def render_episode(ep, kind):
    is_short = kind == "short"
    size = (720,1280) if is_short else (1280,720)
    segment_files = []
    for i, seg in enumerate(ep["segments"]):
        stem = f"{kind}_{i:02d}"
        wav = WORK / f"{stem}.wav"
        img = WORK / f"{stem}.png"
        mp4 = WORK / f"{stem}.mp4"
        # Open-source local TTS. No external voice subscription.
        run(["espeak-ng", "-v", "en-us+f3", "-s", "158" if is_short else "148",
             "-w", str(wav), seg["narration"]])
        audio_seconds = float(run(["ffprobe","-v","error","-show_entries","format=duration",
                                   "-of","default=noprint_wrappers=1:nokey=1",str(wav)]).strip())
        frame = draw_scene(seg, i, len(ep["segments"]), size, kind,
                           int(hashlib.sha256((ep["title"]+kind).encode()).hexdigest()[:8],16))
        frame.save(img)
        run(["ffmpeg","-y","-loop","1","-i",str(img),"-i",str(wav),
             "-c:v","libx264","-t",f"{audio_seconds:.3f}","-pix_fmt","yuv420p",
             "-vf",f"scale={size[0]}:{size[1]},format=yuv420p",
             "-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(mp4)])
        segment_files.append(mp4)
    concat = WORK / f"{kind}_concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_files))
    final = OUT / f"{kind}_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",
         "-movflags","+faststart",str(final)])
    thumb = OUT / f"{kind}_thumbnail.jpg"
    create_thumbnail(ep["thumbnail_text"], thumb, size)
    return final, thumb

def create_thumbnail(text, path, size):
    w,h = (1280,720)
    im = Image.new("RGB",(w,h),(10,20,45))
    d = ImageDraw.Draw(im)
    for i in range(12):
        x = (i*173) % w
        d.ellipse((x-120,80,x+120,320),outline=(40,170,180),width=5)
    d.rounded_rectangle((65,65,1215,655),radius=42,outline=(54,211,180),width=8)
    lines = wrap_text(d,text.upper(),font(92,True),1050)
    y = (h-len(lines)*112)//2
    for line in lines[:3]:
        bb=d.textbbox((0,0),line,font=font(92,True))
        d.text(((w-(bb[2]-bb[0]))//2,y),line,font=font(92,True),fill=(255,255,255))
        y+=112
    d.text((75,590),"LEARNWITHSHIVA",font=font(34,True),fill=(100,230,205))
    im.save(path,quality=92)

def youtube_client():
    client_id = require_env("YOUTUBE_CLIENT_ID")
    client_secret = require_env("YOUTUBE_CLIENT_SECRET")
    refresh_token = require_env("YOUTUBE_REFRESH_TOKEN")
    creds = Credentials(
        token=None, refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds.refresh(Request())
    return build("youtube","v3",credentials=creds)

def upload(youtube, video, thumb, ep, kind):
    suffix = " #Shorts" if kind == "short" else ""
    title = (ep["title"][:90] + suffix)[:100]
    desc = ep.get("description","") + "\n\nOriginal educational content created for LearnWithShiva."
    tags = [re.sub(r"[^A-Za-z0-9 ]","",t)[:30] for t in ep.get("tags",[])[:15]]
    body = {
        "snippet": {
            "title": title, "description": desc[:4900], "tags": tags,
            "categoryId": CATEGORY_ID, "defaultLanguage": LANGUAGE
        },
        "status": {
            "privacyStatus": PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True)
    req = youtube.videos().insert(part="snippet,status",body=body,media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress()*100)}%")
    video_id = response["id"]
    youtube.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(thumb),mimetype="image/jpeg")).execute()
    print(f"Uploaded {kind}: https://www.youtube.com/watch?v={video_id}")

def main():
    print("Creating original educational Short...")
    short_ep = make_episode("short")
    short_video, short_thumb = render_episode(short_ep,"short")
    print("Creating original educational long-form video...")
    long_ep = make_episode("long")
    long_video, long_thumb = render_episode(long_ep,"long")
    yt = youtube_client()
    upload(yt,short_video,short_thumb,short_ep,"short")
    upload(yt,long_video,long_thumb,long_ep,"long")
    print("Both uploads completed.")

if __name__ == "__main__":
    main()
