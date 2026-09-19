from audioextract import extract_audio

result = extract_audio(
    "video.mp4",
    output_format="wav",
    overwrite=True,
)
print(result)
