import io, ast
p = "app/services/resolution.py"
s = io.open(p, encoding="utf-8").read()

old = '["PERSON", "ORGANIZATION", "LOCATION", "PHONE",\n                     "VEHICLE", "ACCOUNT", "UPI"]'
new = '["PERSON", "ORGANIZATION", "LOCATION"]'

if old in s:
    s = s.replace(old, new)
    io.open(p, "w", encoding="utf-8").write(s)
    ast.parse(s)
    print("PATCHED OK")
else:
    i = s.find("entity_type.in_")
    print("PATTERN NOT FOUND. Actual block:")
    print(repr(s[i-60:i+220]))
