import asyncio

from audioextract import AudioExtractor, ExtractionOptions

extractor = AudioExtractor(
    max_concurrency=2,
    options=ExtractionOptions(overwrite=True),
)


async def main() -> None:
    results = await asyncio.gather(
        extractor.extract_async("one.mp4"),
        extractor.extract_async("two.mp4"),
        extractor.extract_async("three.mp4"),
    )
    for result in results:
        print(result.path)


asyncio.run(main())
