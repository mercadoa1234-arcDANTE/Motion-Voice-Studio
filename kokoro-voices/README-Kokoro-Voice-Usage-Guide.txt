💡 Customize pronunciation with Markdown link syntax and /slashes/ like [Kokoro](/kˈOkəɹO/)

💬 To adjust intonation, try punctuation ;:,.!?—…"()“” or stress ˈ and ˌ

⬇️ Lower stress [1 level](-1) or [2 levels](-2)

⬆️ Raise stress 1 level [or](+2) 2 levels (only works on less stressed, usually short words)

Subjectively, voices will sound better or worse to different people.

Support for non-English languages may be absent or thin due to weak G2P and/or lack of training data. Some languages are only represented by a small handful or even just one voice (French).

Most voices perform best on a "goldilocks range" of 100-200 tokens out of ~500 possible. Voices may perform worse at the extremes:

Weakness on short utterances, especially less than 10-20 tokens. Root cause could be lack of short-utterance training data and/or model architecture. One possible inference mitigation is to bundle shorter utterances together.
Rushing on long utterances, especially over 400 tokens. You can chunk down to shorter utterances or adjust the speed parameter to mitigate this.