# Cloudflare Travel Launch Checklist

Complete this checklist with the owner signed in to Cloudflare. Do not paste a
tunnel token, Access cookie, API key, account ID, or screenshot containing
credentials into Git, chat, or task evidence.

The canonical hostname currently has no public DNS record. The existing `www`
hostname does have public records and must not be replaced.

## 1. Record existing site state

In the Cloudflare dashboard for `rishabhtamhane.com`, privately record:

- the current `www` DNS record and whether it is proxied;
- existing Redirect Rules, Page Rules, Workers routes, and Transform Rules;
- the current edge-certificate status; and
- the current zone plan and available rate-limit settings.

Do not modify the `www` DNS record.

## 2. Prepare the Mac

The current preflight found that `cloudflared` is not installed. Install it
through Cloudflare's supported Homebrew path, then record the installed version:

```bash
brew install cloudflared
cloudflared --version
```

Do not create a quick tunnel; its hostname and availability contract are for
testing only.

## 3. Create the connector without publishing a hostname

In Cloudflare, go to **Networking → Tunnels**, create a Cloudflared tunnel named
`checkmate-mac`, and select the macOS arm64 connector instructions.

The dashboard displays a secret tunnel token. Enter it through a hidden prompt
so the literal value does not enter shell history:

```bash
printf "Paste the Cloudflare tunnel token: "
IFS= read -r -s CLOUDFLARED_TOKEN
printf "\n"
sudo cloudflared service install "$CLOUDFLARED_TOKEN"
unset CLOUDFLARED_TOKEN
```

Return to the dashboard and confirm the connector is healthy. Do not add the
public hostname yet.

## 4. Create Access before publishing

In **Zero Trust → Access controls → Applications**:

1. Create a **Self-hosted** application for the exact hostname
   `checkmate.rishabhtamhane.com`.
2. Use a 24-hour session duration for the travel preview.
3. Enable one-time PIN as an identity provider.
4. Add an **Allow** policy whose Include selector is the owner's exact email
   address.
5. Require the one-time-PIN login method.

Never select **Everyone** and never use one-time PIN as an unrestricted Include
selector. Add invited testers only as individual email addresses.

## 5. Configure edge protections before publishing

Create a rate-limiting rule matching:

```text
http.host eq "checkmate.rishabhtamhane.com"
and http.request.method eq "POST"
and http.request.uri.path eq "/api/receipts/extract"
```

Use five requests per minute per source IP and a ten-minute mitigation timeout
when the zone plan offers those values. If the plan cannot provide an
equivalent rule, stop before publishing and revise the design.

Create a response-header Transform Rule matching only:

```text
http.host eq "checkmate.rishabhtamhane.com"
```

Set this response header:

```text
Strict-Transport-Security: max-age=31536000
```

Do not enable `includeSubDomains`, preload, or zone-wide HSTS as part of this
launch. Confirm the OpenAI project has a budget or usage alert.

## 6. Publish the named route

In the `checkmate-mac` tunnel, add a Published application route:

```text
Hostname: checkmate.rishabhtamhane.com
Service:  http://localhost:8080
```

Retain the tunnel's catch-all 404 behavior. The tunnel creates the proxied DNS
record; do not create an A record pointing at the home Internet address.

Open the canonical URL in a private browser window. The first response must be
the Cloudflare Access login, not the Checkmate page. If Checkmate is visible
without authentication, remove or disable the published route immediately and
repair Access before continuing.

## 7. Verify from the iPhone

With Wi-Fi disabled:

1. Open `https://checkmate.rishabhtamhane.com/`.
2. Authenticate using the allowlisted email and one-time PIN.
3. Confirm the page and CSS load without a mixed-content warning.
4. Enter a synthetic bill, calculate it, and download its PDF.
5. Upload one synthetic receipt only if the owner chooses to spend the paid
   extraction request.
6. Confirm a private browser without an allowed session receives Access rather
   than the application.

## 8. Add the portfolio redirect last

After both the portfolio and canonical app pass verification, create one
temporary Single Redirect matching only:

```text
http.host eq "www.rishabhtamhane.com"
and http.request.uri.path in {"/checkmate" "/checkmate/"}
```

Redirect to `https://checkmate.rishabhtamhane.com/` with status 302. Preserve
query parameters if Cloudflare presents that option. Verify the portfolio root
and an unrelated path remain unchanged. Promote the rule to 301 only after
owner acceptance.

## Official references

- <https://developers.cloudflare.com/tunnel/setup/>
- <https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/macos/>
- <https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/>
- <https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/>
- <https://developers.cloudflare.com/waf/rate-limiting-rules/>
- <https://developers.cloudflare.com/rules/url-forwarding/>
- <https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/>
