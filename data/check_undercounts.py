import sqlite3

db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()

# Countries we'd expect thousands+ from based on population and NGO sector size
# but probably got capped by Wikidata query limits
expected_large = {
    'IN': ('India', 10000),
    'CN': ('China', 5000),
    'BR': ('Brazil', 5000),
    'ID': ('Indonesia', 3000),
    'MX': ('Mexico', 3000),
    'JP': ('Japan', 3000),
    'DE': ('Germany', 3000),
    'FR': ('France', 3000),
    'GB': ('United Kingdom', 3000),
    'IT': ('Italy', 2000),
    'ES': ('Spain', 2000),
    'KR': ('South Korea', 2000),
    'PH': ('Philippines', 2000),
    'PK': ('Pakistan', 2000),
    'BD': ('Bangladesh', 1500),
    'RU': ('Russia', 2000),
    'NG': ('Nigeria', 2000),
    'CA': ('Canada', 2000),
    'AU': ('Australia', 2000),
    'ZA': ('South Africa', 2000),
    'KE': ('Kenya', 1500),
    'CO': ('Colombia', 1500),
    'AR': ('Argentina', 1500),
    'PE': ('Peru', 1000),
    'TH': ('Thailand', 1000),
    'VN': ('Vietnam', 1000),
    'TR': ('Turkey', 1500),
    'PL': ('Poland', 1000),
    'EG': ('Egypt', 1000),
    'UA': ('Ukraine', 1000),
}

print(f"{'CC':<4} {'Country':<25} {'Actual':>8} {'Expected':>10} {'Gap':>8} {'%':>6}")
print("-" * 70)

rerun_list = []
for cc, (name, expected) in sorted(expected_large.items(), key=lambda x: x[1][1], reverse=True):
    c.execute("SELECT COUNT(*) FROM organizations WHERE status != 'removed' AND country_code = ?", (cc,))
    actual = c.fetchone()[0]
    gap = expected - actual
    pct = (actual / expected * 100) if expected > 0 else 0
    flag = " *** RE-RUN" if actual < expected * 0.5 else ""
    print(f"{cc:<4} {name:<25} {actual:>8,} {expected:>10,} {gap:>+8,} {pct:>5.0f}%{flag}")
    if actual < expected * 0.5:
        rerun_list.append((cc, name, actual, expected))

print(f"\n--- NEED RE-RUN ({len(rerun_list)} countries) ---")
for cc, name, actual, expected in rerun_list:
    print(f"{cc}  {name} ({actual} vs expected {expected}+)")

db.close()
