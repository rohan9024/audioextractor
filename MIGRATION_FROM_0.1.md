# Migrating from 0.1.x

The 0.2 API returns an `ExtractionResult` instead of only a `Path`.

Old:

```python
path = extract_audio("video.mp4")
```

New:

```python
result = extract_audio("video.mp4")
path = result.path
```

The package now includes a real async API:

```python
result = await extract_audio_async("video.mp4")
```

For server workloads, prefer one reusable `AudioExtractor` instance so you can bound concurrency:

```python
extractor = AudioExtractor(max_concurrency=3)
result = await extractor.extract_async("video.mp4")
```
