import asyncio

from audioextract import extract_audio_async


async def main() -> None:
    result = await extract_audio_async("video.mp4", overwrite=True)
    print(result.path)


asyncio.run(main())
