# Aura startup guide

<!-- aura-startup:start -->
## Supported local startup

Aura is a private local application with no sign-in. Its default API bind is
`127.0.0.1`; keep that loopback boundary for normal use. Commands below run from
the repository root and work in Linux/macOS shells or PowerShell.

### Explicit setup

Setup is separate from startup. Run it when first preparing or intentionally
updating the checked-out environment:

<!-- aura-setup-command -->
```bash
uv sync --locked
```

<!-- aura-setup-command -->
```bash
npm ci
```

Neither the runtime nor its wrapper scripts installs, synchronizes, downloads,
changes permissions, edits configuration, or kills an existing process.

`.env.example` selects local Ollama without a credential. Copy it to `.env` only
to customize settings. Gemini and OpenRouter are optional cloud providers: select
one explicitly and supply its credential privately. There is no silent cloud
fallback. The configured selected model must already exist at the selected
provider; Aura does not download it.

### Report-only preflight

<!-- aura-runtime-command -->
```bash
uv run --locked --no-sync python -m aura_backend.runtime preflight
```

The command returns one JSON report covering Python, uv, Node, npm, both lock
contracts, provider configuration, port availability, writable existing storage,
the selected provider service and selected model, and the application factory.
The provider rows are a bounded live provider check; the deterministic test suite
does not need a running model.

The aggregate status and process exit code are:

| Status | Exit | Meaning |
|---|---:|---|
| `pass` | 0 | Every required check passed; startup is licensed. |
| `missing` | 2 | A required command, lock, path, or selected model is absent. |
| `failed` | 3 | A check ran and failed, including an unavailable selected service. |
| `blocked` | 4 | Configuration, port use, identity, or readiness blocks startup. |
| `not_run` | 5 | A prerequisite prevented the check from running. |
| `not_applicable` | 6 | The check cannot apply in the observed environment. |

The report exposes fixed codes and safe values, not secrets, prompts, file
contents, or source exceptions. A non-pass result is not readiness. Follow its
remediation code explicitly, then rerun preflight.

### Serve

<!-- aura-runtime-command -->
```bash
uv run --locked --no-sync python -m aura_backend.runtime serve
```

`serve` repeats preflight, starts only its own backend/frontend children, waits
for the backend `/ready` contract, and propagates failure. Ctrl+C/SIGTERM cleans
up only locally owned children and provider sessions. Local cancellation cannot
guarantee stopped remote compute or billing at a cloud provider.

These wrappers are convenience delegates, not alternative lifecycle systems:

- `./start_full_system.sh` or `start_full_system.bat` — full serve
- `./aura_backend/start_api.sh` — `serve --backend-only`
- `./aura_backend/start_frontend.sh` — `serve --frontend-only`
- `./aura_backend/start_mcp.sh` — standalone optional MCP process; not included
  in normal Aura readiness

For explicit LAN use, pass a non-loopback `--host`. The runtime prints an
explicit LAN warning because Aura has no sign-in. Do not expose it directly to
the internet.

After readiness, use <http://localhost:5173> for the UI,
<http://localhost:8000> for the API, and <http://localhost:8000/docs> for local
API documentation. A live result describes only the selected provider/model in
the current environment; environment-blocked checks and skipped live lanes must
be reported as such, not as success.
<!-- aura-startup:end -->

## Troubleshooting boundaries

- `port_unavailable`: stop the process you own or choose another port with
  `serve --port PORT`; Aura never kills an unknown process.
- `storage_path_missing` / `storage_not_writable`: create or choose a storage
  path explicitly. Preflight never creates or edits storage.
- `provider_service_unavailable`: start the provider you selected, then rerun
  preflight.
- `provider_model_missing`: install the selected model explicitly through that
  provider, then rerun preflight.
- `provider_configuration_invalid`: review only the recognized settings in
  `.env.example`; unknown provider selection fails closed.

Legacy MCP internals, storage migration, emotional-quality claims, packaging,
and remote deployment instructions belong to later rehabilitation phases. This
guide intentionally makes no readiness claim for those areas.
