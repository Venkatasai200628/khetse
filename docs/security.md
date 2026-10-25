# Security Policy

How the KhetSe backend protects accounts, money, data and privacy. This
document describes what is **implemented today**; anything listed under
[Planned](#planned) is explicitly not yet enforced.

## Authentication & sessions

- Phone + OTP login; there are no passwords anywhere in the system.
- OTPs are stored **hashed** (HMAC with a server-side secret), never in
  plain text, and expire after `OTP_EXPIRE_SECONDS`.
- OTP verification is rate-limited: `OTP_MAX_ATTEMPTS` wrong entries per
  code, `OTP_RATE_LIMIT_PER_HOUR` requests per phone per hour.
- Sessions are short-lived JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES`) signed
  with `JWT_SECRET` (HS256).
- Registration tokens issued after OTP verification are single-purpose
  JWTs of a distinct token type; they cannot be replayed as session
  tokens.
- Development OTPs (`dev_otp` in the response) are only returned when
  `SMS_PROVIDER=mock` **and** demo mode is on, which is force-disabled
  when `ENV=production`.

## Secrets

- Secrets live only in `.env` at the repository root, which is
  git-ignored (`.env.example` is the committed template).
- The application **refuses to start in production** when `JWT_SECRET`
  is a known placeholder or shorter than 32 characters. Generate one with:

  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

- Demo features (demo login, simulated payments/SMS) are automatically
  disabled when `ENV=production`.

## Authorization

- Role-based access control is enforced **server-side on every
  endpoint** (`require_roles` dependency): farmer, buyer, business,
  driver, FPO operator, admin.
- Admin and FPO-operator accounts cannot be self-registered; they are
  provisioned by administrators.
- Resource ownership is re-checked in the service layer, not just the
  router: buyers see only their own carts and orders; farmers manage
  only their own listings; order details are visible only to the buyer,
  the farmers with lines in the order, their FPO operator, and admins.
- An FPO operator may respond to orders only on behalf of farmers who
  are members of their own FPO (`FarmerProfile.fpo_id`).

## Money handling

- All amounts are stored and computed as **integer paise** (₹1 = 100);
  there is no floating-point arithmetic in financial code.
- Percentages and fees are resolved from the `platform_settings` table
  at calculation time and are type-checked on write.
- Checkout is **idempotent**: a retry with the same idempotency key
  returns the original order, and a key belonging to another buyer is
  rejected with 409 — order details are never leaked across accounts.
- Overselling is impossible: listing rows are locked at checkout,
  availability is re-checked, and the reserved quantity can never exceed
  the total.
- Order state changes go through an explicit state machine; every
  transition is validated against the allowed graph and recorded as an
  audit event with actor, timestamp and reason.

## Privacy

- Buyers never see exact farm coordinates — only the farmer's
  village/district. Coordinates are visible solely to the owning farmer
  and used server-side for delivery-fee calculation and logistics.
- Payment settlement is tracked separately from delivery status
  (`Order.payment_status`), so a delivered order is never mistaken for a
  paid one.

## Error handling & disclosure

- Error responses have a single, consistent shape and never include
  stack traces, SQL or internal details; unexpected errors are logged
  server-side and returned as a generic 500.
- Input validation (Pydantic) runs before any database access; phone
  numbers are normalised and pattern-checked.

## Payments

- There is no real payment provider wired up yet. The only capture path is
  the mock `POST /orders/{id}/pay` endpoint, which is **enabled only while
  demo mode is on** (and demo mode is force-disabled in production).
- The production capture path — `POST /payments/webhook` — is shipped as a
  stub: it is disabled (503) until `RAZORPAY_WEBHOOK_SECRET` is configured,
  verifies the provider's HMAC-SHA256 body signature on every delivery
  (401 otherwise), applies the same state-machine capture
  (PAYMENT_PENDING → CONFIRMED) and acknowledges replayed deliveries
  idempotently.

## Planned

Not yet implemented — tracked for the payments and logistics milestones:

- Real payment-provider integrations (order creation, capture, refunds)
  behind the webhook stub.
- Generic rate limiting middleware on sensitive endpoints beyond OTP.
- Audit-log entries for admin/financial actions (the `audit_logs` table
  exists; writing to it is not yet wired).
- Refresh tokens / session revocation.
