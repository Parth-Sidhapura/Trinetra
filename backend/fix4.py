import io, ast
p = "app/services/resolution.py"
s = io.open(p, encoding="utf-8").read()

s = s.replace('SEMANTIC_THRESHOLD = 0.86', 'SEMANTIC_THRESHOLD = 0.93')
s = s.replace('["PERSON", "ORGANIZATION", "LOCATION"]))',
              '["PERSON", "ORGANIZATION"]))')
s = s.replace('if obs_a.entity_type not in ("PERSON", "ORGANIZATION", "LOCATION"):',
              'if obs_a.entity_type not in ("PERSON", "ORGANIZATION"):')
s = s.replace("if obs_a.entity_type not in ('PERSON','ORGANIZATION','LOCATION'):",
              "if obs_a.entity_type not in ('PERSON','ORGANIZATION'):")

io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("PATCHED OK")
