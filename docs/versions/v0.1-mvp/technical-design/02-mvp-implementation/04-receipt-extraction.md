# Receipt Extraction Guide

## Status

Approved.

Approval date: 2026-08-19.

## Document role

This guide explains the receipt-upload, image-normalization, OpenAI adapter,
failure-handling, and extraction-evaluation approach proposed in
[`../02-mvp-implementation.md`](../02-mvp-implementation.md). The parent
document remains authoritative. This status records review of this design area;
it does not approve the overall workstream.

Read this guide before implementing upload handling, Pillow normalization, the
`ReceiptParser` protocol, the OpenAI adapter, parser fakes, or extraction tests.

## Extraction is input assistance, not business logic

The provider's job is to transcribe visible receipt information into an
editable shape. It must not decide who owes money, repair inconsistent totals,
or apply tax and tip rules.

```text
Receipt image
     |
     v
Image validation and normalization
     |
     v
ReceiptParser adapter
     |
     v
Editable suggestions
     |
     v
User review and correction
     |
     v
Normal domain validation and calculation
```

Every provider value is a suggestion. The user can edit it, and the same
validation pipeline handles extracted and manually entered data.

## Why use a protocol

The application needs one capability: turn a normalized receipt image into an
extraction result. It does not need to know how an OpenAI request is created.

```python
class ReceiptParser(Protocol):
    async def parse(self, image: NormalizedReceiptImage) -> ExtractionResult: ...
```

This narrow boundary allows:

```text
ReceiptParser
    |
    +-- OpenAIReceiptParser  production behavior
    `-- FakeReceiptParser    deterministic tests and local demonstrations
```

The application owns `NormalizedReceiptImage` and `ExtractionResult`. OpenAI
SDK request and response types remain inside the adapter.

## Upload boundary

The endpoint accepts one multipart field named `receipt`. Multipart encoding is
the standard browser mechanism for sending file bytes and accompanying form
metadata in an HTTP request.

The filename and declared media type are untrusted hints. A file named
`receipt.jpg` could contain unrelated or malicious bytes. Pillow must decode
the content successfully as one of the explicitly accepted formats: JPEG, PNG,
or WebP. This includes the narrow iPhone MPO/JPEG compatibility case described
below.

### Size enforcement

The server reads at most 10 MiB plus one byte:

```text
0 through 10 MiB       -> continue validation
10 MiB plus one byte   -> reject as too large
```

Reading only to the bound prevents an untrusted client from forcing the
application to buffer an unlimited request before checking its size.

Encoded byte size and decoded pixel count protect against different risks. A
highly compressed image can have a small file size but expand to enormous
dimensions, so the design also rejects images over 25 megapixels.

## Image normalization pipeline

Normalization creates one safe, predictable provider input:

```text
Uploaded bytes
    |
    | decode only JPEG, PNG, or WebP
    v
Decoded single-frame image or approved MPO primary frame
    |
    | reject decompression bombs and every other multi-frame image
    v
Apply EXIF orientation
    |
    | convert color mode to RGB
    v
Downscale longest edge to at most 4,000 px
    |
    | never upscale a smaller image
    v
Re-encode as JPEG quality 90
    |
    | omit source metadata
    v
NormalizedReceiptImage
```

Applying EXIF orientation is important because a phone may store landscape
pixels with metadata saying they should be displayed as portrait. The vision
provider should receive the same orientation the user saw.

Re-encoding removes source EXIF, XMP, comments, filename information, and other
metadata that are unnecessary for transcription. It also gives the adapter one
known media type and color representation.

### iPhone MPO/JPEG compatibility

Some iPhones write a file with a normal JPEG signature and `.JPG` extension but
include an MPO index plus auxiliary image data. Pillow correctly identifies
that container as `MPO`, reports multiple frames, and therefore caused the
previous blanket multi-frame check to reject an otherwise valid receipt photo.

This case is accepted only when the encoded content has a JPEG signature and
Pillow identifies it as MPO. The normalizer explicitly selects frame zero,
checks that primary frame against the 25-megapixel limit, and fully decodes only
that frame. It does not seek, decode, combine, or transmit any auxiliary frame.
The 10 MiB encoded-size limit still bounds the complete uploaded container.

The selected frame follows the normal orientation, RGB conversion, resizing,
and JPEG re-encoding pipeline. Re-encoding omits the MPO index and all source
metadata, so the provider receives one metadata-free JPEG. Animated PNG/WebP
and every other multi-frame input remain rejected. This compatibility rule does
not create a general multi-photo upload feature.

The original upload and normalized bytes live only for the request. They are
not written to an application-managed receipt directory.

## Provider request design

The parent design selects the OpenAI Responses API, a dated model snapshot,
image detail `original`, and Structured Outputs.

The dated snapshot makes evaluation meaningful: a moving alias could change
behavior without a code change. The model identifier and prompt version are
therefore treated like reviewed application inputs.

The provider request:

- Contains one normalized image.
- Uses a bounded structured schema.
- Has no tools and cannot browse.
- Uses `store=False`.
- Does not create an OpenAI file object or conversation.
- Instructs the model to transcribe rather than calculate.
- Treats text inside the image as data, not as instructions.

The last point protects against prompt-like text printed on a receipt. For
example, text saying “ignore previous instructions” is still receipt content
and must not change the provider's job.

## Why structured output uses strings for money

JSON numbers commonly become binary floating-point values somewhere in a data
pipeline. Receipt amounts are requested as strings instead:

```json
{
  "name": "Noodles",
  "quantity": "1",
  "line_total": "16.00"
}
```

The adapter can normalize an unambiguous string, but it must not repair receipt
arithmetic. If extracted item totals disagree with the extracted subtotal, the
user sees the normal reconciliation error.

## Provider schema behavior

The schema is strict about shape but tolerant of information that may not be
visible:

- Restaurant and date may be `null`.
- Optional totals may be `null` when they cannot be read.
- Each item requires a name and line-total string.
- Quantity may be absent.
- Unknown keys are rejected.
- Item count and text length are bounded.

A missing visible tip becomes `0.00` because absence of tip is meaningful in
the supported receipt model. Other required money fields remain blank when the
provider cannot supply them, prompting user correction rather than invention.

## Asynchronous execution

Calling the provider waits on network I/O, so the parser protocol is
asynchronous. While one request is waiting, the ASGI process can continue
servicing unrelated lightweight requests.

Asynchronous code does not make the external provider faster. Timeouts and
concurrency bounds are still required.

```text
Maximum active extraction calls per process: 4
Overall provider timeout:                    30 seconds
SDK retries for selected transient errors:   at most 1
```

The semaphore limits expensive in-process work. It is not a public rate limiter
and does not coordinate across multiple containers.

## Failure translation

Clients should receive a stable application error, not an SDK exception or
provider response body.

| Failure | HTTP result | User outcome |
|---|---:|---|
| Invalid image content | 400 | Choose a valid receipt image |
| Upload exceeds 10 MiB | 413 | Choose a smaller image |
| Unsupported format | 415 | Use JPEG, PNG, or WebP |
| Provider timeout | 504 | Retry or enter manually |
| Provider refusal/unavailability/invalid response | 502 | Retry or enter manually |
| Unexpected internal failure | 500 | Safe message with request ID |

The browser preserves the current draft in all extraction-failure cases.

## Manual-entry mode

The web application remains useful without `OPENAI_API_KEY`. It starts normally,
explains that automatic extraction is unavailable, and exposes the same manual
receipt controls.

This separation improves local development and failure tolerance:

- Domain and browser work do not require paid API calls.
- CI does not require credentials.
- A provider outage does not make calculation or PDF generation unhealthy.

## Deterministic tests versus external evaluation

Normal tests use a fake parser. They prove how Checkmate handles known parser
results and failures.

Adapter contract tests use synthetic response objects to verify translation
between the SDK and application-owned models.

The opt-in `external` evaluation answers a different question: how well does
the selected model and prompt transcribe representative receipts? It uses 12
generated fixtures, requires a real credential, and runs only when explicitly
requested.

```text
Normal CI
  - deterministic
  - no network
  - no API cost
  - fake parser

External evaluation
  - probabilistic
  - real provider
  - explicit cost
  - required for model or prompt changes
```

Provider output should never become a normal CI release gate because network
availability and probabilistic variation are outside source-code correctness.

## Privacy implications

Receipt images and extracted text are sensitive request data:

- The UI tells the user before the upload is sent to OpenAI.
- The API key stays on the server.
- Image bytes and provider response content are excluded from logs.
- Tests and documentation use generated receipts and fictional identities.
- No claim of zero provider retention is made unless the deployed OpenAI
  project is separately configured and approved for it.

## Implications for implementation tasks

A practical extraction milestone is:

1. Define application-owned normalized-image and extraction-result models.
2. Define `ReceiptParser` and a deterministic fake.
3. Implement bounded upload reading and format rejection.
4. Implement safe Pillow decode and normalization, including primary-frame-only
   handling for the approved iPhone MPO/JPEG compatibility case.
5. Define the private provider schema and prompt version.
6. Implement the OpenAI adapter with timeout, retry, and semaphore behavior.
7. Map failures to safe application and HTTP errors.
8. Connect successful extraction to editable browser state.
9. Add synthetic unit, adapter, HTTP, and browser tests.
10. Run and record the opt-in external evaluation before merging the adapter.

## Review checklist

- Is the filename or declared media type ever trusted as proof of format?
- Are both encoded size and decoded dimensions bounded?
- Is source metadata removed during normalization?
- Does an iPhone MPO/JPEG contribute only its primary frame while every other
  multi-frame input remains rejected?
- Can provider output bypass ordinary domain validation?
- Are SDK types contained inside the adapter?
- Are timeout, retry, and concurrency policies explicit?
- Does every failure preserve manual entry?
- Can normal CI run without a network or API key?
