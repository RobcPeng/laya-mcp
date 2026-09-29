"""Generate the security-incident-triage accelerator set (deterministic, stdlib only).

Each family is one alert scenario (a detection rule plus the facts around it) with fixed gold: category,
whether it is a true positive, severity, and escalation. Most categories have a malicious family, a
low-impact real family, and a false-positive look-alike (authorized scanner, load test, phishing
simulation, approved travel, backup job, EICAR test). Alerts render in one of five formats (key/value,
JSON, syslog, SOC analyst note, ticket) with a vendor severity that is often wrong, as real tools are.

    python datasets/accelerators/security-incident-triage/generate.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "security-incident-triage"
PREFIX = "sec"
PER_FAMILY = 26
SEED = 4242

DEPTS = ["FIN", "HR", "ENG", "OPS", "SALES", "LEGAL", "IT", "CLERK", "PD", "DMV", "HLTH", "PW"]
EXT_IPS = [f"203.0.113.{i}" for i in range(2, 250, 7)] + [f"198.51.100.{i}" for i in range(3, 250, 11)]
BAD_DOMAINS = ["examp1e-login.com", "secure-examplemail.net", "exarnple-sso.org", "login-example.co",
               "update-portal-example.net", "cdn-sync-example.info", "files-example-share.biz"]
COUNTRIES = ["Country A", "Country B", "Country C", "Region X", "Region Y"]
CITIES = ["Denver", "Austin", "Boise", "Phoenix", "Toronto", "Lisbon", "Singapore", "Frankfurt", "Lagos",
          "Sao Paulo", "Seoul", "Warsaw"]


def host(rng, kind=None):
    kind = kind or C.pick(rng, ["WS", "LT", "SRV", "VM"])
    return f"{kind}-{C.pick(rng, DEPTS)}-{rng.randrange(1, 400):03d}"


def user(rng):
    f, l = C.pick(rng, C.FIRST), C.pick(rng, C.LAST)
    return C.pick(rng, [f"{f[0].lower()}.{l.lower()}", f"{f.lower()}.{l.lower()}", f"{l.lower()}{f[0].lower()}",
                        f"{f.lower()}_{l.lower()}"])


def int_ip(rng):
    return f"10.{rng.randrange(0, 60)}.{rng.randrange(0, 255)}.{rng.randrange(2, 254)}"


SLOTS = {
    "host": host, "srv": lambda r: host(r, "SRV"), "user": user, "ext_ip": EXT_IPS, "int_ip": int_ip,
    "bad_domain": BAD_DOMAINS, "city": CITIES, "country": COUNTRIES,
    "n_small": lambda r: str(r.randrange(3, 40)), "n_big": lambda r: f"{r.randrange(200, 9000):,}",
    "gb": lambda r: str(r.randrange(4, 80)), "mins": lambda r: str(r.randrange(2, 55)),
    "chg": lambda r: f"CHG-{r.randrange(10000, 99999)}", "port": ["445", "3389", "22", "5985", "135"],
    "ext": [".locked", ".crypt", ".enc9", ".payme"], "proc": ["powershell.exe", "rundll32.exe", "mshta.exe",
                                                             "wscript.exe", "regsvr32.exe"],
    "parent": ["WINWORD.EXE", "EXCEL.EXE", "OUTLOOK.EXE", "AcroRd32.exe", "chrome.exe"],
    "bucket": lambda r: f"{C.pick(r, ['cust', 'records', 'exports', 'citizen', 'claims', 'hr'])}-"
                        f"{C.pick(r, ['data', 'backup', 'share', 'archive'])}-{r.randrange(10, 99)}",
    "saas": ["FileDropper", "QuickShareBox", "PasteNest", "SyncBarn", "NoteCloudy"],
    "tool": ["uTorrent-like client", "unlicensed PDF editor", "remote desktop freeware", "browser VPN extension",
             "game launcher"],
    "cve": lambda r: f"CVE-2026-{r.randrange(1000, 49999)}",
    "vendor": ["an approved awareness-training vendor", "the security team's simulation platform"],
}

# (category, family, true_positive, severity 0-4, [ (rule, summary template, context template) ... ])
# needs_escalation = true_positive and severity >= 3
FAMILIES = [
    # ---------------------------------------------------------------- malware
    ("malware", "malware/ransomware", True, 4, [
        ("Mass file modification", "{n_big} files on {srv} renamed with extension {ext} in {mins} minutes; "
         "vssadmin.exe delete shadows /all /quiet executed by {user}.", "Ransom note README_RESTORE.txt found in 40+ shares."),
        ("Ransomware behavior", "Process on {host} encrypting network shares; shadow copies deleted; SMB writes to "
         "{n_small} servers.", "Help desk getting calls that files will not open."),
    ]),
    ("malware", "malware/macro-powershell", True, 3, [
        ("Suspicious child process", "{parent} spawned {proc} with an encoded command line on {host} (user {user}); "
         "process then connected to {ext_ip}:443.", "No known business reason; file came from an external email."),
        ("Office macro execution", "Macro in invoice.docm launched {proc} -> download from http://{bad_domain}/a.bin "
         "on {host}.", "Payload written to AppData and set to run at logon."),
    ]),
    ("malware", "malware/quarantined", True, 1, [
        ("Malware quarantined", "Adware bundle detected in Downloads on {host} ({user}) and quarantined before "
         "execution.", "No process ran; no network activity observed."),
        ("PUA blocked", "Potentially unwanted toolbar installer blocked on {host}.", "Endpoint agent remediated automatically."),
    ]),
    ("malware", "malware/fp-admin-tool", False, 0, [
        ("Remote execution tool", "PsExec-style service created on {srv} from jump host {host} by admin account "
         "{user}.", "Matches scheduled patch deployment {chg}; activity inside the approved window."),
        ("Suspicious script", "{proc} ran a signed inventory script on {n_small} hosts from the IT management "
         "server.", "Script hash matches the IT config repo; approved under {chg}."),
    ]),
    ("malware", "malware/fp-eicar", False, 0, [
        ("Malware detected", "EICAR test file detected on {host} by user {user}.",
         "Security team is validating endpoint coverage this week; ticket {chg}."),
    ]),
    # ---------------------------------------------------------------- phishing
    ("phishing", "phishing/cred-harvest-entered", True, 3, [
        ("Credential phishing click", "{user} clicked a link to https://{bad_domain}/sso and submitted credentials; "
         "a new sign-in from {ext_ip} followed {mins} minutes later.", "Same email delivered to {n_small} mailboxes."),
        ("Phish URL visited", "Proxy shows {user} POSTed a form to {bad_domain} imitating our login page.",
         "User confirmed they typed their password."),
    ]),
    ("phishing", "phishing/reported-blocked", True, 1, [
        ("User-reported phish", "{user} reported an email asking to 'confirm payroll details' linking to "
         "{bad_domain}.", "Nobody clicked; gateway purged the message from {n_small} inboxes."),
        ("Phish blocked", "Email gateway blocked {n_small} messages with a lure link to {bad_domain}.",
         "No clicks recorded."),
    ]),
    ("phishing", "phishing/simulation", False, 0, [
        ("Phish URL click", "{user} clicked a link in 'Action required: benefits update' sent from {vendor}.",
         "Part of this quarter's scheduled phishing simulation."),
        ("Suspicious email campaign", "{n_big} internal recipients got the same lure email; sender domain registered "
         "last week.", "Domain belongs to {vendor} running the approved awareness campaign."),
    ]),
    ("phishing", "phishing/bec-wire", True, 3, [
        ("Executive impersonation", "Email to accounts payable from 'the CFO' via {bad_domain} asks to change a "
         "vendor's bank account before today's payment run.", "Finance has not paid yet but the change was entered."),
        ("Payment redirection lure", "Reply-to mismatch: message claiming to be a contractor requests wire to a new "
         "account.", "{user} forwarded it to treasury asking to process it."),
    ]),
    # ---------------------------------------------------------------- account compromise
    ("account_compromise", "acct/impossible-travel-mfa", True, 3, [
        ("Impossible travel", "{user} signed in from {city} and {mins} minutes later from {ext_ip} ({country}); "
         "{n_small} MFA push prompts sent before one was approved.", "User says they did not approve any prompt."),
        ("MFA fatigue", "{n_small} MFA denials then an approval for {user} from a new device at 03:12.",
         "New inbox rule created to forward mail externally."),
    ]),
    ("account_compromise", "acct/spray-failed", True, 2, [
        ("Password spray", "{n_big} failed sign-ins across {n_small} accounts from {ext_ip} in {mins} minutes.",
         "No successful sign-ins from that address."),
        ("Brute force attempt", "Repeated failed logins to the VPN for {user} from {ext_ip}.", "Account locked out; no success."),
    ]),
    ("account_compromise", "acct/fp-travel", False, 0, [
        ("Impossible travel", "{user} signed in from {city} and then from {ext_ip} ({country}) within an hour.",
         "Second address is the corporate VPN egress; user is on approved travel."),
        ("Atypical sign-in location", "New country sign-in for {user}.", "HR travel calendar shows the conference trip; MFA passed on the known phone."),
    ]),
    ("account_compromise", "acct/admin-token-theft", True, 4, [
        ("Anomalous token", "Session token for global admin {user} reused from {ext_ip} on a new ASN; new app "
         "registration with mail.read for all users.", "Admin was asleep; token issued to a laptop at home."),
        ("Privilege escalation", "{user} added to Domain Admins by an account that signed in from {ext_ip}.",
         "Golden-ticket style Kerberos anomalies on {n_small} DCs."),
    ]),
    # ---------------------------------------------------------------- exfiltration
    ("data_exfiltration", "exfil/personal-cloud", True, 3, [
        ("Large upload to personal storage", "{user} uploaded {gb} GB to a personal cloud drive from {host} over "
         "two nights.", "HR lists {user} as resigning on Friday; files include customer lists."),
        ("DLP bulk transfer", "{n_big} files from the finance share synced to an unmanaged device.", "Device not enrolled; user is a contractor."),
    ]),
    ("data_exfiltration", "exfil/dns-tunnel", True, 3, [
        ("DNS tunneling", "{host} sent {n_big} TXT queries with long random subdomains of {bad_domain}.",
         "Query volume started after a new scheduled task appeared."),
        ("Beaconing and exfil", "{host} beaconing to {ext_ip} every 60s; outbound bytes {gb} GB overnight.", "Server normally sends under 1 GB a day."),
    ]),
    ("data_exfiltration", "exfil/fp-backup", False, 0, [
        ("Unusual outbound volume", "{srv} sent {gb} GB to {ext_ip} between 01:00 and 03:00.",
         "Destination is the contracted offsite backup provider; nightly job {chg}."),
        ("Large transfer", "Replication traffic from {srv} to the DR site spiked.", "Quarterly full backup scheduled tonight."),
    ]),
    ("data_exfiltration", "exfil/email-to-self", True, 2, [
        ("DLP: sensitive data to personal email", "{user} emailed a spreadsheet with {n_big} customer records to a "
         "personal address.", "User says they wanted to work from home; one-time event."),
        ("DLP policy match", "Attachment with 40 SSN-pattern matches sent externally by {user}.", "Recipient is a personal webmail address."),
    ]),
    # ---------------------------------------------------------------- recon
    ("reconnaissance", "recon/internet-noise", True, 0, [
        ("Port scan detected", "{ext_ip} scanned {n_small} public IPs on common ports.", "Firewall dropped everything; routine internet background noise."),
        ("Inbound scan", "Mass scanner probing TCP {port} on the perimeter.", "Blocked at the edge; no internal hits."),
    ]),
    ("reconnaissance", "recon/internal-lateral", True, 3, [
        ("Internal port sweep", "Workstation {host} ({user}) connected to TCP {port} on {n_big} internal hosts in "
         "{mins} minutes.", "Workstation is not an admin or scanner host."),
        ("SMB enumeration", "{host} enumerated shares and sessions on every domain controller.", "Tooling matches known post-exploitation kits."),
    ]),
    ("reconnaissance", "recon/fp-vuln-scanner", False, 0, [
        ("Port scan detected", "{int_ip} scanned {n_big} internal hosts on {n_small} ports.",
         "Source is the authorized vulnerability scanner; weekly scan {chg}."),
        ("Network sweep", "Discovery sweep across the server VLAN.", "Asset inventory tool on its normal schedule."),
    ]),
    ("reconnaissance", "recon/web-enum", True, 1, [
        ("Directory brute force", "WAF logged {n_big} requests from {ext_ip} for /admin, /.git, /backup.zip on the "
         "public portal.", "All returned 404 or 403."),
        ("Web crawler probing", "Automated requests testing for common CMS login paths.", "Rate limit engaged; nothing found."),
    ]),
    # ---------------------------------------------------------------- DoS
    ("denial_of_service", "dos/volumetric", True, 3, [
        ("SYN flood", "Public permit portal receiving {n_big}k packets/s from many sources; page loads timing out.",
         "Residents cannot submit applications."),
        ("HTTP flood", "Layer-7 flood against the payments API from {n_small}k IPs; error rate 60%.", "Customer checkout down."),
    ]),
    ("denial_of_service", "dos/fp-load-test", False, 0, [
        ("Traffic spike", "Requests to the staging API jumped to {n_big}/s from {int_ip}.",
         "QA load test announced in the change calendar ({chg})."),
        ("Possible DoS", "CPU pegged on {srv} from high request volume.", "Planned performance test run by the platform team."),
    ]),
    ("denial_of_service", "dos/rate-limited", True, 1, [
        ("Login endpoint flood", "Bot sending {n_big} login attempts per minute to the public site from {ext_ip}.",
         "Rate limiting and CAPTCHA absorbing it; no user impact."),
    ]),
    # ---------------------------------------------------------------- misconfiguration
    ("misconfiguration", "misconfig/public-bucket", True, 3, [
        ("Public storage", "Storage bucket {bucket} allows anonymous read; contains {n_big} files with names like "
         "applicants_*.csv.", "Access logs show downloads from {ext_ip}."),
        ("Exposed database", "Database on {srv} reachable from the internet without authentication.", "Holds case management records."),
    ]),
    ("misconfiguration", "misconfig/open-rdp", True, 2, [
        ("Exposed management port", "Test VM {host} has RDP ({port}) open to 0.0.0.0/0.", "No sign-ins yet; created by a developer last week."),
        ("Weak TLS settings", "Public site still accepts TLS 1.0 and weak ciphers.", "Found by external posture scan."),
    ]),
    ("misconfiguration", "misconfig/missing-patch", True, 2, [
        ("Missing critical patch", "{srv} missing the fix for {cve} (remote code execution).", "No exploitation seen; patch window is next Tuesday."),
    ]),
    ("misconfiguration", "misconfig/fp-public-site", False, 0, [
        ("Public storage", "Bucket {bucket} allows anonymous read.",
         "Bucket serves the public website images; documented exception {chg}."),
        ("Open port", "Port 443 open to the internet on the web server.", "Expected: it is the public website."),
    ]),
    # ---------------------------------------------------------------- policy
    ("policy_violation", "policy/unapproved-software", True, 1, [
        ("Unapproved software", "{tool} installed on {host} by {user}.", "Not on the approved software list."),
        ("Software policy", "Personal game launcher and {tool} found on a library kiosk.", "No malware detected."),
    ]),
    ("policy_violation", "policy/shadow-it", True, 1, [
        ("Unsanctioned SaaS", "{n_small} users in one department uploading work files to {saas}.", "Service is not approved; data type unknown."),
    ]),
    ("policy_violation", "policy/usb-restricted", True, 2, [
        ("Removable media", "USB mass storage mounted on restricted workstation {host}; {n_big} files copied.",
         "Station handles criminal justice data; USB is blocked by policy."),
    ]),
    ("policy_violation", "policy/fp-exception", False, 0, [
        ("Unapproved software", "{tool} installed on {host} by {user}.", "Approved exception on file ({chg}) for the research team."),
        ("Unsanctioned SaaS", "Uploads to {saas} from the comms team.", "Security review approved {saas} last month; allowlist not updated yet."),
    ]),
]


# Extra phrasings (appended to the families above) for lexical variety.
EXTRA = {
    "malware/ransomware": [("File encryption detected", "Canary files on {srv} modified; {n_big} documents now "
                            "unreadable, entropy spike on the file server.", "Backups for that share last ran two days ago.")],
    "malware/macro-powershell": [("Living-off-the-land binary", "{proc} on {host} fetched a script from {bad_domain} "
                                  "and injected into explorer.exe.", "User {user} opened a 'shipping label' attachment first.")],
    "malware/quarantined": [("Threat remediated", "Trojan dropper in a zip on {host} deleted on write.", "Never executed; full scan clean.")],
    "phishing/cred-harvest-entered": [("Suspicious sign-in after phish", "{user} opened the 'Voicemail received' email, "
                                       "entered credentials on {bad_domain}, and the account then logged in from {ext_ip}.",
                                       "Mailbox rules were changed shortly after.")],
    "phishing/reported-blocked": [("Phishing report", "Staff reported a fake invoice email with a link to {bad_domain}.",
                                   "Link was already on the blocklist; zero clicks.")],
    "acct/impossible-travel-mfa": [("Risky sign-in", "{user} authenticated from {ext_ip} ({country}) while their badge "
                                    "was used in the office {mins} minutes earlier.", "Legacy protocol used; MFA not challenged.")],
    "acct/spray-failed": [("Excessive failed logins", "Sign-in failures for {n_small} users with the same password "
                           "guess from {ext_ip}.", "Smart lockout blocked the source; no success.")],
    "acct/fp-travel": [("Unfamiliar sign-in properties", "{user} logged in from a new device in {city}.",
                        "User replaced their laptop today; IT ticket {chg}; MFA satisfied.")],
    "exfil/personal-cloud": [("Unusual data egress", "{host} ({user}) sent {gb} GB to a file-sharing site at 02:00.",
                              "User account was disabled for termination this morning.")],
    "exfil/fp-backup": [("Data transfer anomaly", "{gb} GB outbound from {srv} to {ext_ip}.",
                         "Owner confirms database export to the vendor's managed backup, approved under {chg}.")],
    "recon/internal-lateral": [("Lateral movement suspected", "{host} tried remote WMI on {n_small} servers using "
                                "{user}'s credentials.", "Account belongs to a receptionist with no admin duties.")],
    "recon/fp-vuln-scanner": [("Host scan", "{int_ip} probing TCP {port} across the data center.",
                               "IP is the security team's scanner; results feed the monthly report.")],
    "dos/volumetric": [("Service degradation", "Traffic to the online bill-pay site is 40x normal from botnet sources.",
                        "Site intermittently down during tax deadline week.")],
    "misconfig/public-bucket": [("Data exposure", "File share link for {bucket} is set to 'anyone with the link' and "
                                 "indexed by a search engine.", "Contains scanned permit applications with SSN fields.")],
    "misconfig/open-rdp": [("Firewall rule too broad", "Rule allows any source to SSH (22) on {host}.", "Added for a vendor "
                            "last month and never removed; no suspicious logins.")],
    "policy/unapproved-software": [("Blocked application", "{user} tried to install {tool} on {host}.", "Install blocked; reminder email sent.")],
    "policy/shadow-it": [("Unapproved cloud app", "Traffic to {saas} from {n_small} devices.", "Team says it is for sharing meeting notes.")],
}


SOURCES = {
    "malware": ["EDR", "Antivirus console", "SIEM correlation"], "phishing": ["Email gateway", "User report button", "SIEM correlation"],
    "account_compromise": ["Identity provider sign-in logs", "SIEM correlation", "VPN logs"],
    "data_exfiltration": ["DLP", "Firewall / NDR", "SIEM correlation"], "reconnaissance": ["IDS", "Firewall / NDR", "WAF"],
    "denial_of_service": ["WAF", "Load balancer monitoring", "Firewall / NDR"],
    "misconfiguration": ["Cloud security posture scan", "Vulnerability scanner", "External attack surface scan"],
    "policy_violation": ["Endpoint management", "CASB", "DLP"],
}
VENDOR_SEV = ["Low", "Medium", "High", "Critical", "Informational", "3", "7", "9"]
TS = lambda r: f"2026-{r.randrange(1, 13):02d}-{r.randrange(1, 29):02d}T{r.randrange(0, 24):02d}:{r.randrange(0, 60):02d}:{r.randrange(0, 60):02d}Z"  # noqa: E731


def render(rng, rule, summary, context):
    fmt = rng.randrange(5)
    vsev = C.pick(rng, VENDOR_SEV)
    aid = f"{C.pick(rng, ['ALRT', 'INC', 'DET', 'EVT'])}-{rng.randrange(100000, 999999)}"
    if fmt == 0:
        return f"Alert: {rule}\nID: {aid}\nVendor severity: {vsev}\nTime: {TS(rng)}\nDetails: {summary}\nNotes: {context}"
    if fmt == 1:
        return json.dumps({"alert_id": aid, "rule": rule, "vendor_severity": vsev, "timestamp": TS(rng),
                           "description": summary, "enrichment": context})
    if fmt == 2:
        return (f"<{rng.randrange(100, 190)}>{TS(rng)} sensor01 alert rule=\"{rule}\" sev={vsev} "
                f"msg=\"{summary}\" note=\"{context}\"")
    if fmt == 3:
        who = C.pick(rng, ["Tier 1 analyst", "SOC note", "On-call", "Analyst"])
        return f"{who}: {rule} fired. {summary} {context} {C.pick(rng, ['Please advise.', 'Triage?', '', 'Assigning to queue.'])}"
    return (f"Ticket {aid} [{C.pick(rng, ['NEW', 'OPEN', 'AUTO'])}] {rule} - vendor sev {vsev}\n"
            f"{summary}\n---\n{context}")


TEST_FAMILIES = ["malware/macro-powershell", "malware/fp-eicar", "phishing/simulation", "exfil/dns-tunnel", "recon/web-enum", "dos/fp-load-test", "misconfig/public-bucket",
                 "policy/usb-restricted", "acct/admin-token-theft"]


def build(rng):
    examples = []
    for cat, fam, tp, sev, variants in FAMILIES:
        variants = variants + EXTRA.get(fam, [])
        for i in range(PER_FAMILY):
            rule, summary, context = variants[i % len(variants)]
            s = C.fill(rng, summary, SLOTS)
            c = C.fill(rng, context, SLOTS)
            if rng.random() < 0.3:
                s = C.typo(rng, s, 0.03)
            alert = render(rng, rule, s, c)
            examples.append({
                "family": fam, "group": cat,
                "state": {"source": C.pick(rng, SOURCES[cat]), "alert": alert},
                "gold": {"category": cat, "true_positive": tp, "severity": sev,
                         "needs_escalation": bool(tp and sev >= 3)},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
