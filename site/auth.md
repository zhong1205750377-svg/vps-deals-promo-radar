# VPS Price Watch auth.md

## Agent audience and scope
This service offers anonymous machine registration for read-only access to already-public content. It does not authenticate a human, expose private account data, accept orders or grant write permissions.

## Agent registration metadata
agent_auth: anonymous
register_uri: https://vpspricewatch.com/oauth/register
identity_types_supported: anonymous
credential_types_supported: oauth2_client_credentials
claim_uri: https://vpspricewatch.com/oauth/register

## Registration
POST /oauth/register with Content-Type: application/json and {"grant_types":["client_credentials"],"scope":"content:read","token_endpoint_auth_method":"client_secret_post"}. The response returns client_id and client_secret. Keep the secret private. It expires after 24 hours; register again after expiry. No email or payment is required.

## Credential use
POST /oauth/token with application/x-www-form-urlencoded fields grant_type=client_credentials, client_id, client_secret and scope=content:read. Send the returned access_token only in Authorization: Bearer on GET /api/agent/content?q=namesilo. Access tokens expire after 600 seconds and use RS256 signatures. Public verification keys are at /.well-known/jwks.json. No refresh token, user authorization grant or early credential revocation endpoint is offered. Rotating the signing key invalidates existing credentials.

## Public alternative
GET /api/content?q=namesilo needs no credential. Both routes search published snapshots and preserve source page links. They do not verify current checkout availability.
