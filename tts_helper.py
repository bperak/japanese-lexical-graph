import base64
import mimetypes
import os
import re
import struct
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def save_binary_file(file_path: str, data: bytes) -> None:
    """
    Save binary data to a file.

    Args:
        file_path: Path to save the file.
        data: Binary audio data.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(data)
    logger.info(f"File saved to: {file_path}")


def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """
    Parses bits per sample and rate from an audio MIME type string.

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate".
    """
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.lower().startswith("audio/l"):
            try:
                bits_per_sample = int(param.split("l", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Wrap raw audio data with a WAV header based on mime_type parameters.

    Args:
        audio_data: Raw audio bytes.
        mime_type: MIME type describing format and rate.

    Returns:
        Bytes of a valid WAV file.
    """
    params = parse_audio_mime_type(mime_type)
    bits_per_sample = params.get("bits_per_sample", 16)
    sample_rate = params.get("rate", 24000)
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data


def generate_tts(
    japanese_text: str,
    translation_text: str,
    file_prefix: str = "tts",
    output_dir: str = ".",
    api_key: str | None = None,
    model: str = "gemini-2.5-pro-preview-tts",
) -> list[str]:
    """
    Generate a multi-speaker TTS audio file for given Japanese and translation texts.

    Args:
        japanese_text: The Japanese text (kanji/hiragana) to read.
        translation_text: The English translation to read.
        file_prefix: Prefix for output filenames.
        output_dir: Directory to save audio files.
        api_key: Google GenAI API key (if None, uses environment var).
        model: The TTS model name to use.

    Returns:
        A list of file paths to the generated audio files.
    """
    # Configure client
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()

    # Prepare content with speaker labels
    text = (
        f"Read aloud in a warm, welcoming tone\n"
        f"Speaker 1: {japanese_text}\n"
        f"Speaker 2: {translation_text}"
    )
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]

    # Configure multi-speaker speech synthesis
    generate_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 1",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 2",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Puck"
                            )
                        ),
                    ),
                ]
            )
        ),
    )

    # Stream generation and save files
    file_paths: list[str] = []
    file_index = 0
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_config,
    ):
        # Skip chunks without audio data
        if not chunk.candidates or not chunk.candidates[0].content.parts:
            continue
        part = chunk.candidates[0].content.parts[0]
        if part.inline_data and part.inline_data.data:
            data = part.inline_data.data
            ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".wav"
            if ext == ".wav" and not part.inline_data.mime_type.startswith("audio/"):
                data = convert_to_wav(data, part.inline_data.mime_type)
            filename = f"{file_prefix}_{file_index}{ext}"
            output_path = os.path.join(output_dir, filename)
            save_binary_file(output_path, data)
            file_paths.append(output_path)
            file_index += 1
        else:
            logger.info(chunk.text)

    return file_paths 