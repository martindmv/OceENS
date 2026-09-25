# OcéEns

EPF's course evaluation platform: surveys (*sondages*) are created per program, students answer them, and the answers are exported, visualised and summarised (*synthèses*).

## Language

The documentation, the code's identifiers, the issues and the ADRs are in English. The application itself is in French: its interface, its log messages, and the product vocabulary that comes from it stay in French wherever they name something in the product, such as *sondage* (a survey) and *synthèse* (an LLM summary of free-text answers). Use the French word when you quote the interface or a table; use the English one everywhere else.

### Authentication

**Development sign-in** (`AUTH_MODE=dev`):
Sign-in without an identity provider: you pick a user's e-mail address and are signed in as them, with no proof of identity. It only exists when `AUTH_MODE=dev` and must never be used in production.
_Avoid_: impersonation, spoofing, fake login
