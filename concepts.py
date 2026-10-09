"""The vocabulary Clef-omni answers for every segment.

Each concept is one `noul` (yes/no) question. The search bar matches what you type against
`label` + `syn`, then ranks segments by P(yes). `kind` is shown in the UI:
  see  - answered from the frames
  hear - answered from the soundtrack (non-speech)
  say  - answered from what is spoken
  both - needs picture and sound together
"""
from __future__ import annotations

SEE, HEAR, SAY, BOTH = "see", "hear", "say", "both"


def see(cid, label, what, syn=()):
    return dict(id=cid, kind=SEE, label=label, syn=list(syn), q=f"Is {what} visible in the video?")


def hear(cid, label, what, syn=()):
    return dict(id=cid, kind=HEAR, label=label, syn=list(syn), q=f"Can you hear {what} in the audio?")


def topic(cid, label, what, syn=()):
    return dict(id=cid, kind=SAY, label=label, syn=list(syn), q=f"Does someone in the audio talk about {what}?")


def word(cid, label, spoken, syn=()):
    return dict(id=cid, kind=SAY, label=label, syn=list(syn), q=f"Does someone say the word '{spoken}' out loud?")


def both(cid, label, q, syn=()):
    return dict(id=cid, kind=BOTH, label=label, syn=list(syn), q=q)


def custom(cid, kind, label, q, syn=()):
    return dict(id=cid, kind=kind, label=label, syn=list(syn), q=q)


CONCEPTS = [
    # ------------------------------------------------------------------ people
    see("person", "person", "a person (a real human, not a drawing)", ["people", "human", "someone", "presenter"]),
    custom("talking_head", SEE, "talking head", "Is a person shown large in the frame, facing the camera, as the main subject?",
           ["face", "selfie", "on camera", "speaker", "host"]),
    see("webcam_inset", "webcam overlay", "a small webcam picture of a person overlaid in the corner of a screen recording",
        ["picture in picture", "pip", "facecam", "webcam", "inset"]),
    see("hat", "hat", "a person wearing a hat", ["fedora", "wearing a hat", "guy in a hat", "hat guy"]),
    see("cap", "baseball cap", "a person wearing a baseball cap", ["cap", "ball cap", "snapback"]),
    see("glasses", "glasses", "a person wearing glasses", ["spectacles", "eyeglasses", "specs"]),
    see("beard", "beard", "a person with a beard", ["bearded", "facial hair"]),
    see("bald", "bald", "a person with a bald or shaved head", ["shaved head", "no hair"]),
    see("cf_shirt", "cloudflare shirt", "a person wearing clothing with the Cloudflare logo", ["cloudflare t-shirt", "cloudflare tee", "branded shirt", "merch"]),
    see("mic", "microphone", "a microphone", ["mic", "podcast mic", "studio mic"]),
    see("headphones", "headphones", "a person wearing headphones or earbuds", ["headset", "earbuds"]),
    see("two_people", "two people", "two or more different real people", ["multiple people", "group", "interview", "duo"]),
    see("smiling", "smiling", "a person smiling or grinning", ["smile", "happy", "grin"]),
    see("gesturing", "hand gestures", "a person gesturing with their hands while talking", ["hands", "gesturing", "waving hands"]),
    see("pointing", "pointing", "a person pointing at something", ["points"]),
    see("grayscale_person", "black and white", "a person shown in black and white while the rest of the frame is in color",
        ["grayscale", "monochrome", "desaturated"]),
    see("plants", "plants", "plants or greenery", ["plant", "houseplant", "leaves", "greenery"]),
    see("bookshelf", "bookshelf", "a bookshelf or books in the background", ["books", "library", "shelves"]),
    see("home_office", "home office", "a home office or studio room behind a person", ["room", "studio", "office", "background"]),
    see("lights_bokeh", "blurry lights", "blurry out-of-focus lights in the background", ["bokeh", "fairy lights", "string lights"]),

    # ------------------------------------------------------------------ screens & software
    see("screen_recording", "screen recording", "a recording of a computer screen", ["screencast", "screen share", "desktop", "computer screen"]),
    see("code_editor", "code editor", "a code editor showing source code", ["code", "ide", "vs code", "vscode", "editor", "source code", "programming"]),
    see("terminal", "terminal", "a command-line terminal window", ["command line", "cli", "shell", "console", "bash", "zsh"]),
    see("browser", "web browser", "a web browser window", ["browser", "chrome", "website", "web page", "tab"]),
    see("cf_dashboard", "cloudflare dashboard", "the Cloudflare dashboard web interface", ["dashboard", "dash", "control panel"]),
    see("error_page", "error page", "an error page or error message", ["500", "404", "error", "something went wrong", "crash", "failure"]),
    see("auth_dialog", "login dialog", "a login, sign-in, or authorize-access dialog", ["login", "sign in", "oauth", "authorize", "permission"]),
    see("phone_ui", "phone screen", "a smartphone or mobile phone screen", ["phone", "mobile", "iphone", "smartphone", "app"]),
    see("diagram", "diagram", "a diagram, flowchart, or architecture drawing with boxes and arrows",
        ["architecture", "flowchart", "flow chart", "boxes and arrows", "system design"]),
    see("big_title", "title card", "large title text filling much of the screen", ["title", "headline", "big text", "title slide"]),
    see("bullets", "bullet list", "a bulleted or numbered list of text", ["list", "bullets", "bullet points", "slide"]),
    see("docs_page", "documentation", "a documentation or article web page with paragraphs of text", ["docs", "article", "readme", "blog post"]),
    see("github", "github", "a GitHub web page", ["repo page", "repository", "pull request", "github page"]),
    see("chat_ui", "chat interface", "a chat interface with messages, like an AI assistant chat", ["chat", "chatbot", "ai chat", "assistant", "messages"]),
    see("json", "json", "JSON data", ["json data", "api response", "payload"]),
    see("python_code", "python code", "Python source code", ["python", "py", "def", "import"]),
    see("ts_code", "typescript code", "JavaScript or TypeScript source code", ["typescript", "javascript", "js", "ts", "node"]),
    see("config_file", "config file", "a configuration file such as cloudflare.config.ts, wrangler.toml, or package.json",
        ["config", "configuration", "wrangler.toml", "package.json", "settings file"]),
    see("dark_ui", "dark mode", "software with a dark theme (light text on a dark background)", ["dark theme", "dark ui"]),
    see("light_ui", "light mode", "software with a light theme (dark text on a white background)", ["light theme", "white ui"]),
    see("cursor", "mouse cursor", "a mouse pointer or text cursor", ["pointer", "mouse", "cursor"]),
    see("highlight", "highlighted text", "text that is highlighted, selected, or boxed for emphasis", ["selection", "highlight", "emphasis", "callout"]),
    see("table", "table", "a table of data with rows and columns", ["spreadsheet", "rows", "columns", "grid"]),
    see("chart", "chart", "a chart or graph", ["graph", "plot", "bar chart", "line chart", "metrics", "analytics"]),
    see("cf_logo", "cloudflare logo", "the orange Cloudflare cloud logo", ["logo", "cloudflare cloud", "orange cloud", "brand"]),
    see("orange_button", "orange button", "an orange button", ["button", "cta", "call to action button"]),
    see("url_bar", "url", "a web address or URL", ["link", "address bar", "domain", "website address"]),
    see("form", "form", "a form with input fields", ["input", "text field", "fields", "form fields"]),
    see("log_output", "logs", "log output or build/deploy progress text scrolling in a terminal", ["logs", "build output", "deploy output", "progress", "stack trace"]),
    see("file_tree", "file tree", "a file explorer sidebar listing files and folders", ["files", "folders", "sidebar", "explorer", "project files"]),
    see("split_screen", "split screen", "two or more windows or panels side by side", ["side by side", "split", "multiple windows"]),
    see("animated_text", "animated text", "text animating or appearing word by word on screen", ["kinetic typography", "motion graphics", "captions"]),
    see("captions", "captions", "subtitles or captions of the speech", ["subtitles", "closed captions"]),
    see("emoji", "emoji", "emoji", ["emojis", "smiley"]),
    see("image_gen", "generated image", "an AI-generated image or picture being shown inside an app", ["ai image", "generated", "image result"]),

    # ------------------------------------------------------------------ illustration & art
    see("illustration", "illustration", "a drawing or illustration (not a photo, not a screen)", ["drawing", "art", "artwork", "painting", "cartoon"]),
    see("vintage_art", "vintage illustration", "an old-fashioned, vintage, or Victorian-style illustration",
        ["vintage", "victorian", "old timey", "retro", "antique"]),
    see("cartoon_char", "cartoon character", "a cartoon character or mascot", ["mascot", "character", "cartoon"]),
    see("carnival", "carnival", "a carnival, circus, or fairground", ["circus", "fair", "tent", "big top", "fairground"]),
    see("globe", "globe", "a globe or world map", ["world", "earth", "map", "planet"]),
    see("animal", "animal", "an animal", ["animals", "dog", "cat", "bird", "pet"]),
    see("food", "food", "food or a dish", ["meal", "dish", "dinner", "restaurant", "cooking"]),
    see("robot", "robot", "a robot", ["bot", "android", "machine"]),
    see("gift", "gifts", "wrapped gifts or presents", ["present", "presents", "gift", "birthday", "party"]),
    see("confetti", "confetti", "confetti, balloons, or celebration graphics", ["celebration", "balloons", "party", "launch"]),
    see("paper_texture", "paper texture", "a paper, parchment, or textured background", ["parchment", "paper", "texture", "craft"]),
    see("phone_device", "phone", "a telephone handset or phone call graphic", ["telephone", "call", "phone call", "dial"]),
    see("gradient_bg", "gradient", "a colorful gradient background", ["gradient", "colorful background", "rainbow"]),
    see("orange", "orange", "a frame dominated by the color orange", ["orange color", "amber"]),
    see("blue", "blue", "a frame dominated by the color blue", ["blue color", "navy"]),
    see("pink_purple", "pink", "a frame dominated by pink or purple", ["purple", "magenta", "violet"]),
    see("green", "green", "a frame dominated by the color green", ["green color"]),
    see("mostly_white", "white", "a mostly white, bright frame", ["bright", "white background", "minimal"]),
    see("mostly_dark", "dark", "a mostly dark or black frame", ["black", "dark background", "night"]),
    see("cloud", "cloud", "a cloud shape or cloud graphic", ["clouds", "cloud icon"]),
    see("git_ui", "git", "Git commands or a Git interface such as branches, commits, fork, or clone", ["branch", "commit", "fork", "clone", "version control"]),

    # ------------------------------------------------------------------ sounds (non-speech)
    hear("speech", "speech", "someone speaking", ["talking", "voice", "speaking", "narration", "voiceover"]),
    hear("music", "music", "music", ["song", "soundtrack", "beat", "tune", "background music"]),
    hear("music_under_speech", "music under voice", "background music playing underneath someone speaking", ["background music", "bed music"]),
    custom("music_only", HEAR, "music only", "Is music playing with nobody speaking?", ["instrumental", "no talking", "just music", "music but nobody talking"]),
    hear("sfx", "sound effects", "a sound effect such as a whoosh, pop, ding, or swoosh", ["whoosh", "pop", "ding", "swoosh", "sfx", "sound effect"]),
    hear("typing", "typing", "keyboard typing", ["keyboard", "keystrokes", "clacking"]),
    hear("clicks", "clicking", "mouse clicks", ["click", "mouse click"]),
    hear("laughing", "laughing", "someone laughing", ["laugh", "laughter", "chuckle", "funny"]),
    custom("silence", HEAR, "silence", "Is the audio silent or nearly silent?", ["quiet", "no sound", "mute", "silent"]),
    hear("ringing", "phone ringing", "a phone ringing, a dial tone, or phone call audio", ["ring", "ringtone", "dial tone", "phone call"]),
    hear("synthetic_voice", "robot voice", "a synthetic, computer-generated, or text-to-speech voice", ["ai voice", "tts", "text to speech", "computer voice", "synthetic voice"]),
    hear("two_voices", "conversation", "two or more different people speaking", ["dialogue", "conversation", "two voices", "interview"]),
    custom("excited", HEAR, "excited", "Does the speaker sound excited or enthusiastic?", ["enthusiastic", "energetic", "hyped", "excitement"]),
    custom("calm", HEAR, "calm voice", "Does the speaker sound calm and relaxed?", ["relaxed", "chill", "soothing"]),
    custom("fast_talk", HEAR, "fast talking", "Is the speaker talking very fast?", ["rapid", "quick", "speed"]),
    hear("breath_pause", "pause", "a noticeable pause or hesitation in the speech", ["um", "uh", "hesitation", "pause"]),
    hear("applause", "applause", "applause or cheering", ["clapping", "cheering", "crowd"]),

    # ------------------------------------------------------------------ spoken words / topics
    word("w_cloudflare", "cloudflare mentioned", "Cloudflare", ["cloudflare", "says cloudflare"]),
    word("w_workers", "workers mentioned", "Workers", ["workers", "cloudflare workers", "worker"]),
    topic("t_durable_objects", "durable objects", "Durable Objects", ["durable object", "do", "stateful"]),
    topic("t_workflows", "workflows", "Workflows", ["workflow", "steps", "durable execution"]),
    topic("t_r2", "r2", "R2 object storage", ["object storage", "bucket", "s3"]),
    topic("t_d1", "d1", "D1 or SQL databases", ["database", "sql", "sqlite", "db"]),
    topic("t_kv", "kv", "KV key-value storage", ["key value", "kv store"]),
    topic("t_ai_gateway", "ai gateway", "AI Gateway", ["gateway"]),
    topic("t_workers_ai", "workers ai", "Workers AI or running AI models", ["models", "inference", "ai models"]),
    topic("t_mcp", "mcp", "MCP (Model Context Protocol) servers", ["model context protocol", "mcp server"]),
    topic("t_cf_cli", "cf cli", "the cf command-line tool", ["cf", "command line tool"]),
    topic("t_wrangler", "wrangler", "Wrangler", ["wrangler cli"]),
    topic("t_previews", "previews", "preview deployments or preview URLs", ["preview", "preview url", "preview deployments", "staging"]),
    topic("t_artifacts", "artifacts", "Cloudflare Artifacts", ["artifact"]),
    topic("t_containers", "containers", "containers or Docker", ["container", "docker"]),
    topic("t_isolates", "isolates", "V8 isolates or sandboxes", ["isolate", "sandbox", "v8"]),
    topic("t_python", "python", "the Python programming language", ["python", "py", "pyodide"]),
    topic("t_typescript", "typescript", "TypeScript or JavaScript", ["javascript", "js", "ts"]),
    topic("t_git", "git", "Git or GitHub repositories", ["github", "repo", "repository", "git"]),
    topic("t_agents", "ai agents", "AI agents", ["agent", "agents", "agentic"]),
    topic("t_llm", "llms", "large language models or LLMs", ["llm", "gpt", "claude", "language model", "ai model"]),
    topic("t_flue", "flue", "Flue", ["flue agents"]),
    topic("t_blog", "blog", "writing a blog or blog posts", ["blog post", "writing", "article", "content"]),
    topic("t_pricing", "pricing", "pricing, cost, or billing", ["price", "cost", "billing", "money", "cheap"]),
    topic("t_free", "free", "something being free or a free tier", ["free tier", "no cost", "for free"]),
    topic("t_beta", "open beta", "an open beta or beta release", ["beta", "launch", "release", "available today"]),
    topic("t_deploy", "deploy", "deploying an application", ["deployment", "ship", "shipping", "publish", "go live"]),
    topic("t_realtime", "real-time", "real-time updates or WebSockets", ["realtime", "live updates", "websockets", "websocket", "streaming"]),
    topic("t_phone_call", "phone calls", "phone calls or calling a phone number", ["call", "telephony", "dial", "calling"]),
    topic("t_auth", "authentication", "API tokens, authentication, or logging in", ["auth", "token", "api key", "login", "oauth"]),
    topic("t_dashboard", "dashboard talk", "the Cloudflare dashboard", ["dashboard", "ui"]),
    topic("t_config", "configuration", "configuration or config files", ["config", "settings", "configure"]),
    topic("t_performance", "performance", "speed, latency, or performance", ["fast", "speed", "latency", "quick", "performance"]),
    topic("t_security", "security", "security or safety", ["secure", "safety", "attack", "protect"]),
    topic("t_errors", "debugging", "errors, bugs, or debugging", ["error", "bug", "debug", "fix", "broken"]),
    topic("t_testing", "testing", "testing code", ["tests", "test", "qa"]),
    topic("t_open_source", "open source", "open source", ["oss", "open-source"]),
    topic("t_design", "design", "design or how a website looks", ["looks", "ui design", "styling", "css", "aesthetic", "ai-generated look"]),
    topic("t_images", "images", "images, photos, or image assets", ["image", "photo", "pictures", "assets"]),
    topic("t_frontend", "frontend", "frontend frameworks like React, Vite, or CSS", ["react", "vite", "css", "front end", "html"]),
    topic("t_npm", "npm", "installing packages with npm", ["npm install", "package", "dependencies"]),
    topic("t_env", "secrets", "environment variables or secrets", ["environment variables", "env", "secret", "secrets"]),
    topic("t_scheduling", "scheduling", "cron jobs, scheduling, or queues", ["cron", "schedule", "queues", "background jobs"]),
    topic("t_storage", "file upload", "uploading or storing files", ["upload", "files", "storage"]),
    topic("t_prompt", "prompts", "prompts or prompt engineering", ["prompt", "system prompt", "instructions"]),
    topic("t_tools", "tool calling", "tool calling or giving an AI tools", ["tools", "function calling", "tool use"]),
    topic("t_voice", "voice ai", "voice, speech, or talking to an AI by voice", ["voice", "speech to text", "talking to ai"]),
    topic("t_api", "api", "an API or API requests", ["rest", "endpoint", "http", "request"]),
    topic("t_edge", "edge", "the edge or Cloudflare's global network", ["global network", "edge network", "cdn", "data centers"]),
    custom("t_demo", SAY, "demo", "Does the speaker say they are about to show or demo something?", ["let me show you", "demo", "walkthrough", "show"]),
    custom("t_greeting", SAY, "intro", "Does the speaker introduce themselves or greet the audience?",
           ["hi", "hello", "greeting", "introduction", "my name is", "welcome"]),
    custom("t_signoff", SAY, "outro", "Does the speaker say goodbye, thanks for watching, or wrap up?",
           ["goodbye", "bye", "thanks for watching", "sign off", "ending", "wrap up"]),
    custom("t_cta", SAY, "call to action", "Does the speaker ask viewers to try something, subscribe, or check out a link?",
           ["subscribe", "try it", "check it out", "link in description", "sign up"]),
    custom("t_joke", SAY, "joke", "Does the speaker make a joke or say something humorous?", ["funny", "humor", "humour", "pun"]),
    custom("t_question", SAY, "question", "Does the speaker ask the audience a question?", ["asks", "rhetorical question"]),
    custom("t_numbers", SAY, "numbers", "Does the speaker mention specific numbers or statistics?", ["stats", "statistics", "percent", "metrics"]),
    custom("t_compare", SAY, "comparison", "Does the speaker compare two approaches or products?", ["versus", "vs", "compare", "instead of", "better than"]),
    custom("t_problem", SAY, "the problem", "Does the speaker describe a problem or pain point?", ["pain", "problem", "frustrating", "hard", "annoying"]),
    custom("t_steps", SAY, "step by step", "Does the speaker walk through steps one by one?", ["tutorial", "how to", "first", "next", "steps"]),

    # ------------------------------------------------------------------ picture + sound together
    both("b_talk_no_screen", "talking, no code", "Is a person talking to the camera with no code or screen recording visible?",
         ["just talking", "talking head only", "no code", "face only"]),
    both("b_explain_code", "explaining code", "Is someone explaining code that is visible on screen?",
         ["code walkthrough", "narrating code", "explains code", "reading code"]),
    both("b_typing_live", "live typing", "Is text being typed on screen right now?", ["typing code", "writing code", "live coding", "typing"]),
    both("b_live_demo", "live demo", "Is someone demonstrating software live while narrating?", ["demo", "demonstration", "walkthrough", "showing"]),
    both("b_music_graphics", "music over graphics", "Is music playing over graphics or animation with no person speaking?",
         ["intro", "animation with music", "motion graphics", "title sequence"]),
    both("b_intro", "video intro", "Is this the opening of a video, with a title or the host introducing the topic?", ["opening", "start", "beginning", "intro"]),
    both("b_outro", "video ending", "Is this the end of a video, with a wrap-up or end screen?", ["end", "ending", "end screen", "conclusion", "outro"]),
    both("b_laugh_cam", "laughing on camera", "Is a person visible on camera laughing?", ["laughing face", "cracking up"]),
    both("b_explain_diagram", "explaining diagram", "Is someone explaining a diagram that is visible on screen?", ["architecture explanation", "whiteboard"]),
    both("b_terminal_cmd", "running commands", "Is someone running commands in a terminal while talking about them?", ["running a command", "cli demo", "terminal demo"]),
    both("b_error_reaction", "error demo", "Is an error visible on screen while the speaker talks about it?", ["showing an error", "broken demo", "it failed"]),
    both("b_cf_brand", "cloudflare branding", "Is Cloudflare shown on screen (logo, shirt, or name) while someone speaks?",
         ["cloudflare on screen", "branding", "logo"]),
    both("b_python_both", "python on screen and spoken", "Is Python code visible while someone talks about Python?", ["python demo"]),
    both("b_phone_demo", "phone demo", "Is a phone screen shown while someone talks about calling or phones?", ["calling demo", "mobile demo"]),
    both("b_hat_talking", "hat guy talking", "Is a person wearing a hat talking on camera?", ["man in a hat talking"]),
    both("b_two_talking", "two people talking", "Are two people on screen talking with each other?", ["chat", "interview", "discussion"]),
]


def check() -> None:
    ids = [c["id"] for c in CONCEPTS]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, dupes
    for c in CONCEPTS:
        assert len(c["id"]) <= 100 and c["q"].endswith("?"), c


check()

if __name__ == "__main__":
    from collections import Counter

    print(len(CONCEPTS), "concepts", dict(Counter(c["kind"] for c in CONCEPTS)))
