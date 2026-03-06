# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |

Only the latest minor release receives security patches. Users should always run the most recent version.

## Reporting a Vulnerability

If you discover a security vulnerability in audit-trail, please report it responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email your findings to the maintainers with the subject line: `[SECURITY] audit-trail vulnerability report`
2. Include a description of the vulnerability, steps to reproduce, and the potential impact.
3. If possible, include a suggested fix or mitigation.

### What to Expect

- **Acknowledgement**: We will acknowledge receipt of your report within 48 hours.
- **Assessment**: We will investigate and assess the severity within 7 days.
- **Fix timeline**: Critical vulnerabilities will be patched as soon as possible, typically within 14 days. Lower-severity issues will be addressed in the next scheduled release.
- **Disclosure**: We will coordinate with you on public disclosure timing. We ask that you allow us reasonable time to address the issue before any public disclosure.

### Scope

The following are in scope for security reports:

- Authentication and authorization bypasses
- Hash chain integrity violations or tampering vectors
- SQL injection, command injection, or other injection attacks
- Sensitive data exposure in API responses or logs
- Denial of service vulnerabilities in API endpoints

### Out of Scope

- Vulnerabilities in dependencies (report these to the upstream project)
- Issues requiring physical access to the server
- Social engineering attacks

## Security Considerations

audit-trail is designed for tamper-evident audit logging. The hash chain mechanism ensures that any modification to historical events is detectable. However, operators are responsible for:

- Securing the PostgreSQL database with proper access controls
- Using TLS for all API traffic in production
- Rotating JWT signing keys periodically
- Configuring appropriate retention policies
- Running the service with least-privilege permissions
