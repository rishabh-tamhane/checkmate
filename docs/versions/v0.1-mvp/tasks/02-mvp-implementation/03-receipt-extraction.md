# Milestone 3: Receipt Extraction

## Status

Ready.

## Outcome

A user can upload one supported restaurant-receipt image, receive structured
editable suggestions from the approved OpenAI adapter, and continue through the
same manual workflow. Invalid images and provider failures are safe,
actionable, bounded, and never destroy the current draft.

## Requirement traceability

- Receipt extraction in requirements section 3
- Editable receipt behavior in section 4
- Acceptance criteria 1, 2, and 6

## Design sources

- [Receipt extraction](../../technical-design/02-mvp-implementation/04-receipt-extraction.md)
- [Web workflow](../../technical-design/02-mvp-implementation/03-web-workflow.md)
- [Security and privacy](../../technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [Runtime and testing](../../technical-design/02-mvp-implementation/07-runtime-and-testing.md)

## Dependencies

- [ ] **M3-01:** Add `openai`, `pillow`, and `python-multipart` with `uv add`;
  add `pytest-asyncio` as a development dependency if the existing test stack
  cannot exercise the async parser boundary without it.
- [ ] **M3-02:** Confirm the OpenAI SDK, Pillow, and multipart parser remain
  outside the domain package and no OCR, storage, or background-job dependency
  is added.

## Application-owned extraction contract

- [ ] **M3-03:** Define immutable `NormalizedReceiptImage` with JPEG bytes,
  dimensions, and media type.
- [ ] **M3-04:** Define `ExtractionResult` with ordered editable item drafts,
  optional restaurant/date/totals strings, and non-blocking review notices.
- [ ] **M3-05:** Define asynchronous vendor-neutral `ReceiptParser.parse` and a
  deterministic `FakeReceiptParser` for tests and local demonstrations.
- [ ] **M3-06:** Prevent SDK response objects, provider IDs, prompts, and token
  accounting from crossing into application, domain, or web models.

## Bounded upload and image normalization

- [ ] **M3-07:** Accept one multipart field named `receipt` and reject missing,
  duplicate, or structurally invalid upload input with a stable safe error.
- [ ] **M3-08:** Read at most 10 MiB plus one byte, return `413` when the bound is
  exceeded, and close the framework upload in `finally`.
- [ ] **M3-09:** Decode content with Pillow while allowing only JPEG, PNG, and
  WebP; do not trust filename extensions or declared content type.
- [ ] **M3-10:** Reject invalid content as `400`, unsupported formats as `415`,
  animations and multi-frame images, images over 25 megapixels, and Pillow
  decompression-bomb warnings.
- [ ] **M3-11:** Fully decode the image, apply EXIF orientation, convert it to
  RGB, and downscale without upscaling so its longest edge is at most 4,000
  pixels.
- [ ] **M3-12:** Re-encode as JPEG quality 90 without source EXIF, XMP, comments,
  filenames, or other metadata.
- [ ] **M3-13:** Keep original and normalized bytes only for the active request
  and never create an application-managed receipt file.

## OpenAI adapter

- [ ] **M3-14:** Implement the private strict Pydantic provider schema with
  optional metadata/totals, required item name and line-total string, optional
  quantity, rejected unknown keys, 100-item limit, and 200-character text
  limits.
- [ ] **M3-15:** Add a separately versioned extraction prompt whose only job is
  transcription and which treats all image text as untrusted receipt content.
- [ ] **M3-16:** Call the Responses API with model snapshot
  `gpt-5.4-mini-2026-03-17`, image detail `original`, Structured Outputs, no
  tools, no conversation or file object, inline image bytes, and `store=False`.
- [ ] **M3-17:** Trim provider strings and normalize only unambiguous monetary
  forms; do not repair arithmetic or invent missing receipt values.
- [ ] **M3-18:** Default an absent visible tip to `0.00`, leave other missing
  required money fields blank, and add a general review notice to every
  successful extraction.
- [ ] **M3-19:** Configure a 30-second overall provider timeout, at most one SDK
  retry for approved transient failures, and a four-call per-process semaphore.
- [ ] **M3-20:** Map timeout to sanitized `504`; map refusal, unavailability,
  exhausted rate limit, and invalid structured output to sanitized `502`.

## Application, HTTP, and browser integration

- [ ] **M3-21:** Implement the extraction application service so validation,
  normalization, parser invocation, result conversion, and cleanup have one
  explicit orchestration path.
- [ ] **M3-22:** Implement `POST /api/receipts/extract` with stable response and
  error schemas, `Cache-Control: no-store`, request IDs, same-origin protection,
  and no sensitive body logging.
- [ ] **M3-23:** Select the OpenAI adapter only when `OPENAI_API_KEY` is present;
  otherwise advertise manual-entry mode without making application health fail.
- [ ] **M3-24:** Add the upload control and pre-upload disclosure that the image
  is sent to OpenAI, extracted values require review, and manual entry is
  available.
- [ ] **M3-25:** On explicit successful upload, replace receipt fields and item
  IDs, retain participants, clear assignments, and calculate the new draft.
- [ ] **M3-26:** On upload or provider failure, retain the entire existing draft,
  show the actionable safe error and retry option, and keep manual editing
  available.
- [ ] **M3-27:** Do not expose the API key, provider response body, prompt, SDK
  exception, original filename, receipt values, or image bytes to HTML, client
  errors, or logs. Log only request ID, upload byte count, normalized
  dimensions, model, prompt version, duration, and safe error category.

## Verification

- [ ] **M3-28:** Generate synthetic images to unit-test each accepted format,
  invalid bytes, size boundary, pixel boundary, decompression warning,
  animation, EXIF rotation, color conversion, downscaling, and no-upscale case.
- [ ] **M3-29:** Verify normalized JPEG dimensions, orientation, quality path,
  and absence of source metadata without committing real receipt images.
- [ ] **M3-30:** Contract-test the OpenAI adapter with synthetic SDK response
  objects for success, missing values, unknown keys, refusal, timeout, rate
  limit, server error, retry exhaustion, and invalid structured output.
- [ ] **M3-31:** Application-test fake-parser success and every failure category
  without importing provider objects outside the adapter.
- [ ] **M3-32:** HTTP-test multipart bounds, content detection, status mapping,
  response schema, origin policy, cache policy, cleanup, and privacy-safe logs.
- [ ] **M3-33:** Browser-test successful upload, editable correction,
  participant retention, assignment clearing, failure preservation, retry, and
  no-key manual mode using the fake parser.
- [ ] **M3-34:** Create 12 generated external-evaluation receipts covering
  clean, rotated, skewed, long, low-contrast, and optional-tip layouts.
- [ ] **M3-35:** Run the opt-in `external` evaluation with a real key and record
  12/12 schema-valid outputs, exact item counts and money, no invented items,
  and at least 90% exact normalized optional text before merging the adapter;
  record metrics without committing provider response bodies.
- [ ] **M3-36:** Run all required `AGENTS.md` checks with normal CI remaining
  credential-free and network-free.

## Completion criteria

- [ ] Acceptance criteria 1, 2, and 6 pass with the deterministic fake parser.
- [ ] The recorded external evaluation meets every approved threshold.
- [ ] Unsupported or hostile uploads cannot bypass byte, pixel, format,
  animation, or metadata controls.
- [ ] Provider failure never loses the user's draft or disables manual entry.
- [ ] Normal automated tests contain only generated receipts and fictional data.
