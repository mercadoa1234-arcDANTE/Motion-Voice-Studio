# Motion-Voice-Studio — CPU-only Docker image
#
# Build:
#   docker build -t motion-voice-studio .
#
# Run a storyboard:
#   docker run --rm -v "$PWD":/work motion-voice-studio /work/storyboard.json
#
# Or interactive shell:
#   docker run --rm -it -v "$PWD":/work motion-voice-studio bash
#
# Image size: ~1.5 GB (1 GB of that is TeX Live for MathTex).
# To skip TeX Live and shrink to ~500 MB, build with:
#   docker build --build-arg INSTALL_LATEX=0 -t motion-voice-studio:slim .

FROM ubuntu:24.04

# ── System packages ───────────────────────────────────────────────────────

ARG INSTALL_LATEX=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        python3 python3-pip python3-dev \
        ffmpeg \
        espeak-ng \
        dvisvgm \
        libpangocairo-1.0-0 libpango1.0-dev libcairo2-dev pkg-config \
        poppler-utils \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN if [ "$INSTALL_LATEX" = "1" ]; then \
        apt-get update -qq && \
        apt-get install -y -qq --no-install-recommends \
            texlive-latex-extra texlive-fonts-recommended texlive-latex-recommended && \
        rm -rf /var/lib/apt/lists/* ; \
    fi

# ── Python packages ───────────────────────────────────────────────────────

WORKDIR /opt/motion-voice-studio
COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

# ── Repository ────────────────────────────────────────────────────────────

COPY . /opt/motion-voice-studio

# ── Assemble Kokoro model at build time ───────────────────────────────────
# Bakes the 156 MB ONNX into the image so containers start ready-to-render.
# If the parts are missing from the build context, this fails the build
# loudly rather than producing an image that can't speak.

RUN python3 Kokoro_TTS_Agent_Skill_Pack/combine.py \
        --manifest Kokoro_TTS_Agent_Skill_Pack/manifest.json \
        --out model/ && \
    cp Kokoro_TTS_Agent_Skill_Pack/config.json model/ && \
    mkdir -p voices && cp kokoro-voices/*.pt voices/ 2>/dev/null || true && \
    echo "Model and voices staged at build time."

# ── Sanity check at build time ────────────────────────────────────────────
# Catches broken images before they ship.

RUN python3 -c "import manim, onnxruntime; from phonemizer.backend import EspeakBackend; \
    print('runtime imports ok:', manim.__version__, onnxruntime.__version__)" && \
    python3 -c "import sys; sys.path.insert(0, 'scripts'); \
    from kokoro_engine import KokoroEngine; \
    e = KokoroEngine('model/kokoro-v1_0_fp16.onnx', 'model/config.json', 'voices'); \
    a, sr = e.synthesize('Image built.', voice='af_bella'); \
    print(f'kokoro ok: {len(a)/sr:.2f}s audio')"

# ── Default invocation ────────────────────────────────────────────────────
# `docker run motion-voice-studio /path/to/storyboard.json` will render.
# `docker run -it motion-voice-studio bash` for shell access.

ENV MVS_HOME=/opt/motion-voice-studio
ENV PATH=/opt/motion-voice-studio/scripts:$PATH

ENTRYPOINT ["python3", "/opt/motion-voice-studio/scripts/voiceover.py"]
CMD ["--help"]
