# System Architecture Guide

## Status

Approved.

Approval date: 2026-08-18.

## Document role

This guide explains the architecture proposed in
[`../02-mvp-implementation.md`](../02-mvp-implementation.md). The parent
document remains authoritative. This status records review of this design area;
it does not approve the overall workstream. If the two documents disagree,
follow the parent and correct this guide.

Read this guide when working on application structure, HTTP routes, dependency
direction, configuration, or the initial web process.

## The system in one sentence

Checkmate is one stateless Python web application: the browser owns the current
editable draft, FastAPI receives requests, application services coordinate the
work, deterministic domain code calculates the split, and adapters communicate
with external systems.

```text
Browser
   |
   | HTTP
   v
FastAPI web layer
   |
   v
Application services
   |
   +-----------------------> Domain calculation
   |
   +----> ReceiptParser ---> OpenAI
   |
   `----> PdfRenderer -----> PDF bytes
```

There is deliberately no database, server-side session, message queue, or
background worker in v0.1.

## How the browser reaches Python

The browser speaks HTTP. FastAPI is the Python framework that describes which
function handles each URL. Uvicorn is the server process that listens for HTTP
connections. ASGI is the standard contract Uvicorn and FastAPI use to exchange
requests and responses.

```text
Browser request
      |
      v
Uvicorn HTTP server
      |
      | ASGI request messages
      v
FastAPI application
      |
      | ASGI response messages
      v
Uvicorn sends HTTP response
```

Application code normally does not implement ASGI directly. FastAPI constructs
the ASGI application and Uvicorn runs it.

## One user journey, several independent requests

Opening the page does not create a permanent server-side Checkmate session.
Instead, the browser makes separate requests as the user progresses.

```text
1. GET  /
   Response: HTML, with links to local CSS and JavaScript

2. POST /api/receipts/extract
   Request:  one receipt image
   Response: an editable receipt draft or a safe extraction error

3. POST /api/splits/calculate
   Request:  the complete current draft
   Response: issues, reconciliation values, and calculated totals

4. POST /api/splits/pdf
   Request:  the complete current draft
   Response: PDF bytes, but only when server validation succeeds

5. GET /health
   Response: process status for people and deployment systems
```

Every calculation and PDF request contains the complete draft. The server does
not need to remember what happened in an earlier request.

### Example

Suppose a user adds Maya after already entering a receipt. The browser updates
its local `draft` and sends the whole receipt, all participants, and all
assignments to the calculation endpoint. The server calculates only from that
request. It does not look up a previous receipt or modify stored state.

This has important consequences:

- Refreshing the page loses the draft, as the requirements allow.
- Any identical valid request produces the same calculation result.
- Multiple container replicas can handle requests without sharing session data.
- HTTP tests can describe a complete scenario without preparing a database.

## The four application layers

### Domain

The domain contains the rules that make Checkmate correct:

- Parse and format money safely.
- Validate receipts, participants, and assignments.
- Divide shared items.
- Allocate tax and tip.
- Reconcile the calculated and entered totals.

It uses standard-library types and must not import FastAPI, OpenAI, ReportLab,
or browser concerns.

### Application

The application layer describes use cases and coordinates dependencies. It
answers questions such as:

- What must happen when a receipt is extracted?
- What must happen before a PDF can be rendered?
- How does a parser failure become an application failure?

It declares narrow protocols such as `ReceiptParser` and `PdfRenderer`. It does
not know which vendor implements them.

### Adapters

Adapters translate between Checkmate and external technology:

- `OpenAIReceiptParser` converts normalized image input into an
  application-owned extraction result.
- `ReportLabPdfRenderer` converts a finalized split into PDF bytes.
- Test fakes implement the same protocols without network calls or complex
  rendering.

An adapter may import a vendor SDK. Vendor objects must stop at this boundary.

### Web

The web layer owns HTTP and browser presentation:

- FastAPI routes
- Pydantic request and response schemas
- Status codes and response headers
- Jinja templates
- Static CSS and JavaScript
- Conversion between HTTP data and application inputs

The web layer may report a domain issue, but it must not reimplement the rule
that produced it.

## Dependency direction

Dependencies point toward stable business policy:

```text
web --------> application --------> domain
  \                 ^
   \                |
    `----------> adapters
```

More precisely, the web composition root constructs adapter instances and
passes them to application services. The application layer depends only on the
protocol, while the concrete adapter depends on that protocol.

### Why this matters

Without this separation, a calculation test might need FastAPI or an OpenAI
credential. With it, a unit test can call a plain Python function:

```python
result = calculate_split(split_input)
```

Similarly, an application test can inject a fake:

```python
service = ReceiptService(parser=FakeReceiptParser(expected_result))
```

The test proves orchestration without paying for a network request.

## Composition root

`web.app` is the composition root: the one place where concrete parts are
assembled.

At startup it will conceptually:

1. Read and validate environment configuration.
2. Create the OpenAI parser when an API key is configured, otherwise select the
   manual-entry behavior.
3. Create the ReportLab renderer.
4. Create application services with those dependencies.
5. Register FastAPI routes that call the services.

Keeping construction in one place prevents hidden global dependencies from
appearing throughout the package.

## Boundary models versus domain models

The web and provider boundaries accept imperfect data. A user can temporarily
leave a money input blank, and an extraction provider can omit a date. Domain
calculation must not receive malformed values.

```text
Raw JSON strings
      |
      v
Pydantic boundary shape
      |
      v
Validation and conversion
      |
      v
Valid domain values
```

Pydantic proves that an HTTP or provider payload has the expected structure.
Domain validation proves that the values are meaningful for Checkmate. These
are related but different responsibilities.

## Error ownership

Errors are translated at the nearest boundary that understands both sides:

- The domain produces structured validation issues, not HTTP status codes.
- The application maps adapter failures into application error categories.
- The web layer maps those categories to safe HTTP responses.
- The browser presents actionable messages without exposing internal details.

For example, the domain should not know what HTTP `422` means, and the OpenAI
adapter should not create a FastAPI response.

## Implications for implementation tasks

Architecture tasks should establish boundaries before adding external
adapters. A practical order is:

1. Create the package directories and dependency rules.
2. Add configuration and the application composition root.
3. Serve `/` and `/health` from FastAPI.
4. Define application protocols and request-independent models.
5. Implement the deterministic domain before connecting OpenAI or PDF output.
6. Add adapters behind their protocols.
7. Verify imports point in the allowed direction.

Each task should name the layer it changes and include a focused test at the
same boundary.

## Review checklist

- Can domain tests run without FastAPI and third-party services?
- Can application tests replace the parser and renderer with fakes?
- Are vendor SDK objects contained inside adapters?
- Does every calculation request contain the complete draft?
- Is there any accidental persistence or server-side session state?
- Is construction of concrete dependencies centralized?
- Does the browser avoid implementing monetary policy?
