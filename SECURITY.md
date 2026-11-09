# Security Policy

## Supported versions

Security fixes are released against the latest published version of pystrip on
PyPI.

## Reporting a vulnerability

Please report security issues privately rather than in a public issue.

- Use GitHub's [private vulnerability reporting](https://github.com/pystrip/pystrip/security/advisories/new)
  for this repository, or
- email the maintainer at `alex.garrido@protonmail.com`.

Include a minimal reproduction and the affected version. You can expect an
acknowledgement within a few days. Once a fix is available, it will be released
and the advisory published.

## Scope

pystrip reads and rewrites Python source. The most relevant risks are a strip
that removes code it should not, or malformed output. Reproductions that show
pystrip changing program behaviour are especially valuable.
