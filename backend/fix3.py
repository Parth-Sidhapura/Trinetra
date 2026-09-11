import io, ast
p = "app/services/resolution.py"
s = io.open(p, encoding="utf-8").read()

old = "        sim = _cosine(list(vec_a or []), list(vec_b or []))"
new = ("        sim = _cosine(\n"
       "            list(vec_a) if vec_a is not None else [],\n"
       "            list(vec_b) if vec_b is not None else [],\n"
       "        )")

if old in s:
    s = s.replace(old, new)
    io.open(p, "w", encoding="utf-8").write(s)
    ast.parse(s)
    print("PATCHED OK")
else:
    i = s.find("_cosine(list(")
    print("NOT FOUND:", repr(s[i-80:i+120]))
