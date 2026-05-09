## 1. Target Scripts

- [x] 1.1 Add workspace-local frontend target resolution for manual/stable and test targets.
- [x] 1.2 Add lifecycle probe and monitor logging for fixed frontend targets.
- [x] 1.3 Add a Next-aware dedicated test frontend launcher for port 4180.

## 2. E2E Integration

- [x] 2.1 Add Playwright configuration and smoke tests for the resolved frontend target.
- [x] 2.2 Add frontend package scripts and Playwright dev dependency.

## 3. Validation

- [x] 3.1 Run frontend build validation.
- [x] 3.2 Run E2E smoke validation against the dedicated test target.
- [x] 3.3 Stop the wrong-workspace 4180 process if present and start the harness test frontend.
