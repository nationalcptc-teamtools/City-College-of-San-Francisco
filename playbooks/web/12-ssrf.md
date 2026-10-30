*Draft: command steps not filled in yet.*

# 12. Server-Side Request Forgery (SSRF)

- **Phase:** No credentials or Low credentials (wherever the feature is)
- **Risk:** 🟡 Noisy: the client's server makes requests we choose. Reading cloud metadata can expose live keys: stop at proof, pass keys to the team and don't use them without approval.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** Burp Suite
- **You need:** a feature that fetches or renders something we control (a URL field, a PDF or report generator)

## What it is
The server fetches a URL or file for the user without checking where it points, so an attacker can make it reach internal systems, local files, or the cloud metadata service that hands out keys.

In 2024 a report generator that turned user input into a PDF ran our script on the server. The PDF came back with a system file in it, and then with cloud keys.

**Fix to recommend:** allow-list the hosts and URL schemes the server may fetch; check what comes back before returning it.

## Commands
A vulnerability was found in a comments field on a web page by inserting some javascript into the form using

```
<script>x=new XMLHttpRequest;x.onload=function(){document.write(this.responseText)};x.open("$TYPE$","$PAYLOAD$");x.send();
</script>
```

Where TYPE might be GET, POST, PUT, etc, and PAYLOAD would be something like a file `file:///etc/passwd`


## Evidence to capture
- `evidence/F-NNN-01.png`: the input field with the test input.
- `evidence/F-NNN-02.png`: the result showing data from inside the server, secrets redacted.

## Practice
- PortSwigger Web Security Academy, SSRF labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
