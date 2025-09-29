# Security Policy

## Supported Versions

We provide security updates for the following versions of HypeRate Python:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Yes             |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

We take the security of HypeRate Python seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please DO NOT report security vulnerabilities through public GitHub issues.

Instead, please report them responsibly by using one of the following methods:

### 🔒 Private Security Reporting (Preferred)

1. Go to the **Security** tab in the [HypeRate Python repository](https://github.com/Serpensin/HypeRate-Python)
2. Click on **"Report a vulnerability"**
3. Fill out the security advisory form with as much detail as possible

### 📧 Email Reporting

Send an email to: **[serpensin@protonmail.com](mailto:serpensin@protonmail.com)**

Include the word "SECURITY" in the subject line and provide:
- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fixes or mitigations

## What to Include in Your Report

Please include as much of the following information as possible:

- **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- **Full paths of source file(s)** related to the manifestation of the issue
- **The location of the affected source code** (tag/branch/commit or direct URL)
- **Any special configuration** required to reproduce the issue
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit the issue

## Response Timeline

We will acknowledge receipt of your vulnerability report within **48 hours** and will send a more detailed response within **7 days** indicating the next steps in handling your report.

After the initial reply to your report, we will endeavor to keep you informed of the progress being made towards a fix and full announcement, and may ask for additional information or guidance surrounding the reported issue.

## Disclosure Policy

- We will investigate and validate the security issue
- We will work on a fix for the vulnerability
- We will prepare a security advisory
- We will coordinate the release of the fix
- We will publicly disclose the vulnerability in a responsible manner

### Timeline for Disclosure

- **Day 0**: Vulnerability reported
- **Day 1-7**: Initial assessment and acknowledgment
- **Day 7-30**: Investigation and fix development
- **Day 30+**: Coordinated disclosure (may be extended if needed)

## Security Measures

### Code Security

- All code is reviewed before merging
- Dependencies are regularly updated and scanned for vulnerabilities
- Static analysis tools are used in the CI/CD pipeline
- Type checking with mypy helps prevent certain classes of vulnerabilities

### API Security

- Input validation is performed on all user inputs
- Proper error handling prevents information leakage
- No sensitive information is logged or exposed in error messages
- WebSocket connections use secure practices

### Infrastructure Security

- GitHub Actions workflows use pinned versions
- Secrets are properly managed using GitHub Secrets
- PyPI publishing uses token-based authentication
- All communications use HTTPS/WSS

## Security Best Practices for Users

When using HypeRate Python in your applications:

1. **Keep Dependencies Updated**: Regularly update to the latest version
2. **Validate Input**: Always validate data received from the API
3. **Handle Errors Gracefully**: Don't expose sensitive information in error handling
4. **Use Environment Variables**: Store sensitive configuration in environment variables
5. **Monitor for Updates**: Watch the repository for security updates

## Scope

This security policy applies to:

- The HypeRate Python library code
- Documentation and examples
- CI/CD workflows and infrastructure
- Dependencies and their security

This policy does NOT cover:

- The HypeRate API service itself (report to HypeRate directly)
- Third-party applications using this library
- Security issues in dependencies (unless they affect this library specifically)

## Recognition

We appreciate the efforts of security researchers and will acknowledge your contribution to the security of HypeRate Python:

- We will publicly thank you (if desired) after the vulnerability is disclosed
- Your name will be included in the security advisory (if you wish)
- We will work with you on the disclosure timeline

## Contact

For any questions about this security policy, please contact:

- **Email**: [serpensin@protonmail.com](mailto:serpensin@protonmail.com)
- **GitHub**: [@Serpensin](https://github.com/Serpensin)

---

Thank you for helping keep HypeRate Python secure! 🔒