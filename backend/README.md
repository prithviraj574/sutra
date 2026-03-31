# Sutra Backend

FastAPI control plane for Sutra.

This package is intentionally separate from the Hermes submodule. Hermes remains the
runtime engine; this backend owns tenancy, auth, persistence, orchestration, and
runtime policy.